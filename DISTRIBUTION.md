# Distribution Guide

This document explains how to distribute Zone New Companion through various package managers.

## Table of Contents

- [Windows - Chocolatey](#windows---chocolatey)
- [Manual Installation](#manual-installation)

---

## Windows - Chocolatey

Chocolatey is a package manager for Windows that simplifies software installation.

### Prerequisites

1. Install Chocolatey:
   ```powershell
   Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
   ```

2. Install `choco` package tool:
   ```powershell
   choco install chocolatey-core.extension
   ```

### Building the Package

1. Copy the built executable to the chocolatey tools folder:
   ```powershell
   Copy-Item "dist\zone-new-companion.exe" "chocolatey\tools\zone-new-companion.exe"
   ```

2. Navigate to the chocolatey folder:
   ```powershell
   cd chocolatey
   ```

3. Create the package:
   ```powershell
   choco pack
   ```

4. Test the package locally:
   ```powershell
   choco install zone-new-companion -source . -force
   ```

### Publishing to Chocolatey Community Repository

1. Get an API key from https://community.chocolatey.org/account

2. Set the API key:
   ```powershell
   choco apikey --key <your-api-key> --source https://push.chocolatey.org/
   ```

3. Push the package:
   ```powershell
   choco push zone-new-companion.1.2.0.nupkg --source https://push.chocolatey.org/
   ```

4. Wait for moderation (usually 1-2 business days)

### Maintenance

To update the package for a new version:
1. Update version in `zone-new-companion.nuspec`
2. Update release notes URL
3. Build and push new package

---

## Manual Installation

### Windows

1. Download `zone-new-companion.exe` from GitHub Releases
2. Place it in a folder (e.g., `C:\Program Files\Zone New Companion\`)
3. Create a shortcut on the Desktop or Start Menu
4. VLC must be installed separately from https://videolan.org

### macOS

1. Download the macOS release from GitHub
2. Drag `Zone New Companion.app` to Applications folder
3. VLC must be installed separately via DMG or Homebrew:
   ```bash
   brew install --cask vlc
   ```

### Linux

1. Download the AppImage or binary from GitHub Releases
2. Make it executable:
   ```bash
   chmod +x zone-new-companion
   ```
3. Run it:
   ```bash
   ./zone-new-companion
   ```
4. Or install to system:
   ```bash
   sudo cp zone-new-companion /usr/local/bin/
   sudo cp zone-new-companion.desktop /usr/share/applications/
   ```

---

## VLC Compatibility

The application requires VLC to be installed separately:

| Platform | VLC Installation Methods |
|----------|-------------------------|
| Windows | Chocolatey: `choco install vlc`, Microsoft Store, or videolan.org |
| macOS | Homebrew: `brew install --cask vlc`, or videolan.org |
| Linux | apt: `sudo apt install vlc`, snap: `sudo snap install vlc`, or flatpak |

The application will automatically detect VLC in common installation locations.

---

## Notes for Maintainers

### FOSS Compliance

- All dependencies are open source
- No proprietary components included
- MIT Licensed
- VLC is a separate dependency (GPL-2.0+)

### Security

- Chocolatey packages are moderated by community
- No elevated privileges required to run
- User data stored in standard locations:
  - Windows: `%USERPROFILE%\.zone-new-companion\`
  - Linux/macOS: `~/.zone-new-companion/`

---

## Troubleshooting

### Chocolatey

- Package not found: Wait for moderation to complete
- Installation fails: Check VLC is installed first
- Upgrade issues: `choco upgrade zone-new-companion --force`

---

## Contact

For distribution issues, open an issue on GitHub:
https://github.com/kidpoleon/zone-new-companion/issues
