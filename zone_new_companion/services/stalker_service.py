"""Stalker portal service implementation."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from urllib.parse import quote

import requests

from zone_new_companion.models import Credentials, EpgEntry, MediaItem, PlaylistCategory
from zone_new_companion.services.base import PortalService
from zone_new_companion.services.logger_service import logger_service
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

    def _validate_mac_address(self, mac: str) -> bool:
        """Validate MAC address format."""
        if not mac:
            return False
            
        # Remove common separators and normalize
        mac_clean = mac.replace(":", "").replace("-", "").replace(".", "")
        
        # Check if it's 12 hexadecimal characters
        if len(mac_clean) != 12:
            return False
            
        # Check if all characters are hexadecimal
        try:
            int(mac_clean, 16)
            return True
        except ValueError:
            return False

    def _ensure_token(self, credentials: Credentials) -> None:
        if not credentials.mac_address:
            raise ValueError("MAC address is required for Stalker portals")
            
        # Validate MAC address format
        if not self._validate_mac_address(credentials.mac_address):
            raise ValueError(f"Invalid MAC address format: {credentials.mac_address}")
            
        current_key = f"{credentials.base_url}|{credentials.mac_address}"
        if self._token and self._token_key == current_key:
            return
            
        logger_service.info(f"Getting Stalker token for MAC: {credentials.mac_address}")
        
        handshake_url = normalize_url(
            credentials.base_url,
            "portal.php?type=stb&action=handshake&JsHttpRequest=1-xml",
        )
        
        try:
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
                # Generate fallback token
                generated = hashlib.sha1(credentials.mac_address.encode("utf-8")).hexdigest().upper()[:32]
                token = generated
                logger_service.warning(f"Using generated token for MAC: {credentials.mac_address}")
                
            self._token = token
            self._token_key = current_key
            logger_service.info(f"Successfully obtained Stalker token: {self._token[:8]}...")
            
        except requests.RequestException as e:
            logger_service.error(f"Failed to get Stalker token: {e}")
            raise ValueError(f"Token request failed: {e}")

    def _portal_candidates(self, credentials: Credentials) -> list[str]:
        base = credentials.base_url.rstrip("/")
        candidates = [normalize_url(base, "portal.php")]
        if "/c" in base:
            root = base.split("/c", 1)[0].rstrip("/")
            candidates.extend(
                [
                    normalize_url(root, "portal.php"),
                    normalize_url(root, "stalker_portal/server/load.php"),
                ],
            )
        else:
            candidates.append(normalize_url(base, "stalker_portal/server/load.php"))
        return list(dict.fromkeys(candidates))

    def _extract_stream_url(self, raw_value: str, credentials: Credentials) -> str:
        logger_service.debug(f"Extracting stream URL from: {raw_value}")
        
        if not raw_value:
            logger_service.warning("Empty raw_value provided to _extract_stream_url")
            return ""
            
        stream_url = raw_value.strip()
        
        # Remove ffmpeg prefix and clean up
        stream_url = re.sub(r"(?i)^ffmpeg\s*", "", stream_url).strip()
        stream_url = stream_url.strip("\"'")
        
        # Try to find HTTP/HTTPS URLs first
        http_match = re.search(r"(https?://[^\s\"']+)", stream_url, flags=re.IGNORECASE)
        if http_match:
            extracted = http_match.group(1)
            logger_service.debug(f"Found HTTP URL: {extracted}")
            return extracted
            
        # Try to find rtsp/rtmp URLs
        rtsp_match = re.search(r"(rtsp://[^\s\"']+)", stream_url, flags=re.IGNORECASE)
        if rtsp_match:
            extracted = rtsp_match.group(1)
            logger_service.debug(f"Found RTSP URL: {extracted}")
            return extracted
            
        rtmp_match = re.search(r"(rtmp://[^\s\"']+)", stream_url, flags=re.IGNORECASE)
        if rtmp_match:
            extracted = rtmp_match.group(1)
            logger_service.debug(f"Found RTMP URL: {extracted}")
            return extracted
        
        # Handle relative paths
        if stream_url.startswith("/"):
            absolute_url = normalize_url(credentials.base_url, stream_url)
            logger_service.debug(f"Converted relative path to absolute: {absolute_url}")
            return absolute_url
            
        # Handle protocol-relative URLs
        if stream_url.startswith("//"):
            absolute_url = f"https:{stream_url}"
            logger_service.debug(f"Converted protocol-relative URL: {absolute_url}")
            return absolute_url
            
        # Handle non-URL but non-empty strings (might be direct paths)
        if stream_url and not re.match(r"^(https?|rtsp|rtmp)://", stream_url, flags=re.IGNORECASE):
            # Try to construct absolute URL
            absolute_url = normalize_url(credentials.base_url, stream_url)
            logger_service.debug(f"Constructed absolute URL from relative: {absolute_url}")
            return absolute_url
            
        logger_service.warning(f"Could not extract valid URL from: {raw_value}")
        return stream_url

    def fetch_categories(self, credentials: Credentials) -> dict[str, list[PlaylistCategory]]:
        self._ensure_token(credentials)
        base = self._portal_candidates(credentials)[0]
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
        base = self._portal_candidates(credentials)[0]
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
        logger_service.info(f"Resolving stream URL for {item.name} (type: {item.item_type})")
        self._ensure_token(credentials)
        
        cmd = str(item.metadata.get("cmd", "")).strip()
        logger_service.debug(f"Original CMD: {cmd}")
        
        if item.item_type == "episode" and not cmd:
            series_cmd = str(item.metadata.get("series_cmd", "")).strip()
            episode_number = str(item.metadata.get("episode_number", "")).strip()
            if series_cmd and episode_number:
                cmd = f"{series_cmd}{episode_number}"
                logger_service.debug(f"Constructed episode CMD: {cmd}")
        
        if not cmd:
            logger_service.error(f"No CMD found for item {item.name}")
            raise ValueError("Missing stream command in selected item.")
            
        encoded = quote(cmd)
        stream_type = "itv" if item.item_type == "channel" else "vod"
        logger_service.debug(f"Stream type: {stream_type}, encoded CMD: {encoded}")
        
        last_error: Exception | None = None
        for i, endpoint in enumerate(self._portal_candidates(credentials)):
            logger_service.debug(f"Trying endpoint {i+1}: {endpoint}")
            try:
                response = self._session.get(
                    endpoint,
                    params={
                        "type": stream_type,
                        "action": "create_link",
                        "cmd": encoded,
                        "JsHttpRequest": "1-xml",
                    },
                    headers=self._headers(),
                    cookies=self._cookies(credentials),
                    timeout=DEFAULT_TIMEOUT,
                )
                logger_service.debug(f"Response status: {response.status_code}")
                response.raise_for_status()
                
                js = response.json().get("js", {})
                logger_service.debug(f"Response JSON: {js}")
                
                raw_stream_url = str(js.get("url") or js.get("cmd") or "").strip()
                logger_service.debug(f"Raw stream URL: {raw_stream_url}")
                
                stream_url = self._extract_stream_url(raw_stream_url, credentials)
                logger_service.debug(f"Processed stream URL: {stream_url}")
                
                if stream_url:
                    logger_service.info(f"Successfully resolved stream URL: {stream_url}")
                    return stream_url
                else:
                    logger_service.warning(f"Empty stream URL from endpoint {i+1}")
                    
            except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
                logger_service.warning(f"Endpoint {i+1} failed: {exc}")
                last_error = exc
                continue
                
        raise ValueError(f"Unable to create stream link for {item.name}: {last_error}")

    def get_connection_info(self, credentials: Credentials) -> dict[str, str]:
        """Fetch account information from Stalker portal."""
        self._ensure_token(credentials)
        info_url = normalize_url(credentials.base_url, "portal.php?type=account_info&action=get_main_info&JsHttpRequest=1-xml")
        
        try:
            response = self._session.get(
                info_url,
                headers=self._headers(),
                cookies=self._cookies(credentials),
                timeout=DEFAULT_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
            
            account = data.get("account", {})
            profile = account.get("profile", {})
            
            expiry = (
                account.get("end_date")
                or profile.get("end_date")
                or account.get("expire_billing_date")
                or profile.get("expire_billing_date")
                or "Unknown"
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
            
        except Exception as e:
            logger_service.error(f"Failed to fetch Stalker connection info: {e}")
            return {
                "Status": "Error",
                "Expiry": "Unknown",
                "Active/Max Connections": "Unknown",
                "Real URL": credentials.base_url,
                "Ports": "Portal managed",
                "Timezone": "Unknown",
                "Created At": "Unknown",
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

    def fetch_now_playing(self, credentials: Credentials, channel_item: MediaItem) -> str:
        self._ensure_token(credentials)
        channel_id = str(channel_item.metadata.get("id", "")).strip()
        if not channel_id:
            return ""
        endpoint = self._portal_candidates(credentials)[0]
        try:
            response = self._session.get(
                endpoint,
                params={
                    "type": "itv",
                    "action": "get_epg_info",
                    "period": "1",
                    "ch_id": channel_id,
                    "JsHttpRequest": "1-xml",
                },
                headers=self._headers(),
                cookies=self._cookies(credentials),
                timeout=DEFAULT_TIMEOUT,
            )
            response.raise_for_status()
        except requests.RequestException:
            return ""
        rows = response.json().get("js", {}).get("data", [])
        if not isinstance(rows, list) or not rows:
            return ""
        now_ts = datetime.now().astimezone().timestamp()
        best = None
        for row in rows:
            if not isinstance(row, dict):
                continue
            try:
                start_ts = float(row.get("start_timestamp") or row.get("time") or 0)
                stop_ts = float(row.get("stop_timestamp") or row.get("time_to") or 0)
            except (TypeError, ValueError):
                continue
            if start_ts <= now_ts <= stop_ts:
                best = row
                break
        if best is None:
            best = next((row for row in rows if isinstance(row, dict)), None)
        if not isinstance(best, dict):
            return ""
        return str(best.get("name") or best.get("title") or "").strip()

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
