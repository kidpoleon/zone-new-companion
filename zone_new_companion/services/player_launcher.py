"""Player launching with platform-specific VLC paths."""

from __future__ import annotations

import logging
import os
import platform
import subprocess
from pathlib import Path

LOGGER = logging.getLogger(__name__)


def candidate_vlc_paths() -> list[str]:
    """Return ordered VLC paths per platform."""
    system = platform.system().lower()
    if system == "windows":
        return [r"C:\Program Files\VideoLAN\VLC\vlc.exe"]
    if system == "darwin":
        return ["/Applications/VLC.app/Contents/MacOS/VLC"]
    return [
        "/usr/bin/vlc",
        "/snap/bin/vlc",
        "/var/lib/flatpak/exports/bin/org.videolan.VLC",
    ]


def resolve_vlc_path() -> str:
    """Resolve first existing VLC executable path."""
    for path in candidate_vlc_paths():
        if Path(path).exists() and os.access(path, os.X_OK):
            return path
    return candidate_vlc_paths()[0]


def launch_stream(stream_url: str) -> None:
    """Launch stream with VLC."""
    vlc_path = resolve_vlc_path()
    LOGGER.info("Launching VLC at %s", vlc_path)
    subprocess.Popen([vlc_path, stream_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
