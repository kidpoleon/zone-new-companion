# zone-new-companion v1.1.4

<div align="center">

![Zone New Companion](https://img.shields.io/badge/Zone-New-Companion-blue?style=for-the-badge)
![Version](https://img.shields.io/badge/version-1.1.4-green?style=for-the-badge)
![Python](https://img.shields.io/badge/python-3.8%2B-blue?style=for-the-badge)
![License](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey?style=for-the-badge)

**Unified desktop IPTV companion app that merges Xtream and Stalker workflows into a single cross-platform PyQt6 application.**

[Features](#-features) • [Installation](#-installation) • [Usage](#-usage) • [Configuration](#-configuration) • [Troubleshooting](#-troubleshooting)

</div>

## 📋 Table of Contents

- [Features](#-features)
- [Screenshots](#-screenshots)
- [Installation](#-installation)
  - [Prerequisites](#prerequisites)
  - [VLC Installation](#vlc-installation)
  - [Python Installation](#python-installation)
  - [Application Setup](#application-setup)
- [Usage](#-usage)
  - [Connecting to IPTV Services](#connecting-to-iptv-services)
  - [Supported Portal Types](#supported-portal-types)
  - [Verification System](#verification-system)
  - [OCR Integration](#ocr-integration)
- [Configuration](#-configuration)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## ✨ Features

### 🎯 Core Functionality
- **Unified UI**: Single interface for both `xtream` and `stalker` portal types
- **Modular Architecture**: Clean separation of controllers, services, and UI components
- **Centralized State Management**: Efficient state handling with `StateStore`
- **Async Operations**: Non-blocking operations using `QThreadPool` + `QRunnable` workers
- **Cross-Platform**: Works on Windows, Linux, and macOS

### 🚀 Advanced Features
- **OCR Integration**: Automatic stream validation using frame analysis and text recognition
- **Enhanced Verification**: Multi-stage stream verification with fallback strategies
- **SSL Optimization**: Multiple SSL profiles for maximum server compatibility
- **DNS Fallback**: Automatic DNS server switching for better connectivity
- **Alphabetical Sorting**: Consistent sorting across all categories and items
- **Progress Reporting**: Detailed terminal progress for verification operations

### 🎨 UI/UX Enhancements
- **Modern Dark Theme**: Professional appearance with alternating row colors
- **Enhanced Tooltips**: Helpful guidance for all UI elements
- **Table Sorting**: Sortable columns with visual feedback
- **Status Indicators**: Clear visual feedback for connection states

## 🖼️ Screenshots

*(Screenshots will be added here - consider contributing screenshots!)*

## 🛠️ Installation

### Prerequisites

Before installing zone-new-companion, ensure you have:

1. **Python 3.8 or higher** installed
2. **VLC media player** installed (required for stream playback)
3. **Git** installed (for cloning the repository)

### VLC Installation

VLC is required for stream playback. Install it using your preferred package manager:

#### Windows
```powershell
# Using Winget (Recommended)
winget install VideoLAN.VLC

# Using Chocolatey
choco install vlc

# Using Scoop
scoop install vlc

# Manual download: https://www.videolan.org/vlc/
```

#### Linux (Ubuntu/Debian)
```bash
# Using APT (Recommended)
sudo apt update && sudo apt install vlc

# Using Snap
sudo snap install vlc

# Using Flatpak
flatpak install flathub org.videolan.VLC

# Using Homebrew (Linux)
brew install --cask vlc
```

#### Linux (Fedora/CentOS)
```bash
# Using DNF (Fedora)
sudo dnf install vlc

# Using YUM (CentOS/RHEL)
sudo yum install vlc
```

#### macOS
```bash
# Using Homebrew (Recommended)
brew install --cask vlc

# Manual download: https://www.videolan.org/vlc/
```

### Python Installation

#### Windows
```powershell
# Download from python.org (Recommended)
# Visit: https://www.python.org/downloads/

# Using Winget
winget install Python.Python.3

# Using Chocolatey
choco install python

# Using Scoop
scoop install python
```

#### Linux
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install python3 python3-pip python3-venv

# Fedora/CentOS
sudo dnf install python3 python3-pip

# Arch Linux
sudo pacman -S python python-pip
```

#### macOS
```bash
# Using Homebrew (Recommended)
brew install python3

# Using MacPorts
sudo port install python3
```

### Application Setup

#### Step 1: Clone the Repository
```bash
git clone https://github.com/kidpoleon/zone-new-companion.git
cd zone-new-companion
```

#### Step 2: Create Virtual Environment
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

#### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

#### Step 4: Launch the Application
```bash
python main.py
```

## 📖 Usage

### Connecting to IPTV Services

1. **Launch the Application**: Run `python main.py` after activating the virtual environment
2. **Select Portal Type**: Choose from Xtream, Stalker, or M3U
3. **Enter Credentials**:
   - **Xtream**: Server URL, Username, Password
   - **Stalker**: Portal URL, MAC Address
   - **M3U**: Playlist URL
4. **Click Connect**: The app will fetch categories and channels
5. **Browse Content**: Select categories to view channels/movies/series
6. **Play Content**: Double-click any item to launch in VLC

### Supported Portal Types

#### Xtream Codes API
- Full support for live channels, VOD, and series
- Automatic category and item sorting
- Enhanced connection handling with SSL optimization

#### Stalker Portal
- Complete Stalker middleware compatibility
- Token-based authentication
- EPG support where available

#### M3U Playlists
- Support for local and remote M3U files
- Short URL redirection handling (s.id, bit.ly, etc.)
- Enhanced M3U8 stream verification

### Verification System

The application includes a comprehensive verification system:

- **Quick Reachability**: Fast connection testing
- **Stream Analysis**: FFprobe-based codec detection
- **OCR Validation**: Frame analysis for problematic streams
- **Progress Reporting**: Real-time verification progress

### OCR Integration

For streams that fail traditional verification:
- Automatic frame capture using FFmpeg
- Text recognition using Tesseract OCR
- Error pattern detection (offline, geo-blocked, etc.)
- Multi-language support (English, Portuguese, Spanish, French, German, Italian)

## ⚙️ Configuration

### Settings Location
- **Windows**: `%APPDATA%\zone-new-companion\config.json`
- **Linux**: `~/.zone-new-companion/config.json`
- **macOS**: `~/Library/Application Support/zone-new-companion/config.json`

### Configuration Options
```json
{
  "successful_history": [],
  "last_credentials": {},
  "window_state": {},
  "preferences": {
    "verification_timeout": 30,
    "ocr_enabled": true,
    "ssl_optimization": true
  }
}
```

### VLC Paths
The application automatically detects VLC installation:
- **Windows**: `C:\Program Files\VideoLAN\VLC\vlc.exe`
- **Linux**: `/usr/bin/vlc`
- **Snap**: `/snap/bin/vlc`
- **Flatpak**: `/var/lib/flatpak/exports/bin/org.videolan.VLC`
- **macOS**: `/Applications/VLC.app/Contents/MacOS/VLC`

## 🔧 Troubleshooting

### Common Issues

#### VLC Not Found
```bash
# Verify VLC installation
# Windows
where vlc

# Linux
which vlc

# macOS
which vlc
```

#### Python Module Errors
```bash
# Reinstall dependencies
pip install -r requirements.txt --upgrade

# Clear Python cache
find . -type d -name __pycache__ -exec rm -rf {} +
```

#### Connection Issues
- Check firewall settings
- Verify internet connectivity
- Try different DNS servers
- Check SSL certificate validity

#### Verification Failures
- Ensure OCR dependencies are installed (Tesseract)
- Check FFmpeg installation
- Verify stream URL accessibility

### Debug Mode
Enable debug logging by setting environment variable:
```bash
# Windows
set DEBUG=1
python main.py

# Linux/macOS
DEBUG=1 python main.py
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Setup
```bash
# Clone repository
git clone https://github.com/kidpoleon/zone-new-companion.git
cd zone-new-companion

# Create development environment
python3 -m venv dev-env
source dev-env/bin/activate  # Linux/macOS
# or dev-env\Scripts\activate  # Windows

# Install development dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests
python -m pytest

# Run with debug mode
python main.py --debug
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **PyQt6**: For the cross-platform GUI framework
- **VLC**: For media playback capabilities
- **FFmpeg**: For stream analysis and frame extraction
- **Tesseract**: For OCR functionality
- **IPTV-CHECK**: For OCR implementation inspiration

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/kidpoleon/zone-new-companion/issues)
- **Discussions**: [GitHub Discussions](https://github.com/kidpoleon/zone-new-companion/discussions)
- **Wiki**: [GitHub Wiki](https://github.com/kidpoleon/zone-new-companion/wiki)

## 🔗 Related Projects

- [IPTV-CHECK](https://github.com/peterpt/IPTV-CHECK) - OCR implementation inspiration
- [xtream-ui](https://github.com/mhdzumair/xtream-ui) - Xtream Codes interface reference
- [stalker-portalo](https://github.com/StalkerPortal/stalker-portalo) - Stalker middleware reference

---

<div align="center">

**[⬆ Back to top](#zone-new-companion-v114)**

Made with ❤️ by the IPTV community

</div>
