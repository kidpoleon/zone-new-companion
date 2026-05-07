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


@dataclass(slots=True)
class VerificationResult:
    """Verification result for one media item."""

    item_id: str
    status: str


class StreamVerifier:
    """Verify stream reachability and A/V presence without OCR."""

    def __init__(self) -> None:
        self._session = create_session()

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

        with ThreadPoolExecutor(max_workers=max(1, min(workers, 24))) as executor:
            futures = {
                executor.submit(self._verify_single, service, credentials, item): item.id
                for item in target_items
            }
            for future in as_completed(futures):
                item_id = futures[future]
                try:
                    result = future.result()
                    status_by_id[item_id] = result.status
                except (RuntimeError, ValueError, OSError):
                    status_by_id[item_id] = "OFF (Verify Error)"
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
        stream_url = item.stream_url or service.resolve_stream_url(credentials, item)
        if not self._quick_reachable(stream_url):
            return VerificationResult(item_id=item.id, status="OFF (Unreachable)")

        has_video, has_audio = self._probe_with_ffprobe(stream_url)
        if has_video and has_audio:
            return VerificationResult(item_id=item.id, status="OK (Video+Audio)")
        if has_audio:
            return VerificationResult(item_id=item.id, status="OK (Audio)")
        if has_video:
            return VerificationResult(item_id=item.id, status="OK (Video)")
        return VerificationResult(item_id=item.id, status="OFF (No A/V)")

    def _quick_reachable(self, stream_url: str) -> bool:
        try:
            if ".m3u8" in stream_url:
                return self._quick_hls_check(stream_url)
            response = self._session.get(
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

    def _quick_hls_check(self, m3u8_url: str) -> bool:
        try:
            playlist_resp = self._session.get(m3u8_url, timeout=DEFAULT_TIMEOUT)
            playlist_resp.raise_for_status()
            
            # Check if it's actually an M3U playlist
            content = playlist_resp.text.strip()
            if not content.startswith('#EXTM3U'):
                # Not a valid M3U playlist, might be an error page
                return False
            
            lines = [line.strip() for line in content.splitlines() if line.strip()]
            
            # Look for actual media segments (non-comment lines)
            segment_lines = [line for line in lines if not line.startswith('#')]
            
            if not segment_lines:
                # No media segments found, check if it's a live stream with EXTINF
                has_extinf = any('#EXTINF:' in line for line in lines)
                return has_extinf  # Consider it valid if it has EXTINF entries
            
            # Try to access the first segment to verify it's accessible
            segment_line = segment_lines[0]
            segment_url = urljoin(m3u8_url, segment_line)
            
            # Use a shorter timeout for segment checking
            segment_timeout = min(DEFAULT_TIMEOUT, 3)
            segment_resp = self._session.head(segment_url, timeout=segment_timeout)
            
            # Check if segment is accessible (HEAD request is faster)
            ok = segment_resp.status_code < 400
            
            # If HEAD fails, try GET as fallback
            if not ok:
                try:
                    segment_resp = self._session.get(
                        segment_url,
                        stream=True,
                        timeout=segment_timeout,
                    )
                    ok = segment_resp.status_code < 400
                    segment_resp.close()
                except:
                    ok = False
            segment_resp.close()
            return ok
        except RequestException:
            return False

    @staticmethod
    def _probe_with_ffprobe(stream_url: str) -> tuple[bool, bool]:
        command = [
            "ffprobe",
            "-v",
            "quiet",
            "-show_entries",
            "stream=codec_type",
            "-of",
            "json",
            stream_url,
        ]
        try:
            # Hide terminal window on Windows
            creation_flags = 0x08000000 if sys.platform == "win32" else 0  # CREATE_NO_WINDOW
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
                creationflags=creation_flags,
            )
            if completed.returncode != 0:
                return False, False
            payload = json.loads(completed.stdout or "{}")
            streams = payload.get("streams", [])
            has_video = any(stream.get("codec_type") == "video" for stream in streams)
            has_audio = any(stream.get("codec_type") == "audio" for stream in streams)
            return has_video, has_audio
        except (subprocess.SubprocessError, json.JSONDecodeError, OSError, ValueError):
            return False, False
