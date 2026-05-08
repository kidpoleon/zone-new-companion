#!/usr/bin/env python3
"""Build script for zone-new-companion on Windows systems."""

import os
import platform
import subprocess
import sys
from pathlib import Path


def build_executable():
    """Build the executable using PyInstaller for Windows systems."""
    print("Building zone-new-companion executable for Windows...")
    
    # Check if icon exists
    icon_path = Path("zone_new_companion/icon/icon.ico")
    if not icon_path.exists():
        print(f"Error: Icon file not found at {icon_path}")
        return False
    
    # Clean previous build
    print("Cleaning previous build...")
    for path in ["build", "dist"]:
        if Path(path).exists():
            import shutil
            shutil.rmtree(path)
    
    # Build command for Windows systems with OCR support
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean", 
        "--onefile",
        "--windowed",
        "--name", "zone-new-companion",
        "--icon", str(icon_path),
        f"--add-data={icon_path}{os.pathsep}zone_new_companion/icon",
        f"--add-data=media{os.pathsep}media",
        "--hidden-import", "pytesseract",
        "--hidden-import", "cv2",
        "--hidden-import", "numpy",
        "--hidden-import", "PIL",
        "--collect-all", "pytesseract",
        "--collect-all", "cv2",
        "--exclude-module", "matplotlib",
        "--exclude-module", "scipy",
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
            
        exe_file = built_files[0]
        print(f"Executable created at: {exe_file}")
        
        # Force .exe extension on Windows
        if not exe_file.name.endswith(".exe"):
            new_name = exe_file.with_suffix(".exe")
            exe_file.rename(new_name)
            print(f"Renamed to: {new_name}")
            exe_file = new_name
        
        # Verify final executable exists
        if not exe_file.exists():
            print("Error: Final executable not found")
            return False
            
        expected_name = "zone-new-companion.exe"
        if exe_file.name != expected_name:
            print(f"Warning: Expected '{expected_name}' but got '{exe_file.name}'")
        
        print(f"Final Windows executable: {exe_file}")
        print("Note: This executable should be built on Windows for best compatibility.")
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
