"""Stalker portal service implementation."""

from __future__ import annotations

import hashlib
from datetime import datetime
from urllib.parse import quote

from zone_new_companion.models import Credentials, EpgEntry, MediaItem, PlaylistCategory
from zone_new_companion.services.base import PortalService
from zone_new_companion.services.network import DEFAULT_TIMEOUT, create_session, normalize_url


class StalkerService(PortalService):
    """Use Stalker handshake + load.php APIs."""

    def __init__(self) -> None:
        self._session = create_session()
        self._token = ""
        self._token_key = ""

    def _cookies(self, credentials: Credentials) -> dict[str, str]:
        return {
            "mac": credentials.mac_address,
            "stb_lang": "en",
            "timezone": "Europe/London",
            "token": self._token,
        }

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def _ensure_token(self, credentials: Credentials) -> None:
        current_key = f"{credentials.base_url}|{credentials.mac_address}"
        if self._token and self._token_key == current_key:
            return
        handshake_url = normalize_url(
            credentials.base_url,
            "portal.php?type=stb&action=handshake&JsHttpRequest=1-xml",
        )
        response = self._session.get(
            handshake_url,
            cookies={
                "mac": credentials.mac_address,
                "stb_lang": "en",
                "timezone": "Europe/London",
            },
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
        token = response.json().get("js", {}).get("token", "")
        if not token:
            generated = hashlib.sha1(credentials.mac_address.encode("utf-8")).hexdigest().upper()[:32]
            token = generated
        self._token = token
        self._token_key = current_key

    def fetch_categories(self, credentials: Credentials) -> dict[str, list[PlaylistCategory]]:
        self._ensure_token(credentials)
        base = normalize_url(credentials.base_url, "portal.php")
        grouped: dict[str, list[PlaylistCategory]] = {"Live": [], "Movies": [], "Series": []}
        requests_by_tab = {
            "Live": ("itv", "get_genres"),
            "Movies": ("vod", "get_categories"),
            "Series": ("series", "get_categories"),
        }
        for tab, (portal_type, action) in requests_by_tab.items():
            response = self._session.get(
                base,
                params={"type": portal_type, "action": action, "JsHttpRequest": "1-xml"},
                headers=self._headers(),
                cookies=self._cookies(credentials),
                timeout=DEFAULT_TIMEOUT,
            )
            response.raise_for_status()
            rows = response.json().get("js", [])
            grouped[tab] = [
                PlaylistCategory(
                    id=str(row.get("id", "")),
                    name=str(row.get("title", "Unnamed")),
                    media_kind=tab.lower(),
                )
                for row in rows
            ]
        return grouped

    def fetch_items(self, credentials: Credentials, category: PlaylistCategory) -> list[MediaItem]:
        self._ensure_token(credentials)
        base = normalize_url(credentials.base_url, "portal.php")
        if category.media_kind == "live":
            query = {"type": "itv", "action": "get_ordered_list", "genre": category.id}
            item_type = "channel"
        else:
            query = {"type": "vod", "action": "get_ordered_list", "category": category.id}
            item_type = "vod" if category.media_kind == "movies" else "series"
        response = self._session.get(
            base,
            params={**query, "JsHttpRequest": "1-xml"},
            headers=self._headers(),
            cookies=self._cookies(credentials),
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
        rows = response.json().get("js", {}).get("data", [])
        return [
            MediaItem(
                id=str(row.get("id", "")),
                name=str(row.get("name", "Unnamed")),
                media_kind=category.media_kind,
                item_type=item_type,
                metadata=row,
            )
            for row in rows
        ]

    def resolve_stream_url(self, credentials: Credentials, item: MediaItem) -> str:
        self._ensure_token(credentials)
        cmd = str(item.metadata.get("cmd", "")).strip()
        if item.item_type == "episode" and not cmd:
            series_cmd = str(item.metadata.get("series_cmd", "")).strip()
            episode_number = str(item.metadata.get("episode_number", "")).strip()
            if series_cmd and episode_number:
                cmd = f"{series_cmd}{episode_number}"
        if not cmd:
            raise ValueError("Missing stream command in selected item.")
        encoded = quote(cmd)
        create_link_url = normalize_url(
            credentials.base_url,
            f"portal.php?type=itv&action=create_link&cmd={encoded}&JsHttpRequest=1-xml",
        )
        response = self._session.get(
            create_link_url,
            headers=self._headers(),
            cookies=self._cookies(credentials),
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
        js = response.json().get("js", {})
        stream_url = str(js.get("url") or js.get("cmd") or "").strip()
        if stream_url.lower().startswith("ffmpeg"):
            stream_url = stream_url[6:].strip()
        if not stream_url:
            raise ValueError("Unable to create stream link.")
        return stream_url

    def fetch_connection_info(self, credentials: Credentials) -> dict[str, str]:
        self._ensure_token(credentials)
        profile_url = normalize_url(
            credentials.base_url,
            "portal.php?type=stb&action=get_profile&JsHttpRequest=1-xml",
        )
        account_url = normalize_url(
            credentials.base_url,
            "portal.php?type=account_info&action=get_main_info&JsHttpRequest=1-xml",
        )
        profile_response = self._session.get(
            profile_url,
            headers=self._headers(),
            cookies=self._cookies(credentials),
            timeout=DEFAULT_TIMEOUT,
        )
        profile_response.raise_for_status()
        account_response = self._session.get(
            account_url,
            headers=self._headers(),
            cookies=self._cookies(credentials),
            timeout=DEFAULT_TIMEOUT,
        )
        account_response.raise_for_status()
        profile = profile_response.json().get("js", {})
        account = account_response.json().get("js", {})

        expiry = str(
            account.get("expire_billing_date")
            or account.get("exp_date")
            or profile.get("expire_billing_date")
            or "Unknown",
        )
        if expiry.isdigit():
            expiry = datetime.fromtimestamp(int(expiry)).astimezone().strftime("%Y-%m-%d %H:%M")

        max_online = account.get("max_online") or profile.get("max_online") or "Unknown"
        active_online = account.get("active_cons") or profile.get("active_cons") or "Unknown"
        timezone = profile.get("default_timezone") or account.get("timezone") or "Europe/London"
        return {
            "Status": str(account.get("status", profile.get("status", "Unknown"))),
            "Expiry": str(expiry),
            "Active/Max Connections": f"{active_online}/{max_online}",
            "Real URL": credentials.base_url,
            "Ports": "Portal managed",
            "Timezone": str(timezone),
            "Created At": str(account.get("created", "Unknown")),
        }

    def fetch_epg_for_channel(self, credentials: Credentials, channel_item: MediaItem) -> list[EpgEntry]:
        self._ensure_token(credentials)
        channel_id = str(channel_item.metadata.get("id", "")).strip()
        if not channel_id:
            return []
        endpoint = normalize_url(credentials.base_url, "portal.php")
        response = self._session.get(
            endpoint,
            params={
                "type": "itv",
                "action": "get_epg_info",
                "period": "6",
                "ch_id": channel_id,
                "JsHttpRequest": "1-xml",
            },
            headers=self._headers(),
            cookies=self._cookies(credentials),
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
        rows = response.json().get("js", {}).get("data", [])
        entries: list[EpgEntry] = []
        for row in rows:
            start_ts = row.get("start_timestamp") or row.get("time")
            stop_ts = row.get("stop_timestamp") or row.get("time_to")
            if not start_ts or not stop_ts:
                continue
            start_at = datetime.fromtimestamp(int(start_ts)).astimezone()
            end_at = datetime.fromtimestamp(int(stop_ts)).astimezone()
            title = str(row.get("name") or row.get("title") or "Untitled")
            description = str(row.get("descr") or row.get("description") or "")
            entries.append(EpgEntry(title=title, start_at=start_at, end_at=end_at, description=description))
        entries.sort(key=lambda row: row.start_at)
        now = datetime.now().astimezone()
        future_entries = [entry for entry in entries if entry.end_at >= now]
        if future_entries:
            previous_entries = [entry for entry in entries if entry.end_at < now]
            return previous_entries[-2:] + future_entries[:8]
        return entries[-10:]

    def fetch_series_children(self, credentials: Credentials, item: MediaItem) -> list[MediaItem]:
        self._ensure_token(credentials)
        base = normalize_url(credentials.base_url, "portal.php")
        if item.item_type == "series":
            response = self._session.get(
                base,
                params={
                    "type": "vod",
                    "action": "get_ordered_list",
                    "movie_id": item.id,
                    "season_id": "0",
                    "episode_id": "0",
                    "JsHttpRequest": "1-xml",
                },
                headers=self._headers(),
                cookies=self._cookies(credentials),
                timeout=DEFAULT_TIMEOUT,
            )
            response.raise_for_status()
            rows = response.json().get("js", {}).get("data", [])
            season_items: list[MediaItem] = []
            for season in rows:
                season_id = str(season.get("id", ""))
                season_items.append(
                    MediaItem(
                        id=season_id,
                        name=str(season.get("name", f"Season {season_id}")),
                        media_kind=item.media_kind,
                        item_type="season",
                        metadata={
                            "movie_id": item.id,
                            "season_id": season_id,
                            "cmd": season.get("cmd", ""),
                        },
                    ),
                )
            return season_items

        if item.item_type == "season":
            response = self._session.get(
                base,
                params={
                    "type": "vod",
                    "action": "get_ordered_list",
                    "movie_id": item.metadata.get("movie_id", ""),
                    "season_id": item.metadata.get("season_id", ""),
                    "episode_id": "0",
                    "JsHttpRequest": "1-xml",
                },
                headers=self._headers(),
                cookies=self._cookies(credentials),
                timeout=DEFAULT_TIMEOUT,
            )
            response.raise_for_status()
            rows = response.json().get("js", {}).get("data", [])
            children: list[MediaItem] = []
            for episode in rows:
                episode_id = str(episode.get("id", ""))
                children.append(
                    MediaItem(
                        id=episode_id,
                        name=str(episode.get("name", f"Episode {episode_id}")),
                        media_kind=item.media_kind,
                        item_type="episode",
                        metadata={
                            **episode,
                            "movie_id": item.metadata.get("movie_id", ""),
                            "season_id": item.metadata.get("season_id", ""),
                            "series_cmd": item.metadata.get("cmd", ""),
                            "episode_number": episode.get("series_number", episode.get("number", "")),
                        },
                    ),
                )
            return children

        return []
