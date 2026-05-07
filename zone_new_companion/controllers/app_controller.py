"""Application controller."""

from __future__ import annotations

import logging
import re
from typing import Callable

from PyQt6.QtCore import QThreadPool

from zone_new_companion.config import AppConfig, ConfigStore
from zone_new_companion.models import Credentials, MediaItem, PlaylistCategory, PortalType
from zone_new_companion.services.base import PortalService
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
        return self._services[profile.portal_type]

    def _validate_input(self, credentials: Credentials) -> str | None:
        if not credentials.base_url:
            return "Base URL is required."
        if re.search(r"\s", credentials.base_url):
            return "Base URL must not contain spaces."
        if credentials.portal_type == PortalType.XTREAM and (
            not credentials.username or not credentials.password
        ):
            return "Xtream mode requires username and password."
        if credentials.portal_type == PortalType.STALKER and not credentials.mac_address:
            return "Stalker mode requires MAC address."
        if credentials.portal_type == PortalType.STALKER and not re.match(
            r"^[0-9a-fA-F]{2}(:[0-9a-fA-F]{2}){5}$",
            credentials.mac_address,
        ):
            return "MAC address must match format 00:11:22:33:44:55."
        return None

    def connect(self, credentials: Credentials, on_success: Callable[[str], None], on_error: Callable[[str], None]) -> None:
        """Load categories asynchronously and persist profile."""
        self._config.last_input = credentials
        self._config_store.save(self._config)
        validation_error = self._validate_input(credentials)
        if validation_error:
            on_error(validation_error)
            return

        self._state_store.update(
            active_profile=credentials,
            busy=True,
            status_text=f"Connecting to {credentials.base_url}",
        )

        def task() -> tuple[dict[str, list[PlaylistCategory]], dict[str, str]]:
            service = self._service_for(credentials)
            categories = service.fetch_categories(credentials)
            info = service.fetch_connection_info(credentials)
            return categories, info

        worker = TaskWorker(task)
        worker.signals.succeeded.connect(lambda payload: self._on_connected(credentials, payload, on_success))
        worker.signals.failed.connect(lambda message: self._on_error(message, on_error))
        worker.signals.finished.connect(lambda: self._state_store.update(busy=False))
        self._thread_pool.start(worker)

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
            live_epg=[],
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
        self._state_store.update(
            current_items=current,
            verification_results=verification,
            status_text=f"{len(items)} items loaded.",
        )
        on_success(f"{tab_name}: {len(items)} entries")

    def load_live_epg(
        self,
        channel_item: MediaItem,
        on_success: Callable[[str], None],
        on_error: Callable[[str], None],
    ) -> None:
        """Load EPG rows for the selected live channel."""
        profile = self._state_store.state.active_profile
        if profile is None:
            on_error("No active profile.")
            return
        if self._state_store.state.busy:
            return
        self._state_store.update(busy=True, status_text=f"Loading EPG for {channel_item.name}")

        def task() -> list:
            return self._service_for(profile).fetch_epg_for_channel(profile, channel_item)

        worker = TaskWorker(task)
        worker.signals.succeeded.connect(
            lambda epg_rows: self._state_store.update(
                live_epg=epg_rows,
                status_text=f"EPG loaded: {len(epg_rows)} rows",
            ),
        )
        worker.signals.succeeded.connect(lambda _rows: on_success("EPG updated"))
        worker.signals.failed.connect(lambda message: self._on_error(message, on_error))
        worker.signals.finished.connect(lambda: self._state_store.update(busy=False))
        self._thread_pool.start(worker)

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

    def _on_verify_done(
        self,
        tab_name: str,
        results: dict[str, str],
        on_success: Callable[[str], None],
    ) -> None:
        verification = dict(self._state_store.state.verification_results)
        verification[tab_name] = results
        ok_count = sum(1 for status in results.values() if status.startswith("OK"))
        self._state_store.update(
            verification_results=verification,
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
            live_epg=[],
            status_text="Form reset.",
        )
        self._navigation_stack = {"Live": [], "Movies": [], "Series": []}

    def _remember_success(self, credentials: Credentials) -> None:
        LOGGER.info("Saving successful connection for %s", credentials.base_url)
        key = (credentials.base_url, credentials.portal_type.value, credentials.username, credentials.mac_address)
        history: list[Credentials] = []
        for entry in self._config.successful_history:
            entry_key = (entry.base_url, entry.portal_type.value, entry.username, entry.mac_address)
            if entry_key != key:
                history.append(entry)
        history.insert(0, credentials)
        self._config.successful_history = history[:20]
        self._config_store.save(self._config)

    def _on_error(self, message: str, callback: Callable[[str], None]) -> None:
        LOGGER.exception("Operation failed: %s", message)
        self._state_store.update(status_text=f"Error: {message}")
        callback(message)

    def save_ui_state(self, width: int, height: int) -> None:
        """Persist current window size."""
        self._config.ui.width = width
        self._config.ui.height = height
        self._config_store.save(self._config)
