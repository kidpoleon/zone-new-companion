# zone-new-companion v1.0.3

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
