#!/usr/bin/env python3
"""Build script for zone-new-companion."""

import subprocess
import sys
from pathlib import Path


def build_executable():
    """Build the executable using PyInstaller."""
    print("Building zone-new-companion executable...")
    
    # Check if icon exists
    icon_path = Path("zone_new_companion/icon/icon.ico")
    if not icon_path.exists():
        print(f"Error: Icon file not found at {icon_path}")
        return False
    
    # Build command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean", 
        "--onefile",
        "--windowed",
        "--name", "zone-new-companion",
        "--icon", str(icon_path),
        "main.py"
    ]
    
    print(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("Build completed successfully!")
        print("Executable created at: dist/zone-new-companion.exe")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return False


if __name__ == "__main__":
    success = build_executable()
    sys.exit(0 if success else 1)
