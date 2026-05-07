"""Domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class PortalType(str, Enum):
    """Supported portal modes."""

    XTREAM = "xtream"
    M3U = "m3u"
    STALKER = "stalker"


@dataclass(slots=True)
class Credentials:
    """User connection credentials."""

    name: str
    base_url: str
    portal_type: PortalType
    username: str = ""
    password: str = ""
    mac_address: str = ""
    saved_at: str = ""


@dataclass(slots=True)
class EpgEntry:
    """A normalized EPG row in local machine timezone."""

    title: str
    start_at: datetime
    end_at: datetime
    description: str = ""


@dataclass(slots=True)
class PlaylistCategory:
    """A logical category in playlist tabs."""

    id: str
    name: str
    media_kind: str


@dataclass(slots=True)
class MediaItem:
    """A media item that can be browsed or played."""

    id: str
    name: str
    media_kind: str
    item_type: str
    metadata: dict[str, Any] = field(default_factory=dict)
    stream_url: str | None = None
