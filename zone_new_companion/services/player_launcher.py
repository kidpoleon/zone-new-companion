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
    vlc_in_path = shutil.which("vlc")
    if vlc_in_path:
        return vlc_in_path
    return ""


def launch_stream(stream_url: str) -> None:
    """Launch stream with VLC."""
    vlc_path = resolve_vlc_path()
    if not vlc_path:
        raise FileNotFoundError(
            "VLC executable not found. Install VLC or ensure it is available at one of: "
            + ", ".join(candidate_vlc_paths()),
        )
    LOGGER.info("Launching VLC at %s", vlc_path)
    
    # Platform-specific launch options
    startupinfo = None
    if platform.system() == "Windows":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
    
    try:
        subprocess.Popen(
            [vlc_path, stream_url], 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL,
            startupinfo=startupinfo
        )
    except Exception as e:
        LOGGER.error("Failed to launch VLC: %s", e)
        raise RuntimeError(f"Failed to launch VLC: {e}")
