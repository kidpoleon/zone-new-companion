<div align="center">

![Zone New Companion](media/logo.png)

# Zone New Companion

[![Version](https://img.shields.io/badge/version-1.2.3-blue.svg)](https://github.com/kidpoleon/zone-new-companion/releases)
[![Python](https://img.shields.io/badge/python-3.8+-3776ab.svg)](https://www.python.org/)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.7+-41cd52.svg)](https://www.riverbankcomputing.com/software/pyqt/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)]()
[![Downloads](https://img.shields.io/github/downloads/kidpoleon/zone-new-companion/total)]()

**Unified desktop IPTV companion app for Xtream Codes, Stalker Portal, and M3U playlists**

[Download](https://github.com/kidpoleon/zone-new-companion/releases) • [Features](#-features) • [Installation](#-installation) • [Usage](#-usage)

</div>

---

## 📋 Overview

Zone New Companion is a modern, cross-platform PyQt6 application that unifies IPTV workflows into a single intuitive interface. Connect to Xtream Codes, Stalker Portal, or M3U playlists with advanced stream verification and OCR-powered validation.

## ✨ Features

### Core Functionality
- **Unified Interface** — Single UI for Xtream, Stalker, and M3U
- **Modular Architecture** — Clean separation of concerns
- **Async Operations** — Non-blocking UI with QThreadPool
- **Cross-Platform** — Windows, Linux, macOS support

### Advanced Capabilities
- **OCR Integration** — Frame analysis and text recognition
- **Stream Verification** — Multi-stage validation with color-coded results
- **SSL Optimization** — Multiple profiles for server compatibility
- **DNS Fallback** — Automatic server switching
- **Real-Time Updates** — Live progress indicators

### User Experience
- **Dark Theme** — Professional appearance with QDarkStyle
- **History Management** — Persistent credential storage
- **Full-Screen Mode** — Immersive browsing experience
- **Tooltips & Guidance** — Helpful inline documentation

## 🚀 Installation

### Prerequisites

Before running Zone New Companion, ensure you have the following dependencies installed:

#### Required for All Platforms
- **Python 3.8+** — Application runtime
- **VLC Media Player** — Required for streaming playback

#### Optional for OCR Features
- **Tesseract OCR** — Frame text recognition
- **FFmpeg** — Video frame extraction

---

### 📦 Platform-Specific Setup Guides

#### 🪟 Windows

**Option 1: Using Chocolatey (Recommended)**

```powershell
# Install Chocolatey first (if not installed)
# Run PowerShell as Administrator:
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Install all prerequisites
choco install python vlc tesseract ffmpeg git -y
```

**Option 2: Using winget**

```powershell
# Install all prerequisites
winget install Python.Python.3 VideoLAN.VLC TesseractOCR.Tesseract Gyan.FFmpeg Git.Git
```

**Option 3: Manual Installation**
1. **Python**: Download from [python.org](https://www.python.org/downloads/)
2. **VLC**: Download from [videolan.org](https://www.videolan.org/vlc/)
3. **Tesseract**: Download from [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki)
4. **FFmpeg**: Download from [ffmpeg.org](https://ffmpeg.org/download.html)
5. **Git**: Download from [git-scm.com](https://git-scm.com/download/win)

**Add to PATH (if needed):**
- VLC: `C:\Program Files\VideoLAN\VLC`
- Tesseract: `C:\Program Files\Tesseract-OCR`
- FFmpeg: Extract to `C:\ffmpeg\bin`

---

#### 🐧 Linux

**Ubuntu / Debian / Linux Mint / Pop!_OS / Zorin OS**

```bash
# Update package list
sudo apt update

# Install all prerequisites
sudo apt install -y python3 python3-pip python3-venv vlc tesseract-ocr ffmpeg git

# Verify installations
python3 --version
vlc --version
tesseract --version
ffmpeg -version
```

**Fedora / RHEL / CentOS / Rocky Linux / AlmaLinux**

```bash
# Install all prerequisites
sudo dnf install -y python3 python3-pip vlc tesseract ffmpeg git

# For older RHEL/CentOS versions, enable EPEL first:
sudo dnf install epel-release -y
```

**Arch Linux / Manjaro / EndeavourOS / Garuda**

```bash
# Install all prerequisites
sudo pacman -S python python-pip vlc tesseract ffmpeg git --noconfirm
```

**openSUSE / SUSE Linux Enterprise**

```bash
# Install all prerequisites
sudo zypper install -y python3 python3-pip vlc tesseract-ocr ffmpeg git
```

**Solus**

```bash
# Install all prerequisites
sudo eopkg install -y python3 vlc tesseract ffmpeg git
```

**Void Linux**

```bash
# Install all prerequisites
sudo xbps-install -Sy python3 vlc tesseract ffmpeg git
```

**Alpine Linux**

```bash
# Install all prerequisites
sudo apk add --no-cache python3 py3-pip vlc tesseract-ocr ffmpeg git
```

**Snap (Universal Linux)**

```bash
# Install VLC via snap
sudo snap install vlc

# Install other prerequisites via package manager (see above for your distro)
```

**Flatpak (Universal Linux)**

```bash
# Install VLC via flatpak
flatpak install flathub org.videolan.VLC
```

---

#### 🍎 macOS

**Using Homebrew (Recommended)**

```bash
# Install Homebrew first (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install all prerequisites
brew install python vlc tesseract ffmpeg git
```

**Using MacPorts**

```bash
# Install MacPorts first from macports.org

# Install all prerequisites
sudo port install python312 vlc tesseract ffmpeg git
```

**Manual Installation**
1. **Python**: Download from [python.org](https://www.python.org/downloads/macos/)
2. **VLC**: Download from [videolan.org](https://www.videolan.org/vlc/download-macos.html)
3. **Tesseract**: Download installer from GitHub releases
4. **FFmpeg**: Use Homebrew or download from ffmpeg.org
5. **Git**: Download from [git-scm.com](https://git-scm.com/download/mac)

---

### Pre-built Binaries

Download the latest release for your platform from [GitHub Releases](https://github.com/kidpoleon/zone-new-companion/releases):

- **Windows**: `zone-new-companion.exe`
- **Linux**: `zone-new-companion-1.2.3-x86_64.AppImage`
- **macOS**: `Zone New Companion.dmg` or `.app`

#### Quick Download Commands

**Windows (PowerShell):**
```powershell
# Download Windows executable
Invoke-WebRequest -Uri "https://github.com/kidpoleon/zone-new-companion/releases/download/v1.2.3/zone-new-companion.exe" -OutFile "zone-new-companion.exe"
# Run
.\zone-new-companion.exe
```

**Linux:**
```bash
# Download Linux AppImage
wget https://github.com/kidpoleon/zone-new-companion/releases/download/v1.2.3/zone-new-companion-1.2.3-x86_64.AppImage
# Make executable
chmod +x zone-new-companion-1.2.3-x86_64.AppImage
# Run
./zone-new-companion-1.2.3-x86_64.AppImage
```

**macOS:**
```bash
# Download macOS DMG
curl -L -o "Zone-New-Companion-1.2.3.dmg" "https://github.com/kidpoleon/zone-new-companion/releases/download/v1.2.3/Zone-New-Companion-1.2.3.dmg"
# Open
open "Zone-New-Companion-1.2.3.dmg"
```

**Verify Download Integrity:**
```bash
# SHA256 checksums (verify after download)
sha256sum zone-new-companion.exe
sha256sum zone-new-companion-1.2.3-x86_64.AppImage
```

### Build from Source

```bash
# Clone repository
git clone https://github.com/kidpoleon/zone-new-companion.git
cd zone-new-companion

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Launch
python main.py
```

## 📖 Usage

### Connecting to IPTV Services

1. **Launch** the application
2. **Select Portal Type**: Xtream | Stalker | M3U
3. **Enter Credentials**:
   - **Xtream**: URL, Username, Password
   - **Stalker**: URL, MAC Address  
   - **M3U**: Playlist URL
4. **Click Connect** — categories load automatically
5. **Browse & Play** — double-click items to launch in VLC

### Verification System

- 🟢 **Green** — Verified working stream
- 🔴 **Red** — Unreachable or failed
- 🟡 **Yellow** — Unstable/intermittent
- ⚪ **Gray** — Not verified

Right-click any item for verification options.

## ⚙️ Configuration

Settings stored at:
- **Windows**: `%APPDATA%\.zone-new-companion\config.json`
- **Linux**: `~/.zone-new-companion/config.json`
- **macOS**: `~/Library/Application Support/zone-new-companion/config.json`

## 🔧 Troubleshooting

| Issue | Solution |
|-------|----------|
| VLC not found | Install VLC and ensure it's in PATH |
| Connection failed | Check URL format and credentials |
| Icon not showing | Restart Windows Explorer or clear icon cache |

**Debug Mode**: `set DEBUG=1 && python main.py`

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

MIT License — see [LICENSE](LICENSE) file.

## 🙏 Credits

- Original inspiration from [Cyogenus](https://github.com/Cyogenus) IPTV projects
- [IPTV-MAC-STALKER-PLAYER-BY-MY-1](https://github.com/peterpt/IPTV-CHECK) - Stalker implementation reference
- [stalkerhek](https://github.com/CrazeeGhost/stalkerhek/) - Go implementation reference
- Built with PyQt6, VLC, FFmpeg, and Tesseract

---

<div align="center">

**[⬆ Back to top](#zone-new-companion)**

Made with ❤️ by the IPTV community

</div>
