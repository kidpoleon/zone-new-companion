<div align="center">

![Zone New Companion](media/logo.png)

# Zone New Companion

[![Version](https://img.shields.io/badge/version-1.1.8-blue.svg)](https://github.com/kidpoleon/zone-new-companion/releases)
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
- Python 3.8+
- VLC media player
- (Optional) Tesseract OCR for enhanced validation

### Quick Start

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

### Windows Executable

Download the pre-built executable from [Releases](https://github.com/kidpoleon/zone-new-companion/releases):

1. Navigate to **Releases** → **Assets**
2. Download `zone-new-companion.exe`
3. Double-click to run — no installation required

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
- Built with PyQt6, VLC, FFmpeg, and Tesseract

---

<div align="center">

**[⬆ Back to top](#zone-new-companion)**

Made with ❤️ by the IPTV community

</div>
