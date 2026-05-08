# Distribution Guide

This document explains how to distribute Zone New Companion through various package managers.

## Table of Contents

- [Windows - Chocolatey](#windows---chocolatey)
- [Linux - Snap Store](#linux---snap-store)
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
   choco push zone-new-companion.1.1.11.nupkg --source https://push.chocolatey.org/
   ```

4. Wait for moderation (usually 1-2 business days)

### Maintenance

To update the package for a new version:
1. Update version in `zone-new-companion.nuspec`
2. Update release notes URL
3. Build and push new package

---

## Linux - Snap Store

Snap is a universal package manager for Linux that works across distributions.

### Prerequisites

1. Install snapcraft:
   ```bash
   sudo snap install snapcraft --classic
   ```

2. Install multipass (for clean build environment):
   ```bash
   sudo snap install multipass
   ```

### Building the Snap

1. Navigate to the project root:
   ```bash
   cd zone-new-companion
   ```

2. Build the snap:
   ```bash
   snapcraft
   ```

   Or with verbose output:
   ```bash
   snapcraft --debug
   ```

3. The snap will be created as `zone-new-companion_1.1.11_amd64.snap`

### Testing Locally

1. Install the snap locally:
   ```bash
   sudo snap install zone-new-companion_1.1.11_amd64.snap --dangerous
   ```

2. Run the application:
   ```bash
   zone-new-companion
   ```

3. Check logs if needed:
   ```bash
   snap logs zone-new-companion
   ```

### Publishing to Snap Store

1. Create a Snap Store account at https://snapcraft.io/account

2. Login to snapcraft:
   ```bash
   snapcraft login
   ```

3. Register the snap name:
   ```bash
   snapcraft register zone-new-companion
   ```

4. Upload the snap:
   ```bash
   snapcraft upload zone-new-companion_1.1.11_amd64.snap --release=stable
   ```

5. Users can then install via:
   ```bash
   sudo snap install zone-new-companion
   ```

### Auto-build with GitHub Actions

Create `.github/workflows/snap.yml`:
```yaml
name: Build and Publish Snap

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: snapcore/action-build@v1
        id: build
      - uses: snapcore/action-publish@v1
        with:
          store-login: ${{ secrets.SNAP_STORE_LOGIN }}
          snap: ${{ steps.build.outputs.snap }}
          release: stable
```

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
- Snap packages are sandboxed by default
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

### Snap

- Permission denied: Check snap connections with `snap connections zone-new-companion`
- VLC not found: Install VLC snap or ensure it's in PATH
- Display issues: Try `QT_QPA_PLATFORM=xcb zone-new-companion`

---

## Contact

For distribution issues, open an issue on GitHub:
https://github.com/kidpoleon/zone-new-companion/issues
