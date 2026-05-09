# Build Guide

This guide explains how to build Zone New Companion for all supported platforms.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Windows (.exe)](#windows-exe)
- [Linux (.AppImage, .deb, .rpm)](#linux-appimage-deb-rpm)
- [macOS (.dmg, .app)](#macos-dmg-app)
- [Automated Builds (GitHub Actions)](#automated-builds-github-actions)

---

## Prerequisites

### Common Requirements

- Python 3.8 or higher
- pip (Python package installer)
- Git

### Platform-Specific Requirements

#### Windows
- Windows 10/11
- Visual C++ Redistributable (usually installed with Python)

#### Linux
- Ubuntu 20.04+ or similar distribution
- Required packages:
  ```bash
  sudo apt install python3-dev python3-pip python3-venv build-essential
  ```

#### macOS
- macOS 10.15 (Catalina) or higher
- Xcode Command Line Tools:
  ```bash
  xcode-select --install
  ```

### Python Dependencies

Install build dependencies:

```bash
pip install pyinstaller
```

For application dependencies:

```bash
pip install -r requirements.txt
```

---

## Windows (.exe)

### Method 1: Using PyInstaller (Recommended)

1. **Open PowerShell or CMD as Administrator**

2. **Navigate to project directory**:
   ```powershell
   cd C:\path\to\zone-new-companion
   ```

3. **Create virtual environment**:
   ```powershell
   python -m venv venv
   venv\Scripts\activate
   ```

4. **Install dependencies**:
   ```powershell
   pip install -r requirements.txt
   pip install pyinstaller
   ```

5. **Build executable**:
   ```powershell
   pyinstaller --noconfirm --clean --onefile --windowed `
     --name zone-new-companion `
     --icon zone_new_companion\icon\icon.ico `
     --add-data "zone_new_companion\icon\icon.ico;zone_new_companion/icon" `
     --add-data "media;media" `
     --hidden-import pytesseract `
     --hidden-import cv2 `
     --hidden-import numpy `
     --hidden-import PIL `
     --collect-all pytesseract `
     --collect-all cv2 `
     --exclude-module matplotlib `
     --exclude-module scipy `
     main.py
   ```

6. **Output location**: `dist\zone-new-companion.exe`

### Method 2: Using cx_Freeze (Alternative)

```powershell
pip install cx_Freeze
python setup.py build
```

### Icon Embedding

The icon is automatically embedded when using the `--icon` flag with PyInstaller. The icon file is located at:
- `zone_new_companion\icon\icon.ico` (Windows)

---

## Linux (.AppImage, .deb, .rpm)

### AppImage (Universal Linux Package)

1. **Install dependencies**:
   ```bash
   sudo apt install python3-dev python3-pip python3-venv build-essential
   pip install pyinstaller
   ```

2. **Build executable**:
   ```bash
   pyinstaller --noconfirm --clean --onefile --windowed \
     --name zone-new-companion \
     --icon zone_new_companion/icon/icon.ico \
     --add-data "zone_new_companion/icon/icon.ico:zone_new_companion/icon" \
     --add-data "media:media" \
     --hidden-import pytesseract \
     --hidden-import cv2 \
     --hidden-import numpy \
     --hidden-import PIL \
     --collect-all pytesseract \
     --collect-all cv2 \
     --exclude-module matplotlib \
     --exclude-module scipy \
     main.py
   ```

3. **Create AppImage**:
   ```bash
   # Download appimagetool
   wget https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage
   chmod +x appimagetool-x86_64.AppImage
   
   # Create AppDir structure
   mkdir -p AppDir/usr/bin
   cp dist/zone-new-companion AppDir/usr/bin/
   
   # Create desktop file
   cat > AppDir/zone-new-companion.desktop << EOF
   [Desktop Entry]
   Name=Zone New Companion
   Exec=zone-new-companion
   Icon=icon
   Type=Application
   Categories=AudioVideo;Video;
   EOF
   
   # Build AppImage
   ./appimagetool-x86_64.AppImage AppDir
   ```

### Debian Package (.deb)

1. **Create package structure**:
   ```bash
   mkdir -p debian/DEBIAN
   mkdir -p debian/usr/bin
   mkdir -p debian/usr/share/applications
   mkdir -p debian/usr/share/icons/hicolor/256x256/apps
   ```

2. **Copy files**:
   ```bash
   cp dist/zone-new-companion debian/usr/bin/
   cp media/logo.png debian/usr/share/icons/hicolor/256x256/apps/zone-new-companion.png
   ```

3. **Create control file** (`debian/DEBIAN/control`):
   ```
   Package: zone-new-companion
   Version: 1.2.1
   Section: video
   Priority: optional
   Architecture: amd64
   Depends: vlc, python3
   Maintainer: Kidpoleon <kidpoleon@proton.me>
   Description: Unified desktop IPTV companion app
    Zone New Companion is a unified desktop IPTV companion app
    for Xtream Codes, Stalker Portal, and M3U playlists.
   ```

4. **Create desktop entry** (`debian/usr/share/applications/zone-new-companion.desktop`):
   ```ini
   [Desktop Entry]
   Name=Zone New Companion
   Comment=Unified desktop IPTV companion app
   Exec=zone-new-companion
   Icon=zone-new-companion
   Type=Application
   Categories=AudioVideo;Video;
   Terminal=false
   ```

5. **Build package**:
   ```bash
   dpkg-deb --build debian zone-new-companion_1.2.1_amd64.deb
   ```

### RPM Package (.rpm)

1. **Install rpm build tools**:
   ```bash
   sudo apt install rpm  # On Debian/Ubuntu
   # or
   sudo dnf install rpm-build  # On Fedora
   ```

2. **Create RPM spec file** (`zone-new-companion.spec`):
   ```spec
   Name:           zone-new-companion
   Version:        1.2.1
   Release:        1%{?dist}
   Summary:        Unified desktop IPTV companion app
   
   License:        MIT
   URL:            https://github.com/kidpoleon/zone-new-companion
   
   Requires:       vlc
   
   %description
   Zone New Companion is a unified desktop IPTV companion app
   for Xtream Codes, Stalker Portal, and M3U playlists.
   
   %install
   mkdir -p %{buildroot}/usr/bin
   mkdir -p %{buildroot}/usr/share/applications
   mkdir -p %{buildroot}/usr/share/icons/hicolor/256x256/apps
   
   cp %{SOURCE0} %{buildroot}/usr/bin/zone-new-companion
   cp %{SOURCE1} %{buildroot}/usr/share/applications/zone-new-companion.desktop
   cp %{SOURCE2} %{buildroot}/usr/share/icons/hicolor/256x256/apps/zone-new-companion.png
   
   %files
   /usr/bin/zone-new-companion
   /usr/share/applications/zone-new-companion.desktop
   /usr/share/icons/hicolor/256x256/apps/zone-new-companion.png
   ```

3. **Build RPM**:
   ```bash
   rpmbuild -bb zone-new-companion.spec
   ```

---

## macOS (.dmg, .app)

### Building .app Bundle

1. **Install dependencies**:
   ```bash
   brew install python@3.11
   pip3 install pyinstaller
   pip3 install -r requirements.txt
   ```

2. **Build .app bundle**:
   ```bash
   pyinstaller --noconfirm --clean --windowed \
     --name "Zone New Companion" \
     --icon zone_new_companion/icon/icon.icns \
     --add-data "zone_new_companion/icon/icon.icns:zone_new_companion/icon" \
     --add-data "media:media" \
     --hidden-import pytesseract \
     --hidden-import cv2 \
     --hidden-import numpy \
     --hidden-import PIL \
     --collect-all pytesseract \
     --collect-all cv2 \
     --exclude-module matplotlib \
     --exclude-module scipy \
     main.py
   ```

3. **Output location**: `dist/Zone New Companion.app`

### Creating .dmg Installer

1. **Create DMG**:
   ```bash
   # Install create-dmg
   brew install create-dmg
   
   # Create DMG
   create-dmg \
     --volname "Zone New Companion Installer" \
     --volicon "zone_new_companion/icon/icon.icns" \
     --window-pos 200 120 \
     --window-size 800 400 \
     --icon-size 100 \
     --icon "Zone New Companion.app" 200 190 \
     --hide-extension "Zone New Companion.app" \
     --app-drop-link 600 185 \
     "Zone-New-Companion-1.2.1.dmg" \
     "dist/Zone New Companion.app"
   ```

2. **Alternative: Using hdiutil**:
   ```bash
   # Create temporary DMG
   hdiutil create -srcfolder "dist/Zone New Companion.app" -volname "Zone New Companion" -fs HFS+ -fsargs "-c c=64,a=16,e=16" -format UDRW -size 100M temp.dmg
   
   # Convert to compressed read-only DMG
   hdiutil convert temp.dmg -format UDZO -o "Zone-New-Companion-1.2.1.dmg"
   
   # Remove temporary file
   rm temp.dmg
   ```

### Code Signing (Optional but Recommended)

For distribution without Gatekeeper warnings:

```bash
# Sign the app
 codesign --deep --force --verify --verbose --sign "Developer ID Application: Your Name" "dist/Zone New Companion.app"

# Notarize (requires Apple Developer account)
xcrun altool --notarize-app --primary-bundle-id "com.kidpoleon.zone-new-companion" --username "your-apple-id" --password "app-specific-password" --file "Zone-New-Companion-1.2.1.dmg"
```

---

## Automated Builds (GitHub Actions)

This repository includes a GitHub Actions workflow that automatically builds and releases packages for all platforms.

### How It Works

1. Push a tag starting with 'v' (e.g., `v1.2.1`)
2. GitHub Actions automatically:
   - Creates a new release
   - Builds for Windows, Linux, and macOS
   - Attaches all binaries to the release

### Manual Trigger

You can also trigger the workflow manually from the Actions tab.

### Required Secrets

No additional secrets are required for basic builds. The workflow uses `GITHUB_TOKEN` which is automatically provided.

For macOS code signing (optional):
- `APPLE_DEVELOPER_ID`: Your Apple Developer ID
- `APPLE_ID`: Your Apple ID email
- `APPLE_APP_PASSWORD`: App-specific password

---

## Icon Preparation

### Windows (.ico)

The icon file should be at `zone_new_companion/icon/icon.ico` with multiple sizes:
- 16x16
- 32x32
- 48x48
- 256x256

### macOS (.icns)

Convert PNG to ICNS:

```bash
# Install libicns
brew install libicns

# Convert
png2icns zone_new_companion/icon/icon.icns media/logo.png
```

Or create multi-resolution ICNS:

```bash
mkdir icon.iconset
sips -z 16 16 media/logo.png --out icon.iconset/icon_16x16.png
sips -z 32 32 media/logo.png --out icon.iconset/icon_16x16@2x.png
sips -z 32 32 media/logo.png --out icon.iconset/icon_32x32.png
sips -z 64 64 media/logo.png --out icon.iconset/icon_32x32@2x.png
sips -z 128 128 media/logo.png --out icon.iconset/icon_128x128.png
sips -z 256 256 media/logo.png --out icon.iconset/icon_128x128@2x.png
sips -z 256 256 media/logo.png --out icon.iconset/icon_256x256.png
sips -z 512 512 media/logo.png --out icon.iconset/icon_256x256@2x.png
iconutil -c icns icon.iconset -o zone_new_companion/icon/icon.icns
rm -rf icon.iconset
```

### Linux (.png)

Place icon at `media/logo.png` (256x256 or larger).

---

## Troubleshooting

### Windows

**Issue**: "MSVCP140.dll not found"
**Solution**: Install Visual C++ Redistributable from Microsoft

**Issue**: Icon not showing in taskbar
**Solution**: Ensure icon.ico is a valid multi-resolution ICO file

### Linux

**Issue**: "Cannot open display"
**Solution**: Ensure X11 is running and `DISPLAY` environment variable is set

**Issue**: AppImage won't run
**Solution**: Make it executable: `chmod +x zone-new-companion.AppImage`

### macOS

**Issue**: "App is damaged and can't be opened"
**Solution**: Code sign the app or users can right-click → Open

**Issue**: Icon not showing in Dock
**Solution**: Ensure icon.icns is properly created with all required sizes

---

## Build Checklist

Before releasing, verify:

- [ ] Version number updated in all files
- [ ] Icon properly embedded
- [ ] Application launches without errors
- [ ] VLC integration works
- [ ] All portal types tested (Xtream, Stalker, M3U)
- [ ] Stream playback verified
- [ ] No debug/console window shows (for windowed builds)

---

## Contact

For build issues, contact: **Kidpoleon** <kidpoleon@proton.me>

Or open an issue on GitHub: https://github.com/kidpoleon/zone-new-companion/issues
