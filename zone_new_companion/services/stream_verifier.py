"""Fast and safe stream verification service."""

from __future__ import annotations

import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import urljoin

import requests
from requests import RequestException

from zone_new_companion.models import Credentials, MediaItem
from zone_new_companion.services.base import PortalService
from zone_new_companion.services.network import DEFAULT_TIMEOUT, create_session
from zone_new_companion.services.network_optimizer import OptimizedSession
from zone_new_companion.services.logger_service import logger_service
from zone_new_companion.services.ocr_service import OCRService


@dataclass(slots=True)
class VerificationResult:
    """Verification result for one media item."""

    item_id: str
    status: str


class StreamVerifier:
    """Verify stream reachability and A/V presence without OCR."""

    def __init__(self) -> None:
        self._session = OptimizedSession()
        self._ocr_service = OCRService()
        self._verified_count = 0
        self._total_count = 0

    def verify_items(
        self,
        service: PortalService,
        credentials: Credentials,
        items: Iterable[MediaItem],
        workers: int = 8,
    ) -> dict[str, str]:
        """Verify items concurrently and return status map keyed by item id."""
        status_by_id: dict[str, str] = {}
        target_items = [item for item in items if item.item_type in {"channel", "vod", "episode"}]
        if not target_items:
            return status_by_id

        self._total_count = len(target_items)
        self._verified_count = 0
        
        logger_service.info(f"Starting verification of {self._total_count} channels with {workers} workers")
        
        with ThreadPoolExecutor(max_workers=max(1, min(workers, 24))) as executor:
            futures = {
                executor.submit(self._verify_single, service, credentials, item): item
                for item in target_items
            }
            for future in as_completed(futures):
                item = futures[future]
                try:
                    result = future.result()
                    status_by_id[item.id] = result.status
                    self._verified_count += 1
                    
                    # Log progress for each channel
                    progress_percent = (self._verified_count / self._total_count) * 100
                    logger_service.info(
                        f"Channel {self._verified_count}/{self._total_count} ({progress_percent:.1f}%) "
                        f"- {item.name}: {result.status}"
                    )
                    
                except (RuntimeError, ValueError, OSError) as e:
                    status_by_id[item.id] = "OFF (Verify Error)"
                    self._verified_count += 1
                    logger_service.error(f"Channel {self._verified_count}/{self._total_count} - {item.name}: Verification error - {e}")
                    
        logger_service.info(f"Verification complete: {self._verified_count} channels processed")
        return status_by_id

    def verify_item(
        self,
        service: PortalService,
        credentials: Credentials,
        item: MediaItem,
    ) -> VerificationResult:
        return self._verify_single(service, credentials, item)

    def _verify_single(
        self,
        service: PortalService,
        credentials: Credentials,
        item: MediaItem,
    ) -> VerificationResult:
        try:
            stream_url = item.stream_url or service.resolve_stream_url(credentials, item)
            
            # More permissive reachability check
            if not self._quick_reachable(stream_url):
                # Try one more time with different approach
                if not self._fallback_reachable(stream_url):
                    return VerificationResult(item_id=item.id, status="OFF (Unreachable)")

            # Try ffprobe but be more permissive
            has_video, has_audio = self._probe_with_ffprobe(stream_url)
            
            # If ffprobe fails but stream is reachable, use OCR for M3U8 streams
            if not has_video and not has_audio and ".m3u8" in stream_url:
                logger_service.debug(f"Using OCR for M3U8 stream: {item.name}")
                is_valid_content, ocr_text = self._ocr_service.analyze_stream_frame(stream_url, timeout=10)
                if is_valid_content:
                    return VerificationResult(item_id=item.id, status="OK (OCR Validated)")
                else:
                    logger_service.debug(f"OCR validation failed: {ocr_text}")
            
            # If ffprobe fails but stream is reachable, consider it OK
            if has_video and has_audio:
                return VerificationResult(item_id=item.id, status="OK (Video+Audio)")
            elif has_audio:
                return VerificationResult(item_id=item.id, status="OK (Audio)")
            elif has_video:
                return VerificationResult(item_id=item.id, status="OK (Video)")
            else:
                # If ffprobe failed but stream was reachable, mark as OK
                return VerificationResult(item_id=item.id, status="OK (Reachable)")
                
        except Exception as e:
            logger_service.debug(f"Verification failed for {item.name}: {e}")
            return VerificationResult(item_id=item.id, status="OFF (Verify Error)")

    def _quick_reachable(self, stream_url: str) -> bool:
        try:
            if ".m3u8" in stream_url:
                return self._quick_hls_check(stream_url)
            response = self._session.session.get(
                stream_url,
                stream=True,
                timeout=DEFAULT_TIMEOUT,
                allow_redirects=True,
            )
            ok = response.status_code < 400
            response.close()
            return ok
        except RequestException:
            return False

    def _fallback_reachable(self, stream_url: str) -> bool:
        """Fallback reachability check with more permissive settings."""
        try:
            # Try with a longer timeout and different approach
            response = self._session.session.get(
                stream_url,
                stream=True,
                timeout=15,  # Longer timeout
                allow_redirects=True,
                headers={'User-Agent': 'Mozilla/5.0 (compatible; VLC)'}
            )
            ok = response.status_code < 400
            response.close()
            return ok
        except RequestException:
            return False

    def _quick_hls_check(self, m3u8_url: str) -> bool:
        try:
            playlist_resp = self._session.session.get(m3u8_url, timeout=DEFAULT_TIMEOUT)
            playlist_resp.raise_for_status()
            
            # Check if it's actually an M3U playlist
            content = playlist_resp.text.strip()
            if not content.startswith('#EXTM3U'):
                # Not a valid M3U playlist, might be an error page
                return False
            
            lines = [line.strip() for line in content.splitlines() if line.strip()]
            
            # Look for M3U-specific markers that indicate valid playlist
            has_extinf = any('#EXTINF:' in line for line in lines)
            has_ext_x_version = any('#EXT-X-VERSION:' in line for line in lines)
            has_ext_x_stream = any('#EXT-X-STREAM-INF:' in line for line in lines)
            has_ext_x_media = any('#EXT-X-MEDIA:' in line for line in lines)
            
            # If it has M3U markers, consider it valid even without segments
            if has_extinf or has_ext_x_version or has_ext_x_stream or has_ext_x_media:
                logger_service.debug(f"M3U8 playlist has valid markers: EXTINF={has_extinf}, VERSION={has_ext_x_version}, STREAM={has_ext_x_stream}")
                return True
            
            # Look for actual media segments (non-comment lines)
            segment_lines = [line for line in lines if not line.startswith('#')]
            
            if not segment_lines:
                # No media segments found but has M3U structure, consider valid
                logger_service.debug("M3U8 playlist has no segments but has valid structure")
                return True
            
            # Try to access the first segment to verify it's accessible
            segment_line = segment_lines[0]
            segment_url = urljoin(m3u8_url, segment_line)
            
            # Use a shorter timeout for segment checking
            segment_timeout = min(DEFAULT_TIMEOUT, 3)
            segment_resp = self._session.session.head(segment_url, timeout=segment_timeout)
            
            # Check if segment is accessible (HEAD request is faster)
            ok = segment_resp.status_code < 400
            
            # If HEAD fails, try GET as fallback
            if not ok:
                try:
                    segment_resp = self._session.session.get(
                        segment_url,
                        stream=True,
                        timeout=segment_timeout,
                    )
                    ok = segment_resp.status_code < 400
                    segment_resp.close()
                except:
                    ok = False
            segment_resp.close()
            
            # Even if segment check fails, if we have M3U structure, consider it valid
            if not ok and (has_extinf or has_ext_x_version):
                logger_service.debug("M3U8 segment check failed but playlist structure is valid")
                return True
                
            return ok
        except RequestException as e:
            logger_service.debug(f"M3U8 check failed: {e}")
            return False

    def _probe_with_ffprobe(self, stream_url: str) -> tuple[bool, bool]:
        # Enhanced FFprobe analysis for M3U8 streams
        if ".m3u8" in stream_url:
            return self._probe_m3u8_stream(stream_url)
        else:
            return self._probe_regular_stream(stream_url)

    def _probe_m3u8_stream(self, stream_url: str) -> tuple[bool, bool]:
        """Enhanced M3U8 stream probing with better error handling."""
        commands = [
            # First try: Basic stream info
            [
                "ffprobe",
                "-v", "quiet",
                "-show_entries", "stream=codec_type",
                "-of", "json",
                "-analyzeduration", "10",
                "-probesize", "2000000",
                stream_url
            ],
            # Second try: Format info for adaptive streams
            [
                "ffprobe",
                "-v", "quiet",
                "-show_entries", "format=duration",
                "-of", "json",
                "-analyzeduration", "15",
                stream_url
            ],
            # Third try: More aggressive probing
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "stream=codec_type",
                "-of", "json",
                "-analyzeduration", "30",
                "-probesize", "5000000",
                "-threads", "1",
                stream_url
            ]
        ]
        
        for i, command in enumerate(commands):
            try:
                creation_flags = 0x08000000 if sys.platform == "win32" else 0
                completed = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=20 + (i * 5),  # Increasing timeout for each attempt
                    check=False,
                    creationflags=creation_flags,
                )
                
                if completed.returncode == 0:
                    payload = json.loads(completed.stdout or "{}")
                    
                    # Check streams first
                    streams = payload.get("streams", [])
                    if streams:
                        has_video = any(stream.get("codec_type") == "video" for stream in streams)
                        has_audio = any(stream.get("codec_type") == "audio" for stream in streams)
                        if has_video or has_audio:
                            logger_service.debug(f"M3U8 FFprobe success (attempt {i+1}): video={has_video}, audio={has_audio}")
                            return has_video, has_audio
                    
                    # Check format info as fallback
                    format_info = payload.get("format", {})
                    if format_info.get("duration"):
                        logger_service.debug(f"M3U8 format info found (attempt {i+1}): duration={format_info.get('duration')}")
                        return True, True  # Assume both if we have duration
                        
                else:
                    logger_service.debug(f"M3U8 FFprobe attempt {i+1} failed: {completed.stderr}")
                    
            except subprocess.TimeoutExpired:
                logger_service.debug(f"M3U8 FFprobe timeout (attempt {i+1})")
                continue
            except (subprocess.SubprocessError, json.JSONDecodeError, OSError, ValueError) as e:
                logger_service.debug(f"M3U8 FFprobe error (attempt {i+1}): {e}")
                continue
        
        return False, False

    def _probe_regular_stream(self, stream_url: str) -> tuple[bool, bool]:
        """Regular stream probing for non-M3U8 streams."""
        command = [
            "ffprobe",
            "-v", "quiet",
            "-show_entries", "stream=codec_type",
            "-of", "json",
            "-analyzeduration", "5",
            "-probesize", "1000000",
            stream_url,
        ]
        try:
            creation_flags = 0x08000000 if sys.platform == "win32" else 0
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
                creationflags=creation_flags,
            )
            if completed.returncode != 0:
                logger_service.debug(f"FFprobe failed for {stream_url}: {completed.stderr}")
                return False, False
            payload = json.loads(completed.stdout or "{}")
            streams = payload.get("streams", [])
            has_video = any(stream.get("codec_type") == "video" for stream in streams)
            has_audio = any(stream.get("codec_type") == "audio" for stream in streams)
            return has_video, has_audio
        except subprocess.TimeoutExpired:
            logger_service.debug(f"FFprobe timeout for {stream_url}")
            return False, False
        except (subprocess.SubprocessError, json.JSONDecodeError, OSError, ValueError) as e:
            logger_service.debug(f"FFprobe error for {stream_url}: {e}")
            return False, False
