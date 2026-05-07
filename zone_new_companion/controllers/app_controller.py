"""Application controller."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Callable
from urllib.parse import parse_qs, urlparse

from zone_new_companion.services.logger_service import logger_service

from PyQt6.QtCore import QThreadPool

from zone_new_companion.config import AppConfig, ConfigStore
from zone_new_companion.models import Credentials, MediaItem, PlaylistCategory, PortalType
from zone_new_companion.services.base import PortalService
from zone_new_companion.services.m3u_service import M3UService
from zone_new_companion.services.player_launcher import launch_stream
from zone_new_companion.services.stalker_service import StalkerService
from zone_new_companion.services.stream_verifier import StreamVerifier
from zone_new_companion.services.xtream_service import XtreamService
from zone_new_companion.state import StateStore
from zone_new_companion.workers.task_worker import TaskWorker

LOGGER = logging.getLogger(__name__)


class AppController:
    """Coordinate UI events, state, and services."""

    def __init__(self, state_store: StateStore, config_store: ConfigStore) -> None:
        self._state_store = state_store
        self._config_store = config_store
        self._config: AppConfig = config_store.load()
        self._thread_pool = QThreadPool.globalInstance()
        self._services: dict[PortalType, PortalService] = {
            PortalType.XTREAM: XtreamService(),
            PortalType.M3U: M3UService(),
            PortalType.STALKER: StalkerService(),
        }
        self._verifier = StreamVerifier()
        self._navigation_stack: dict[str, list[list[MediaItem]]] = {"Live": [], "Movies": [], "Series": []}

    @property
    def config(self) -> AppConfig:
        return self._config

    def history_entries(self) -> list[Credentials]:
        """Return successful credential history."""
        return list(self._config.successful_history)

    def _service_for(self, profile: Credentials) -> PortalService:
        """Get the appropriate service for the given profile."""
        try:
            service = self._services.get(profile.portal_type)
            if service is None:
                raise ValueError(f"Unsupported portal type: {profile.portal_type}")
            return service
        except Exception as e:
            LOGGER.error(f"Failed to get service for portal type {profile.portal_type}: {e}")
            raise

    def _validate_input(self, credentials: Credentials) -> str | None:
        """Validate input credentials with comprehensive error checking."""
        try:
            if not credentials.base_url:
                return "Base URL is required."
            
            # Validate URL format
            if not credentials.base_url.startswith(('http://', 'https://')):
                return "Base URL must start with http:// or https://"
            
            if re.search(r"\s", credentials.base_url):
                return "Base URL must not contain spaces."
            
            # Portal-specific validation
            if credentials.portal_type == PortalType.XTREAM:
                if not credentials.username or not credentials.password:
                    return "Xtream mode requires username and password."
                if len(credentials.username) < 3:
                    return "Username must be at least 3 characters long."
                    
            elif credentials.portal_type == PortalType.M3U:
                if not credentials.base_url:
                    return "M3U mode requires a valid playlist URL."
                # Additional M3U validation
                if not any(ext in credentials.base_url.lower() for ext in ['.m3u', '.m3u8', 'get.php']):
                    LOGGER.warning("M3U URL doesn't contain typical M3U indicators")
                    
            elif credentials.portal_type == PortalType.STALKER:
                if not credentials.mac_address:
                    return "Stalker mode requires MAC address."
                if not re.match(
                    r"^[0-9a-fA-F]{2}(:[0-9a-fA-F]{2}){5}$",
                    credentials.mac_address,
                ):
                    return "MAC address must match format 00:11:22:33:44:55."
            
            return None
            
        except Exception as e:
            LOGGER.error(f"Validation error: {e}")
            return f"Validation failed: {e}"

    def _normalize_credentials(self, credentials: Credentials) -> Credentials:
        """Normalize user input, including Xtream get.php links."""
        base = credentials.base_url.strip()
        if credentials.portal_type != PortalType.XTREAM:
            return credentials

        parsed = urlparse(base)
        if parsed.path.endswith("/get.php"):
            params = parse_qs(parsed.query)
            username = (params.get("username") or [credentials.username])[0]
            password = (params.get("password") or [credentials.password])[0]
            host = parsed.hostname or ""
            scheme = parsed.scheme or "http"
            port = f":{parsed.port}" if parsed.port else ""
            base = f"{scheme}://{host}{port}"
            return Credentials(
                name=credentials.name,
                base_url=base,
                portal_type=credentials.portal_type,
                username=username,
                password=password,
                mac_address=credentials.mac_address,
                saved_at=credentials.saved_at,
            )
        return credentials

    def connect(self, credentials: Credentials, on_success: Callable[[str], None], on_error: Callable[[str], None]) -> None:
        """Load categories asynchronously and persist profile."""
        try:
            logger_service.info(f"Starting connection to {credentials.base_url}")
            logger_service.debug(f"Portal type: {credentials.portal_type}")
            
            credentials = self._normalize_credentials(credentials)
            self._config.last_input = credentials
            self._config_store.save(self._config)
            validation_error = self._validate_input(credentials)
            if validation_error:
                on_error(validation_error)
                return

            service = self._service_for(credentials)
            
            logger_service.info(f"Using service: {service.__class__.__name__}")
            
            self._state_store.update(
                active_profile=credentials,
                busy=True,
                status_text=f"Connecting to {credentials.base_url}",
            )

            def task() -> tuple[dict[str, list[PlaylistCategory]], dict[str, str]]:
                logger_service.debug("Fetching categories and connection info...")
                categories = service.fetch_categories(credentials)
                info = service.fetch_connection_info(credentials)
                logger_service.info(f"Retrieved {len(categories)} categories")
                return categories, info

            worker = TaskWorker(task)
            worker.signals.succeeded.connect(lambda payload: self._on_connected(credentials, payload, on_success))
            worker.signals.failed.connect(lambda message: self._on_error(message, on_error))
            worker.signals.finished.connect(lambda: self._state_store.update(busy=False))
            self._thread_pool.start(worker)
            
            logger_service.info("Connection task started")
        except Exception as exc:
            logger_service.error(f"Connection failed: {exc}")
            on_error(str(exc))

    def _on_connected(
        self,
        credentials: Credentials,
        payload: tuple[dict[str, list[PlaylistCategory]], dict[str, str]],
        on_success: Callable[[str], None],
    ) -> None:
        categories, connection_info = payload
        self._remember_success(credentials)
        self._state_store.update(
            categories=categories,
            credential_info=connection_info,
            status_text="Playlist categories loaded.",
        )
        on_success(f"Connected ({credentials.portal_type.value})")

    def load_items(
        self,
        tab_name: str,
        category: PlaylistCategory,
        on_success: Callable[[str], None],
        on_error: Callable[[str], None],
    ) -> None:
        """Load category items asynchronously."""
        state = self._state_store.state
        profile = state.active_profile
        if profile is None:
            on_error("No active profile.")
            return
        if self._state_store.state.busy:
            on_error("Another operation is in progress.")
            return
        self._state_store.update(busy=True, status_text=f"Loading {tab_name} items...")

        def task() -> list[MediaItem]:
            return self._service_for(profile).fetch_items(profile, category)

        worker = TaskWorker(task)
        worker.signals.succeeded.connect(
            lambda items: self._on_items_loaded(tab_name, items, on_success, push_stack=False),
        )
        worker.signals.failed.connect(lambda message: self._on_error(message, on_error))
        worker.signals.finished.connect(lambda: self._state_store.update(busy=False))
        self._thread_pool.start(worker)

    def _on_items_loaded(
        self,
        tab_name: str,
        items: list[MediaItem],
        on_success: Callable[[str], None],
        *,
        push_stack: bool,
    ) -> None:
        current = dict(self._state_store.state.current_items)
        if push_stack and current.get(tab_name):
            self._navigation_stack[tab_name].append(list(current[tab_name]))
        current[tab_name] = items
        verification = dict(self._state_store.state.verification_results)
        verification[tab_name] = {}
        now_playing = dict(self._state_store.state.now_playing)
        now_playing[tab_name] = {}
        self._state_store.update(
            current_items=current,
            verification_results=verification,
            now_playing=now_playing,
            status_text=f"{len(items)} items loaded.",
        )
        on_success(f"{tab_name}: {len(items)} entries")

        # Lightweight "now playing" prefetch for Live tab.
        if tab_name == "Live":
            self._prefetch_now_playing(items[:10])

    def play(self, item: MediaItem, on_success: Callable[[str], None], on_error: Callable[[str], None]) -> None:
        """Resolve stream and launch VLC asynchronously."""
        profile = self._state_store.state.active_profile
        if profile is None:
            on_error("No active profile.")
            return
        if self._state_store.state.busy:
            on_error("Another operation is in progress.")
            return

        self._state_store.update(busy=True, status_text=f"Resolving stream for {item.name}")

        def task() -> str:
            stream_url = self._service_for(profile).resolve_stream_url(profile, item)
            launch_stream(stream_url)
            return stream_url

        worker = TaskWorker(task)
        worker.signals.succeeded.connect(lambda _: on_success(f"Playing {item.name}"))
        worker.signals.failed.connect(lambda message: self._on_error(message, on_error))
        worker.signals.finished.connect(lambda: self._state_store.update(busy=False, status_text="Ready"))
        self._thread_pool.start(worker)

    def activate_item(
        self,
        tab_name: str,
        item: MediaItem,
        on_success: Callable[[str], None],
        on_error: Callable[[str], None],
    ) -> None:
        """Handle navigation or playback by item type."""
        if item.item_type in {"series", "season"}:
            self._expand_series_item(tab_name, item, on_success, on_error)
            return
        self.play(item, on_success=on_success, on_error=on_error)

    def _expand_series_item(
        self,
        tab_name: str,
        item: MediaItem,
        on_success: Callable[[str], None],
        on_error: Callable[[str], None],
    ) -> None:
        profile = self._state_store.state.active_profile
        if profile is None:
            on_error("No active profile.")
            return
        self._state_store.update(busy=True, status_text=f"Loading children for {item.name}")

        def task() -> list[MediaItem]:
            return self._service_for(profile).fetch_series_children(profile, item)

        worker = TaskWorker(task)
        worker.signals.succeeded.connect(
            lambda items: self._on_items_loaded(tab_name, items, on_success, push_stack=True),
        )
        worker.signals.failed.connect(lambda message: self._on_error(message, on_error))
        worker.signals.finished.connect(lambda: self._state_store.update(busy=False))
        self._thread_pool.start(worker)

    def go_back(self, tab_name: str) -> bool:
        """Pop last media view for a tab."""
        if not self._navigation_stack[tab_name]:
            return False
        previous = self._navigation_stack[tab_name].pop()
        current = dict(self._state_store.state.current_items)
        current[tab_name] = previous
        verification = dict(self._state_store.state.verification_results)
        verification[tab_name] = {}
        self._state_store.update(
            current_items=current,
            verification_results=verification,
            status_text="Returned to previous list.",
        )
        return True

    def verify_tab_streams(
        self,
        tab_name: str,
        on_success: Callable[[str], None],
        on_error: Callable[[str], None],
    ) -> None:
        """Verify current tab streams for reachability and A/V."""
        profile = self._state_store.state.active_profile
        if profile is None:
            on_error("No active profile.")
            return
        tab_items = self._state_store.state.current_items.get(tab_name, [])
        if not tab_items:
            on_error("No loaded items to verify.")
            return
        if self._state_store.state.busy:
            on_error("Another operation is in progress.")
            return
        self._state_store.update(busy=True, status_text=f"Verifying {len(tab_items)} streams...")

        def task() -> dict[str, str]:
            service = self._service_for(profile)
            return self._verifier.verify_items(service, profile, tab_items)

        worker = TaskWorker(task)
        worker.signals.succeeded.connect(
            lambda results: self._on_verify_done(tab_name, results, on_success),
        )
        worker.signals.failed.connect(lambda message: self._on_error(message, on_error))
        worker.signals.finished.connect(lambda: self._state_store.update(busy=False))
        self._thread_pool.start(worker)

    def verify_single_item(
        self,
        tab_name: str,
        item: MediaItem,
        on_success: Callable[[str], None],
        on_error: Callable[[str], None],
    ) -> None:
        profile = self._state_store.state.active_profile
        if profile is None:
            on_error("No active profile.")
            return
        if item.item_type not in {"channel", "vod", "episode"}:
            on_error("Item is not a playable stream.")
            return

        self._state_store.update(
            status_text=f"Priority verifying {item.name}...",
            priority_verification_active=True
        )

        def task() -> dict[str, str]:
            service = self._service_for(profile)
            # Increase threads for priority verification
            original_max = self._thread_pool.maxThreadCount()
            self._thread_pool.setMaxThreadCount(original_max + 4)
            try:
                result = self._verifier.verify_item(service, profile, item)
                return {item.id: result.status}
            finally:
                self._thread_pool.setMaxThreadCount(original_max)

        worker = TaskWorker(task)
        worker.signals.succeeded.connect(lambda result_map: self._on_verify_done(tab_name, result_map, on_success))
        worker.signals.failed.connect(lambda message: self._on_error(message, on_error))
        self._thread_pool.start(worker)

    def verify_all_channels(
        self,
        tab_name: str,
        on_success: Callable[[str], None],
        on_error: Callable[[str], None],
    ) -> None:
        """Verify all channels in the current tab efficiently."""
        profile = self._state_store.state.active_profile
        if profile is None:
            on_error("No active profile.")
            return

        items = self._state_store.state.current_items.get(tab_name, [])
        if not items:
            on_error("No items to verify in this tab.")
            return

        self._state_store.update(status_text=f"Verifying all {len(items)} channels in {tab_name}...")

        def task() -> dict[str, str]:
            service = self._service_for(profile)
            # Multiply threads by 2 for verify all requests
            original_max = self._thread_pool.maxThreadCount()
            self._thread_pool.setMaxThreadCount(original_max * 2)
            try:
                # Use optimized worker count for large batches
                worker_count = min(48, max(16, len(items) // 5))
                return self._verifier.verify_items(service, profile, items, workers=worker_count)
            finally:
                self._thread_pool.setMaxThreadCount(original_max)

        worker = TaskWorker(task)
        worker.signals.succeeded.connect(lambda result_map: self._on_verify_done(tab_name, result_map, on_success))
        worker.signals.failed.connect(lambda message: self._on_error(message, on_error))
        self._thread_pool.start(worker)

    def verify_tab(
        self,
        tab_name: str,
        on_success: Callable[[str], None],
        on_error: Callable[[str], None],
    ) -> None:
        """Verify all channels in a specific tab from menu."""
        self.verify_all_channels(tab_name, on_success, on_error)

    def cancel_verification(
        self,
        on_success: Callable[[str], None],
        on_error: Callable[[str], None],
    ) -> None:
        """Cancel all ongoing verification processes."""
        try:
            logger_service.info("Cancelling all verification processes")
            # Clear verification queue and stop background verification
            self._state_store.update(
                background_verification_active=False,
                verification_queue=[],
                priority_verification_active=False,
                busy=False
            )
            on_success("All verification processes cancelled.")
            logger_service.info("Verification processes cancelled successfully")
        except Exception as e:
            logger_service.error(f"Failed to cancel verification: {e}")
            on_error(f"Failed to cancel verification: {e}")

    def clear_logs(self) -> None:
        """Clear all logs."""
        logger_service.clear_logs()

    def show_logs(self) -> None:
        """Show logs window."""
        from zone_new_companion.ui.log_viewer import LogViewerDialog
        log_viewer = LogViewerDialog()
        log_viewer.exec()

    def save_logs(self) -> None:
        """Save logs to file."""
        from datetime import datetime
        from pathlib import Path
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_path = Path.home() / f"zone_new_companion_logs_{timestamp}.txt"
        
        try:
            logger_service.save_logs_to_file(default_path)
            logger_service.info(f"Logs saved to {default_path}")
        except Exception as e:
            logger_service.error(f"Failed to save logs: {e}")

    def request_now_playing(
        self,
        tab_name: str,
        item: MediaItem,
    ) -> None:
        profile = self._state_store.state.active_profile
        if profile is None:
            return
        if item.item_type != "channel":
            return
        cached = self._state_store.state.now_playing.get(tab_name, {}).get(item.id, "")
        if cached:
            return

        def task() -> tuple[str, str]:
            title = self._service_for(profile).fetch_now_playing(profile, item)
            return item.id, title

        worker = TaskWorker(task)
        worker.signals.succeeded.connect(lambda pair: self._on_now_playing(tab_name, pair))
        self._thread_pool.start(worker)

    def _on_now_playing(self, tab_name: str, payload: tuple[str, str]) -> None:
        item_id, title = payload
        if not title:
            return
        now_playing = dict(self._state_store.state.now_playing)
        tab_map = dict(now_playing.get(tab_name, {}))
        tab_map[item_id] = title
        now_playing[tab_name] = tab_map
        self._state_store.update(now_playing=now_playing)

    def _prefetch_now_playing(self, items: list[MediaItem]) -> None:
        for item in items:
            if item.item_type == "channel":
                self.request_now_playing("Live", item)

    def _on_verify_done(
        self,
        tab_name: str,
        results: dict[str, str],
        on_success: Callable[[str], None],
    ) -> None:
        # Update current tab verification results
        verification = dict(self._state_store.state.verification_results)
        verification[tab_name] = results
        
        # Update persistent verification results (survives category changes)
        persistent_results = dict(self._state_store.state.persistent_verification_results)
        persistent_results.update(results)
        
        ok_count = sum(1 for status in results.values() if status.startswith("OK"))
        self._state_store.update(
            verification_results=verification,
            persistent_verification_results=persistent_results,
            status_text=f"Verification done: {ok_count}/{len(results)} reachable.",
        )
        on_success(f"Verification done: {ok_count}/{len(results)}")

    def reset_form(self) -> None:
        """Reset state without losing saved profiles."""
        self._state_store.update(
            active_profile=None,
            categories={"Live": [], "Movies": [], "Series": []},
            current_items={"Live": [], "Movies": [], "Series": []},
            verification_results={"Live": {}, "Movies": {}, "Series": {}},
            credential_info={},
            now_playing={"Live": {}, "Movies": {}, "Series": {}},
            status_text="Form reset.",
        )
        self._navigation_stack = {"Live": [], "Movies": [], "Series": []}

    def _remember_success(self, credentials: Credentials) -> None:
        LOGGER.info("Saving successful connection for %s", credentials.base_url)
        stamped = Credentials(
            name=credentials.name,
            base_url=credentials.base_url,
            portal_type=credentials.portal_type,
            username=credentials.username,
            password=credentials.password,
            mac_address=credentials.mac_address,
            saved_at=datetime.now().astimezone().isoformat(timespec="seconds"),
        )
        key = (credentials.base_url, credentials.portal_type.value, credentials.username, credentials.mac_address)
        history: list[Credentials] = []
        for entry in self._config.successful_history:
            entry_key = (entry.base_url, entry.portal_type.value, entry.username, entry.mac_address)
            if entry_key != key:
                history.append(entry)
        history.insert(0, stamped)
        self._config.successful_history = history[:20]
        self._config_store.save(self._config)

    def clear_history(self) -> None:
        self._config.successful_history = []
        self._config_store.save(self._config)

    def _on_error(self, message: str, callback: Callable[[str], None]) -> None:
        LOGGER.error("Operation failed: %s", message)
        self._state_store.update(status_text=f"Error: {message}")
        callback(message)

    def save_ui_state(self, width: int, height: int) -> None:
        """Persist current window size."""
        self._config.ui.width = width
        self._config.ui.height = height
        self._config_store.save(self._config)
