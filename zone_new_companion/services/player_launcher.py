"""Player launching with platform-specific VLC paths."""

from __future__ import annotations

import logging
import os
import platform
import subprocess
from pathlib import Path
import shutil

LOGGER = logging.getLogger(__name__)


def candidate_vlc_paths() -> list[str]:
    """Return ordered VLC paths per platform."""
    system = platform.system().lower()
    if system == "windows":
        return [
            r"C:\Program Files\VideoLAN\VLC\vlc.exe",
            r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
        ]
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
    vlc_in_path = shutil.which("vlc")
    if vlc_in_path:
        return vlc_in_path
    return ""


def launch_stream(stream_url: str) -> None:
    """Launch stream with VLC.

    Args:
        stream_url: The URL to play. Must be a complete, valid URL.

    Raises:
        FileNotFoundError: If VLC is not found.
        RuntimeError: If VLC fails to launch.
    """
    if not stream_url:
        raise ValueError("Stream URL is empty")

    vlc_path = resolve_vlc_path()
    if not vlc_path:
        raise FileNotFoundError(
            "VLC not found. Install VLC from videolan.org"
        )

    LOGGER.info("Launching VLC: %s", vlc_path)
    LOGGER.info("Stream URL: %s", stream_url[:80])

    # Build command with proper URL handling
    # Use --open to ensure URL is treated as a network stream
    cmd = [
        vlc_path,
        "--network-caching=1000",
        "--http-user-agent=Lavf/57.83.100",
        stream_url,
    ]

    # Windows-specific startup info to hide console window
    startupinfo = None
    if platform.system() == "Windows":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE

    try:
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            startupinfo=startupinfo,
        )
    except Exception as e:
        LOGGER.error("Failed to launch VLC: %s", e)
        raise RuntimeError(f"Failed to launch VLC: {e}")
