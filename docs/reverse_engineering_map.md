# Deeper Reverse-Engineering Map

## Program A: XTREME-IPTV-PLAYER-by-MY-1

### Internal Architecture
- Monolithic file: `XTREME IPTV PLAYER BY MY-1 v4.0.py`.
- UI: PyQt5 `QMainWindow` with tab-specific list widgets and manual navigation stacks.
- Async model:
  - `QThreadPool` + `QRunnable` (`EPGWorker`) for XMLTV fetch/parse.
  - Main-thread network calls for many playlist operations.
- Data caching:
  - Credentials in `credentials.ini`.
  - EPG cache in `epg_cache1.xml`.
  - Poster/icon caches in temp/home directories.

### External Contracts
- Xtream API:
  - `player_api.php?action=get_live_categories|get_vod_categories|get_series_categories`
  - `player_api.php?action=get_live_streams|get_vod_streams|get_series`
  - `xmltv.php?username=...&password=...` for EPG.
- Direct playback links:
  - Live: `/live/{user}/{pass}/{stream_id}.ts`
  - VOD: `/movie/{user}/{pass}/{stream_id}.{ext}`
  - Series episodes: `/series/{user}/{pass}/{episode_id}.{ext}`
- External dependency:
  - VLC/SMPlayer via subprocess invocation.

## Program B: IPTV-MAC-STALKER-PLAYER-BY-MY-1

### Internal Architecture
- Split modules:
  - `STALKER PLAYER.py` (UI + orchestration + mixed portal flow)
  - `stalker.py` (Stalker protocol/service logic)
  - `Epg.py` (threaded EPG queue, cache, retries)
- Async model:
  - `QThread` workers (`RequestThread`, `StalkerRequestThread`, `EpgManager`).
  - `ThreadPoolExecutor` in service layer for multi-page fetch.
- State model:
  - Tab-specific navigation stacks and current view flags.
  - Token lifecycle and refresh checks.

### External Contracts
- Stalker endpoints:
  - `portal.php?type=stb&action=handshake`
  - `portal.php?type=stb&action=get_profile`
  - `portal.php?type=itv|vod|series&action=get_genres|get_categories|get_ordered_list`
  - `portal.php?action=create_link&type=itv|vod&cmd=...`
- Non-stalker MAC flow:
  - same `portal.php` handshake + bearer cookie/header conventions.
- EPG endpoints:
  - generic `/portal.php`
  - stalker `/stalker_portal/server/load.php` or `/stalker_portal/load.php`.

## Shared Patterns Discovered
- MAG-like user-agent simulation, cookie-based MAC identity.
- Token-dependent stream-link creation before playback.
- Strong need for robust retries, timeout tuning, and pagination.
- Playback offloaded to external media player binary.
- Tooltip-based metadata and EPG-centric UX.

## Unification Strategy Implemented in `zone-new-companion`

1. **Central state store** for categories, items, busy/status, active profile.
2. **Service abstraction** (`PortalService`) with `XtreamService` and `StalkerService`.
3. **Controller layer** coordinating validation, async workers, state updates, persistence.
4. **Reusable UI widgets** (`LoginPanel`, `ToastLabel`, tabbed category/item views).
5. **Cross-platform VLC launch policy** with hardcoded OS-specific executable paths.
6. **Config persistence** via JSON (`~/.zone-new-companion/config.json`).
7. **Async operations** through generic `TaskWorker` + `QThreadPool`.
8. **Non-intrusive UX feedback** with status bar progress + toast notifications.
