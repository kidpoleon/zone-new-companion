# zone-new-companion v1.1.2

Unified desktop IPTV companion app that merges Xtream and Stalker workflows into a single cross-platform PyQt6 application.

## Highlights

- Unified UI for both `xtream` and `stalker` portal types.
- Modular architecture (controllers, services, state store, reusable UI widgets).
- Centralized state management (`StateStore`).
- Async non-blocking operations (`QThreadPool` + `QRunnable` workers).
- Hardcoded VLC executable paths by platform:
  - Windows: `C:\Program Files\VideoLAN\VLC\vlc.exe`
  - Linux: `/usr/bin/vlc`
  - Snap: `/snap/bin/vlc`
  - Flatpak: `/var/lib/flatpak/exports/bin/org.videolan.VLC`
  - macOS: `/Applications/VLC.app/Contents/MacOS/VLC`
- Persistent config at `~/.zone-new-companion/config.json`.
- Last input credentials are restored automatically on next launch.
- Top menu `History` stores only successful connections.
- Status bar progress + toast notifications.
- Confirmation dialog for reset actions.
- Series hierarchy navigation (double-click series/season to drill down).
- Right-click on item list to go back one level.

## v1.1.2 Verification Accuracy & Progress Reporting

- **Fixed False Negatives**: Resolved issue where playable channels showed as red/unverified
- **Optimized Session Usage**: Stream verifier now uses optimized SSL sessions for better compatibility
- **Enhanced Progress Reporting**: Terminal now shows detailed verification progress for each channel
- **Improved Fallback Logic**: Added secondary reachability checks with longer timeouts
- **Better Error Handling**: More permissive verification logic reduces false positives
- **Detailed Logging**: Individual channel status updates with progress percentages
- **Optimized FFprobe**: Improved stream analysis with better timeout handling
- **Permissive Verification**: Streams marked as OK if reachable even if A/V probe fails

## v1.1.1 OCR & Advanced Connection Improvements

- **OCR Service Integration**: Complete OCR service based on IPTV-CHECK project for video stream validation
- **FFmpeg Frame Extraction**: Automatic frame capture from video streams for content analysis
- **Tesseract OCR Engine**: Multi-language text recognition with error detection patterns
- **Advanced DNS Resolution**: Multiple DNS server fallback (Google, Cloudflare, OpenDNS, Quad9)
- **Enhanced Connectivity Testing**: Multiple endpoint testing for better server compatibility
- **Connection Diagnostics**: Comprehensive connection testing with detailed diagnostics
- **Complete Logs Removal**: Fully removed logs functionality from title bar and application
- **Performance Optimization**: Improved connection success rates through advanced strategies

## v1.1.0 SSL & Connection Improvements

- **Multi-Profile SSL Handling**: 4 SSL configuration profiles (default, legacy, permissive, modern) for maximum compatibility
- **SSL Fallback Strategy**: Automatic fallback through different SSL configurations when connection fails
- **HTTP/HTTPS Protocol Rotation**: Automatic protocol switching with caching for optimal connection method
- **Comprehensive Cipher Support**: Support for legacy and modern cipher suites including `ALL:@SECLEVEL=0`
- **Connection Method Caching**: Remembers successful protocols per domain for faster subsequent connections
- **Enhanced Error Recovery**: Better SSL error handling with multiple retry strategies
- **Server-Specific Optimization**: Adaptive SSL configuration based on server response patterns

## v1.0.9 Improvements

- **Network Optimizations**: Added adaptive timeouts and connection pooling for 50x faster credential testing
- **Enhanced Error Handling**: Improved MAC address validation and Stalker service reliability  
- **Performance Metrics**: Added credential health scoring and real-time progress reporting
- **Fast-Fail Logic**: Pre-validation to quickly identify non-responsive servers
- **Better Parsing**: Multiple strategies for Stalker credential format detection
- **Optimized Testing**: Reduced average test time from 10s to 0.2s per credential
- Fullscreen startup by default.
- Live tab includes local-time EPG guide panel.
- `Tools -> Verify Current Tab Streams` runs fast concurrent checks:
  - reachability precheck (including HLS segment reachability)
  - ffprobe JSON verification for audio/video stream presence
  - channel list is annotated with status labels
- v1.0.1 reliability improvements:
  - Xtream `get.php?...` input auto-parsing into API credentials
  - Xtream endpoint fallback (`player_api.php`, `panel_api.php`, `/xtream`)
  - Stalker playback no longer blocked by EPG lookups
  - Stalker stream creation uses proper `type=itv` vs `type=vod`

## Run (Unix: Linux/macOS) - Step by step, safe setup

```bash
cd /home/administrator/Downloads/zone-new-companion
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py
```

Recommended safety notes:

1. Always run inside `venv` to avoid system package conflicts (PEP 668).
2. Keep VLC installed at one of the supported hardcoded paths.
3. Use `Ctrl+C` in terminal to stop the app cleanly.
4. To restart from a clean state, close app and re-run the steps above.

## Windows EXE build (CI-backed)

The real Windows executable is built on GitHub Actions and uses an `.ico` generated in `zone_new_companion/icon/`.

- `zone_new_companion/executable/windows.exe` is a placeholder in-repo.
- The actual artifact is `dist/zone-new-companion.exe` in the workflow output.

## Unix launcher

- `zone_new_companion/executable/unix.sh` is the runtime launcher for Linux/macOS.
- It prefers a packaged binary (`dist/zone-new-companion`), otherwise falls back to source (`python main.py`).
- It uses Wayland by default and safely falls back to XCB if needed.

Workflows:
- `.github/workflows/build-windows.yml`
- `.github/workflows/build-unix.yml`

## Structure

- `zone_new_companion/models.py`: typed domain models.
- `zone_new_companion/state.py`: centralized state store and state signals.
- `zone_new_companion/controllers/app_controller.py`: business orchestration.
- `zone_new_companion/services/`: portal adapters and VLC launcher.
- `zone_new_companion/ui/`: modular UI components.
- `docs/reverse_engineering_map.md`: deeper reverse-engineering map.
