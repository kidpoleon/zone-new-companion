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
            lines = [line.strip() for line in playlist_resp.text.splitlines() if line.strip()]
            segment_line = next((line for line in lines if not line.startswith("#")), "")
            if not segment_line:
                return True
            segment_url = urljoin(m3u8_url, segment_line)
            segment_resp = self._session.get(
                segment_url,
                stream=True,
                timeout=DEFAULT_TIMEOUT,
            )
            ok = segment_resp.status_code < 400
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
