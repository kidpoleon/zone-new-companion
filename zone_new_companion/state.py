"""Centralized application state store."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from PyQt6.QtCore import QObject, pyqtSignal

from zone_new_companion.models import Credentials, EpgEntry, MediaItem, PlaylistCategory


@dataclass(slots=True)
class AppState:
    """Immutable-ish application state snapshot."""

    active_profile: Credentials | None = None
    categories: dict[str, list[PlaylistCategory]] = field(
        default_factory=lambda: {"Live": [], "Movies": [], "Series": []},
    )
    current_items: dict[str, list[MediaItem]] = field(
        default_factory=lambda: {"Live": [], "Movies": [], "Series": []},
    )
    verification_results: dict[str, dict[str, str]] = field(
        default_factory=lambda: {"Live": {}, "Movies": {}, "Series": {}},
    )
    credential_info: dict[str, str] = field(default_factory=dict)
    live_epg: list[EpgEntry] = field(default_factory=list)
    status_text: str = "Ready"
    busy: bool = False


class StateStore(QObject):
    """Central state manager with a single signal bus."""

    state_changed = pyqtSignal(object)

    def __init__(self) -> None:
        super().__init__()
        self._state = AppState()

    @property
    def state(self) -> AppState:
        return self._state

    def update(self, **kwargs: object) -> None:
        """Merge and publish a new app state."""
        self._state = replace(self._state, **kwargs)
        self.state_changed.emit(self._state)
