# Release Checklist for v1.2.3

## ✅ COMPLETED TASKS

### 1. Version Updates
- [x] `zone_new_companion/__init__.py` - Version updated to 1.2.3
- [x] `zone_new_companion/app.py` - AppUserModelID updated to 1.2.3
- [x] `README.md` - Version badge updated to 1.2.3
- [x] `SECURITY.md` - Version 1.2.3 added to supported versions table
- [x] `chocolatey/zone-new-companion.nuspec` - Version updated to 1.2.3

### 2. Documentation
- [x] Comprehensive prerequisites guides added to README.md:
  - Windows (Chocolatey/winget and manual)
  - Linux (Ubuntu, Fedora, Arch, openSUSE, Solus, Void, Alpine)
  - macOS (Homebrew/MacPorts and manual)
- [x] BUILD.md with detailed build instructions

### 3. Code Quality
- [x] Full codebase audit completed
- [x] All imports verified working
- [x] Fixed Timeout import in network_optimizer.py
- [x] Type annotations complete throughout
- [x] No syntax errors found

### 4. Windows Build
- [x] Windows .exe built successfully
- [x] File: `dist/zone-new-companion.exe` (104 MB)
- [x] Icon properly embedded
- [x] All dependencies bundled

### 5. GitHub Push
- [x] All changes committed
- [x] Pushed to main branch

---

## 📦 MANUAL RELEASE INSTRUCTIONS

### Create GitHub Release

1. Go to: https://github.com/kidpoleon/zone-new-companion/releases
2. Click "Draft a new release"
3. Create tag: `v1.2.3`
4. Target: `main` branch
5. Title: `v1.2.3 - Prerequisites Guide & Bug Fixes`
6. Description:

```markdown
## Release v1.2.3

### 🎉 New Features
- Comprehensive step-by-step prerequisites installation guides
- Support for all major Linux distributions
- Windows package manager support (Chocolatey/winget)

### 🔧 Bug Fixes
- Fixed `Timeout` import error in network_optimizer.py
- Fixed all bare `except:` clauses for proper exception handling
- Code quality improvements and audit

### 📦 Downloads
| Platform | File |
|----------|------|
| Windows | zone-new-companion-1.2.3.exe |
| Linux | zone-new-companion-1.2.3.AppImage |
| macOS | Zone-New-Companion-1.2.3.dmg |

### 🚀 Quick Install

**Windows (Chocolatey):**
```powershell
choco install python vlc tesseract ffmpeg git -y
```

**Ubuntu/Debian:**
```bash
sudo apt install python3 python3-pip vlc tesseract-ocr ffmpeg git
```

**macOS (Homebrew):**
```bash
brew install python vlc tesseract ffmpeg git
```

See README.md for detailed prerequisites guides for all platforms.

### ⚠️ Known Issues
- Linux AppImage requires manual build on Linux system
- macOS build requires Mac machine with Xcode

### 📝 SHA256 Checksums
```
[Will be added after upload]
```
```

7. Attach binaries:
   - `dist/zone-new-companion.exe` → Rename to `zone-new-companion-1.2.3.exe`
   - Linux AppImage (if built separately)
   - macOS DMG (if built separately)

8. Click "Publish release"

---

## 🍫 CHOCOLATEY PUBLISH (Optional)

### Prerequisites
- Chocolatey account: https://chocolatey.org/account
- API Key from your Chocolatey account

### Steps

1. **Install Chocolatey CLI tools:**
   ```powershell
   choco install chocolatey -y
   ```

2. **Set API Key:**
   ```powershell
   choco apikey --key <YOUR_API_KEY> --source https://push.chocolatey.org/
   ```

3. **Create Package:**
   ```powershell
   cd chocolatey
   choco pack
   ```

4. **Push Package:**
   ```powershell
   choco push zone-new-companion.1.2.3.nupkg --source https://push.chocolatey.org/
   ```

### Note on Version 1.2.0
Chocolatey packages cannot be "unpublished" - they can only be:
- **Unlisted**: Still available but not shown in search results
- **Deprecated**: Marked with deprecation notice

To unlist 1.2.0, contact Chocolatey moderators or use the web interface.

---

## 🐧 BUILDING LINUX APPIMAGE

Since you're on Windows, you need to build the Linux AppImage separately:

### Option 1: Use WSL2 (Windows Subsystem for Linux)

```powershell
wsl --install -d Ubuntu
# Restart, then in WSL:
sudo apt update
sudo apt install python3 python3-pip python3-venv vlc tesseract-ocr ffmpeg git
# Clone repo and build following BUILD.md instructions
```

### Option 2: Use Docker

```powershell
docker run --rm -v "${PWD}:/app" -w /app ubuntu:22.04 bash -c "
  apt-get update && apt-get install -y python3 python3-pip python3-venv vlc tesseract-ocr ffmpeg git
  pip3 install pyinstaller -r requirements.txt
  pyinstaller zone-new-companion.spec
  # Then create AppImage following BUILD.md
"
```

### Option 3: Build on Linux VM/Cloud

1. Create Ubuntu VM (AWS EC2, Azure, Google Cloud, etc.)
2. Follow BUILD.md Linux instructions
3. Download the resulting AppImage

---

## 📋 VERIFICATION CHECKLIST

Before marking release complete:

- [ ] Windows .exe launches without errors
- [ ] Linux AppImage launches without errors (if built)
- [ ] macOS DMG installs and launches (if built)
- [ ] VLC integration works
- [ ] Xtream connection works
- [ ] Stalker connection works
- [ ] M3U playlist works
- [ ] Stream playback verified
- [ ] Icon shows properly in taskbar/dock
- [ ] Version shows as 1.2.3 in window title

---

## 🆘 TROUBLESHOOTING

### Windows .exe Issues
- **MSVCP140.dll missing**: Install Visual C++ Redistributable
- **Icon not showing**: Ensure icon.ico is valid multi-resolution file
- **Antivirus blocks**: Add to exclusions or sign the executable

### Linux AppImage Issues
- **Cannot execute**: `chmod +x zone-new-companion.AppImage`
- **Missing libs**: Install system dependencies listed in README.md

### macOS Issues
- **"App is damaged"**: Right-click → Open, or code sign
- **Icon not showing**: Ensure icon.icns has all required sizes

---

## 📞 SUPPORT

For issues:
- GitHub Issues: https://github.com/kidpoleon/zone-new-companion/issues
- Email: kidpoleon@proton.me

---

**Release Date:** 2025-01-XX
**Maintainer:** Kidpoleon
