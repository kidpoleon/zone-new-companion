"""Xtream portal service implementation."""

from __future__ import annotations

from datetime import datetime
from typing import Any
import xml.etree.ElementTree as et

import requests

from zone_new_companion.models import Credentials, EpgEntry, MediaItem, PlaylistCategory
from zone_new_companion.services.base import PortalService
from zone_new_companion.services.network import DEFAULT_TIMEOUT, create_session, normalize_url


class XtreamService(PortalService):
    """Use Xtream `player_api.php` endpoints."""

    def __init__(self) -> None:
        self._session = create_session()
        self._xmltv_cache: bytes | None = None
        self._player_api_endpoint: str | None = None

    @staticmethod
    def _coerce_row_list(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [row for row in payload if isinstance(row, dict)]
        if isinstance(payload, dict):
            if isinstance(payload.get("js"), list):
                return [row for row in payload["js"] if isinstance(row, dict)]
            if isinstance(payload.get("categories"), list):
                return [row for row in payload["categories"] if isinstance(row, dict)]
        return []

    def _candidate_api_endpoints(self, base_url: str) -> list[str]:
        base = base_url.rstrip("/")
        candidates = [
            normalize_url(base, "player_api.php"),
            normalize_url(base, "panel_api.php"),
            normalize_url(base, "xtream"),
        ]
        # Some users paste /c/ panel hosts for Stalker-like portals.
        if base.endswith("/c"):
            root_base = base[:-2].rstrip("/")
            candidates.extend(
                [
                    normalize_url(root_base, "player_api.php"),
                    normalize_url(root_base, "panel_api.php"),
                    normalize_url(root_base, "xtream"),
                ],
            )
        return list(dict.fromkeys(candidates))

    def _request_api(
        self,
        credentials: Credentials,
        *,
        action: str | None = None,
        extra_params: dict[str, str] | None = None,
    ) -> Any:
        params: dict[str, str] = {
            "username": credentials.username,
            "password": credentials.password,
        }
        if action:
            params["action"] = action
        if extra_params:
            params.update(extra_params)

        endpoints = [self._player_api_endpoint] if self._player_api_endpoint else []
        endpoints.extend(self._candidate_api_endpoints(credentials.base_url))
        last_error: Exception | None = None
        for endpoint in dict.fromkeys([ep for ep in endpoints if ep]):
            try:
                response = self._session.get(endpoint, params=params, timeout=DEFAULT_TIMEOUT)
                response.raise_for_status()
                payload = response.json()
                self._player_api_endpoint = endpoint
                return payload
            except (requests.RequestException, ValueError, RuntimeError) as exc:
                last_error = exc
                continue
        raise RuntimeError(f"Xtream API request failed for all endpoints: {last_error}")

    def fetch_categories(self, credentials: Credentials) -> dict[str, list[PlaylistCategory]]:
        mappings = {
            "Live": "get_live_categories",
            "Movies": "get_vod_categories",
            "Series": "get_series_categories",
        }

        grouped: dict[str, list[PlaylistCategory]] = {"Live": [], "Movies": [], "Series": []}
        for tab, action in mappings.items():
            rows = self._coerce_row_list(self._request_api(credentials, action=action))
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
        payload = self._request_api(credentials)
        if not isinstance(payload, dict):
            payload = {}
        user_info = payload.get("user_info", {})
        server_info = payload.get("server_info", {})
        if not isinstance(user_info, dict):
            user_info = {}
        if not isinstance(server_info, dict):
            server_info = {}

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

        payload = self._request_api(credentials, action=action, extra_params={"category_id": category.id})
        rows = self._coerce_row_list(payload)
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
        if item.item_type == "series":
            payload = self._request_api(
                credentials,
                action="get_series_info",
                extra_params={"series_id": item.id},
            )
            if not isinstance(payload, dict):
                return []
            episodes = payload.get("episodes", {})
            if not isinstance(episodes, dict):
                return []
            season_items: list[MediaItem] = []
            for season_name in sorted(episodes.keys(), key=lambda value: int(str(value)) if str(value).isdigit() else 0):
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
