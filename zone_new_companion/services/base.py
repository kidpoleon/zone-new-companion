"""Service interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod

from zone_new_companion.models import Credentials, EpgEntry, MediaItem, PlaylistCategory


class PortalService(ABC):
    """Abstract service for both Xtream and Stalker backends."""

    @abstractmethod
    def fetch_categories(self, credentials: Credentials) -> dict[str, list[PlaylistCategory]]:
        """Fetch categories grouped by tab."""

    @abstractmethod
    def fetch_items(self, credentials: Credentials, category: PlaylistCategory) -> list[MediaItem]:
        """Fetch items for a specific category."""

    @abstractmethod
    def resolve_stream_url(self, credentials: Credentials, item: MediaItem) -> str:
        """Resolve a playable stream URL."""

    def fetch_series_children(self, credentials: Credentials, item: MediaItem) -> list[MediaItem]:
        """Optional series expansion (series -> seasons -> episodes)."""
        return []

    def fetch_connection_info(self, credentials: Credentials) -> dict[str, str]:
        """Fetch account/server metadata for the credential panel."""
        return {}

    def fetch_epg_for_channel(self, credentials: Credentials, channel_item: MediaItem) -> list[EpgEntry]:
        """Fetch EPG for one channel as local machine times."""
        return []
