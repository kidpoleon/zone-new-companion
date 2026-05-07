#!/usr/bin/env python3
"""Build script for zone-new-companion."""

import os
import platform
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
    
    # Determine executable name based on platform
    exe_name = "zone-new-companion.exe" if platform.system() == "Windows" else "zone-new-companion"
    
    # Clean previous build
    print("Cleaning previous build...")
    for path in ["build", "dist"]:
        if Path(path).exists():
            import shutil
            shutil.rmtree(path)
    
    # Build command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean", 
        "--onefile",
        "--windowed",
        "--name", "zone-new-companion",
        "--icon", str(icon_path),
        "--add-data", f"{icon_path}{os.pathsep}zone_new_companion/icon",
        "main.py"
    ]
    
    print(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("Build completed successfully!")
        
        # Check if executable was created
        dist_path = Path("dist")
        if not dist_path.exists():
            print("Error: dist directory not created")
            return False
            
        # Find the executable
        built_files = list(dist_path.glob("*"))
        if not built_files:
            print("Error: No executable found in dist directory")
            return False
            
        exe_file = built_files[0]  # Get the first (should be only) file
        print(f"Executable created at: {exe_file}")
        
        # Rename to have proper .exe extension on Windows
        if platform.system() == "Windows" and not exe_file.name.endswith(".exe"):
            new_name = exe_file.with_suffix(".exe")
            exe_file.rename(new_name)
            print(f"Renamed to: {new_name}")
        elif platform.system() != "Windows" and exe_file.name.endswith(".exe"):
            # Remove .exe extension on non-Windows platforms
            new_name = exe_file.with_suffix("")
            exe_file.rename(new_name)
            print(f"Renamed to: {new_name}")
            
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Build failed with exit code {e.returncode}")
        if e.stdout:
            print("STDOUT:")
            print(e.stdout)
        if e.stderr:
            print("STDERR:")
            print(e.stderr)
        return False
    except Exception as e:
        print(f"Unexpected error during build: {e}")
        return False


if __name__ == "__main__":
    success = build_executable()
    sys.exit(0 if success else 1)
