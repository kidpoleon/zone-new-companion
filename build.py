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
    
    # Build command with platform-specific options
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
    
    # For Windows release, always create .exe extension
    # We'll force rename after build regardless of current platform
    create_windows_exe = True  # Set to True for Windows releases
    
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
        
        # Force .exe extension for Windows releases
        if create_windows_exe:
            if not exe_file.name.endswith(".exe"):
                new_name = exe_file.with_suffix(".exe")
                exe_file.rename(new_name)
                print(f"Renamed to: {new_name}")
                exe_file = new_name
        else:
            # Remove .exe extension on non-Windows releases if present
            if exe_file.name.endswith(".exe"):
                new_name = exe_file.with_suffix("")
                exe_file.rename(new_name)
                print(f"Renamed to: {new_name}")
                exe_file = new_name
        
        # Verify final executable exists and has correct name
        if not exe_file.exists():
            print("Error: Final executable not found")
            return False
            
        expected_name = "zone-new-companion.exe" if create_windows_exe else "zone-new-companion"
        if exe_file.name != expected_name:
            print(f"Warning: Expected '{expected_name}' but got '{exe_file.name}'")
        
        print(f"Final executable: {exe_file}")
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
