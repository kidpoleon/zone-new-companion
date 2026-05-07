"""Xtream portal service implementation."""

from __future__ import annotations

from datetime import datetime
from typing import Any
import xml.etree.ElementTree as et

from zone_new_companion.models import Credentials, EpgEntry, MediaItem, PlaylistCategory
from zone_new_companion.services.base import PortalService
from zone_new_companion.services.network import DEFAULT_TIMEOUT, create_session, normalize_url


class XtreamService(PortalService):
    """Use Xtream `player_api.php` endpoints."""

    def __init__(self) -> None:
        self._session = create_session()
        self._xmltv_cache: bytes | None = None

    def fetch_categories(self, credentials: Credentials) -> dict[str, list[PlaylistCategory]]:
        endpoint = normalize_url(credentials.base_url, "player_api.php")
        common = {"username": credentials.username, "password": credentials.password}
        mappings = {
            "Live": "get_live_categories",
            "Movies": "get_vod_categories",
            "Series": "get_series_categories",
        }

        grouped: dict[str, list[PlaylistCategory]] = {"Live": [], "Movies": [], "Series": []}
        for tab, action in mappings.items():
            response = self._session.get(
                endpoint,
                params={**common, "action": action},
                timeout=DEFAULT_TIMEOUT,
            )
            response.raise_for_status()
            rows = response.json()
            grouped[tab] = [
                PlaylistCategory(
                    id=str(row.get("category_id", "")),
                    name=str(row.get("category_name", "Unnamed")),
                    media_kind=tab.lower(),
                )
                for row in rows
            ]
        return grouped

    def fetch_connection_info(self, credentials: Credentials) -> dict[str, str]:
        endpoint = normalize_url(credentials.base_url, "player_api.php")
        response = self._session.get(
            endpoint,
            params={"username": credentials.username, "password": credentials.password},
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
        user_info = payload.get("user_info", {})
        server_info = payload.get("server_info", {})

        expiry = "Unlimited"
        exp_date = str(user_info.get("exp_date", "")).strip()
        if exp_date.isdigit():
            expiry = datetime.fromtimestamp(int(exp_date)).astimezone().strftime("%Y-%m-%d %H:%M")
        created = "Unknown"
        created_at = str(user_info.get("created_at", "")).strip()
        if created_at.isdigit():
            created = datetime.fromtimestamp(int(created_at)).astimezone().strftime("%Y-%m-%d %H:%M")

        protocol = str(server_info.get("server_protocol", "http"))
        host = str(server_info.get("url", credentials.base_url))
        http_port = str(server_info.get("port", ""))
        https_port = str(server_info.get("https_port", ""))
        return {
            "Status": str(user_info.get("status", "Unknown")),
            "Expiry": expiry,
            "Active/Max Connections": (
                f"{user_info.get('active_cons', '0')}/{user_info.get('max_connections', 'Unknown')}"
            ),
            "Real URL": f"{protocol}://{host}",
            "Ports": f"HTTP {http_port} | HTTPS {https_port}",
            "Timezone": str(server_info.get("timezone", "Unknown")),
            "Created At": created,
        }

    def fetch_items(self, credentials: Credentials, category: PlaylistCategory) -> list[MediaItem]:
        endpoint = normalize_url(credentials.base_url, "player_api.php")
        common = {
            "username": credentials.username,
            "password": credentials.password,
            "category_id": category.id,
        }
        if category.media_kind == "live":
            action = "get_live_streams"
            prefix = "live"
            item_type = "channel"
        elif category.media_kind == "movies":
            action = "get_vod_streams"
            prefix = "movie"
            item_type = "vod"
        else:
            action = "get_series"
            prefix = "series"
            item_type = "series"

        response = self._session.get(
            endpoint,
            params={**common, "action": action},
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
        rows: list[dict[str, Any]] = response.json()
        items: list[MediaItem] = []
        for row in rows:
            stream_id = row.get("stream_id") or row.get("series_id") or row.get("id")
            ext = str(row.get("container_extension", "m3u8"))
            stream_url = None
            if stream_id and item_type in {"channel", "vod"}:
                extension = "ts" if item_type == "channel" else ext
                stream_url = normalize_url(
                    credentials.base_url,
                    f"{prefix}/{credentials.username}/{credentials.password}/{stream_id}.{extension}",
                )
            items.append(
                MediaItem(
                    id=str(stream_id or ""),
                    name=str(row.get("name", "Unnamed")),
                    media_kind=category.media_kind,
                    item_type=item_type,
                    metadata=row,
                    stream_url=stream_url,
                ),
            )
        return items

    def resolve_stream_url(self, credentials: Credentials, item: MediaItem) -> str:
        if item.stream_url:
            return item.stream_url
        raise ValueError("Item does not provide a direct stream URL.")

    @staticmethod
    def _parse_xmltv_timestamp(raw_value: str) -> datetime:
        parts = raw_value.strip().split(" ")
        if len(parts) == 2:
            return datetime.strptime(f"{parts[0]} {parts[1]}", "%Y%m%d%H%M%S %z").astimezone()
        return datetime.strptime(parts[0], "%Y%m%d%H%M%S").astimezone()

    def fetch_epg_for_channel(self, credentials: Credentials, channel_item: MediaItem) -> list[EpgEntry]:
        epg_channel_id = str(channel_item.metadata.get("epg_channel_id", "")).strip().lower()
        if not epg_channel_id:
            return []
        if self._xmltv_cache is None:
            epg_url = normalize_url(
                credentials.base_url,
                f"xmltv.php?username={credentials.username}&password={credentials.password}",
            )
            response = self._session.get(epg_url, timeout=DEFAULT_TIMEOUT)
            response.raise_for_status()
            self._xmltv_cache = response.content
        if self._xmltv_cache is None:
            return []
        root = et.fromstring(self._xmltv_cache)
        entries: list[EpgEntry] = []
        for node in root.findall("programme"):
            channel_id = str(node.get("channel", "")).strip().lower()
            if channel_id != epg_channel_id:
                continue
            start_raw = str(node.get("start", "")).strip()
            stop_raw = str(node.get("stop", "")).strip()
            if not start_raw or not stop_raw:
                continue
            start_at = self._parse_xmltv_timestamp(start_raw)
            end_at = self._parse_xmltv_timestamp(stop_raw)
            title = str(node.findtext("title", "Untitled")).strip()
            description = str(node.findtext("desc", "")).strip()
            entries.append(EpgEntry(title=title, start_at=start_at, end_at=end_at, description=description))
        entries.sort(key=lambda row: row.start_at)
        now = datetime.now().astimezone()
        future_entries = [entry for entry in entries if entry.end_at >= now]
        if future_entries:
            previous_entries = [entry for entry in entries if entry.end_at < now]
            return previous_entries[-2:] + future_entries[:8]
        return entries[-10:]

    def fetch_series_children(self, credentials: Credentials, item: MediaItem) -> list[MediaItem]:
        endpoint = normalize_url(credentials.base_url, "player_api.php")
        if item.item_type == "series":
            response = self._session.get(
                endpoint,
                params={
                    "username": credentials.username,
                    "password": credentials.password,
                    "action": "get_series_info",
                    "series_id": item.id,
                },
                timeout=DEFAULT_TIMEOUT,
            )
            response.raise_for_status()
            payload = response.json()
            episodes = payload.get("episodes", {})
            season_items: list[MediaItem] = []
            for season_name in sorted(episodes.keys(), key=lambda value: int(value)):
                season_items.append(
                    MediaItem(
                        id=f"{item.id}:{season_name}",
                        name=f"Season {season_name}",
                        media_kind=item.media_kind,
                        item_type="season",
                        metadata={"series_id": item.id, "season_number": season_name, "episodes": episodes[season_name]},
                    ),
                )
            return season_items

        if item.item_type == "season":
            raw_episodes = item.metadata.get("episodes", [])
            children: list[MediaItem] = []
            for entry in raw_episodes:
                episode_id = str(entry.get("id", ""))
                ext = str(entry.get("container_extension", "m3u8"))
                stream_url = normalize_url(
                    credentials.base_url,
                    f"series/{credentials.username}/{credentials.password}/{episode_id}.{ext}",
                )
                children.append(
                    MediaItem(
                        id=episode_id,
                        name=str(entry.get("title", f"Episode {entry.get('episode_num', '?')}")),
                        media_kind=item.media_kind,
                        item_type="episode",
                        metadata=entry,
                        stream_url=stream_url,
                    ),
                )
            return children

        return []
