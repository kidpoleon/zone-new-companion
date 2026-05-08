"""Stalker portal service implementation with robust stream handling."""

from __future__ import annotations

import hashlib
import re
import secrets
import string
import threading
import time
from datetime import datetime
from typing import Any
from urllib.parse import quote, urlencode, urlparse, urlunparse

import requests

from zone_new_companion.models import Credentials, EpgEntry, MediaItem, PlaylistCategory
from zone_new_companion.services.base import PortalService
from zone_new_companion.services.logger_service import logger_service
from zone_new_companion.services.network import DEFAULT_TIMEOUT, normalize_url


# MAG Box emulation constants
MAG_USER_AGENT = (
    "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) "
    "MAG200 stbapp ver: 4 rev: 2116 Mobile Safari/533.3"
)
MAG_MODEL = "MAG254"
X_USER_AGENT = f"Model: {MAG_MODEL}; Link: Ethernet"
WATCHDOG_INTERVAL = 120  # seconds - keepalive interval


class StalkerService(PortalService):
    """Enhanced Stalker service with robust stream URL handling."""

    def __init__(self) -> None:
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": MAG_USER_AGENT,
            "X-User-Agent": X_USER_AGENT,
        })

        self._token = ""
        self._token_key = ""
        self._credentials: Credentials | None = None
        self._portal_url = ""
        self._device_id = ""
        self._device_id2 = ""
        self._signature = ""
        self._serial_number = ""
        self._watchdog_thread: threading.Thread | None = None
        self._watchdog_stop = threading.Event()
        self._watchdog_lock = threading.Lock()

    def _generate_device_ids(self, mac_address: str) -> None:
        """Generate deterministic device IDs from MAC address."""
        mac_clean = mac_address.replace(":", "").upper()

        # device_id: first 12 chars of SHA256 in uppercase hex
        self._device_id = hashlib.sha256(
            f"{mac_clean}:device_id".encode()
        ).hexdigest()[:12].upper()

        # device_id2: next 12 chars
        self._device_id2 = hashlib.sha256(
            f"{mac_clean}:device_id2".encode()
        ).hexdigest()[12:24].upper()

        # serial_number: 12 char alphanumeric
        self._serial_number = hashlib.sha256(
            f"{mac_clean}:sn".encode()
        ).hexdigest()[:12].upper()

        # signature: 64 char hex
        self._signature = hashlib.sha256(
            f"{mac_clean}:sig".encode()
        ).hexdigest()

    def _cookies(self) -> dict[str, str]:
        """Build proper Stalker cookies."""
        cookies: dict[str, str] = {
            "mac": self._credentials.mac_address.upper() if self._credentials else "",
            "sn": self._serial_number,
            "stb_lang": "en",
            "timezone": "Europe/London",
        }
        if self._token:
            cookies["token"] = self._token
        return cookies

    def _headers(self) -> dict[str, str]:
        """Build request headers with Bearer token."""
        headers: dict[str, str] = {
            "User-Agent": MAG_USER_AGENT,
            "X-User-Agent": X_USER_AGENT,
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def _normalize_mac(self, mac: str) -> str:
        """Normalize MAC to colon-separated uppercase format."""
        mac = mac.strip().upper()
        mac_clean = mac.replace(":", "").replace("-", "").replace(".", "")
        return ":".join(mac_clean[i:i + 2] for i in range(0, 12, 2))

    def _stop_watchdog(self) -> None:
        """Stop the watchdog keepalive thread."""
        self._watchdog_stop.set()
        if self._watchdog_thread and self._watchdog_thread.is_alive():
            self._watchdog_thread.join(timeout=2)
        self._watchdog_stop.clear()

    def _start_watchdog(self) -> None:
        """Start watchdog thread to keep session alive."""
        self._stop_watchdog()

        def watchdog_loop():
            while not self._watchdog_stop.wait(WATCHDOG_INTERVAL):
                with self._watchdog_lock:
                    try:
                        self._send_watchdog()
                    except Exception as e:
                        logger_service.warning(f"Watchdog update failed: {e}")

        self._watchdog_thread = threading.Thread(target=watchdog_loop, daemon=True)
        self._watchdog_thread.start()

    def _send_watchdog(self) -> None:
        """Send watchdog keepalive to prevent session timeout."""
        if not self._credentials or not self._token:
            return

        endpoint = self._get_portal_endpoint()
        url = (
            f"{endpoint}?action=get_events&event_active_id=0&init=0"
            f"&type=watchdog&cur_play_type=1&JsHttpRequest=1-xml"
        )

        try:
            response = self._session.get(
                url,
                headers=self._headers(),
                cookies=self._cookies(),
                timeout=DEFAULT_TIMEOUT,
            )
            response.raise_for_status()
        except requests.RequestException:
            pass

    def _get_portal_endpoint(self) -> str:
        """Get the portal endpoint URL."""
        if not self._credentials:
            raise ValueError("No credentials set")

        base = self._credentials.base_url.rstrip("/")

        if "/c" in base:
            root = base.split("/c", 1)[0].rstrip("/")
            return f"{root}/portal.php"

        return f"{base}/portal.php"

    def _get_play_endpoint(self) -> str:
        """Get the play endpoint for stream generation."""
        if not self._credentials:
            raise ValueError("No credentials set")

        base = self._credentials.base_url.rstrip("/")

        # Some portals use /play/live.php format
        if "/c" in base:
            root = base.split("/c", 1)[0].rstrip("/")
            return f"{root}/play/live.php"

        return f"{base}/play/live.php"

    def _handshake(self) -> bool:
        """Perform Stalker handshake to obtain/validate token."""
        if not self._credentials:
            raise ValueError("No credentials set")

        endpoint = self._get_portal_endpoint()
        url = (
            f"{endpoint}?type=stb&action=handshake"
            f"&token={self._token}&JsHttpRequest=1-xml"
        )

        try:
            response = self._session.get(
                url,
                headers=self._headers(),
                cookies=self._cookies(),
                timeout=DEFAULT_TIMEOUT,
            )
            response.raise_for_status()

            data = response.json()
            token = data.get("js", {}).get("token", "")

            if token:
                self._token = token
            else:
                if not self._token:
                    mac_clean = self._credentials.mac_address.replace(":", "").upper()
                    self._token = hashlib.sha1(
                        mac_clean.encode()
                    ).hexdigest().upper()[:32]

            return True

        except requests.RequestException as e:
            logger_service.error(f"Handshake failed: {e}")
            return False

    def _authenticate(self) -> bool:
        """Authenticate with username/password if provided."""
        if not self._credentials or not self._credentials.username:
            return True

        endpoint = self._get_portal_endpoint()
        url = (
            f"{endpoint}?type=stb&action=do_auth"
            f"&login={quote(self._credentials.username)}"
            f"&password={quote(self._credentials.password)}"
            f"&device_id={self._device_id}"
            f"&device_id2={self._device_id2}"
            f"&JsHttpRequest=1-xml"
        )

        try:
            response = self._session.get(
                url,
                headers=self._headers(),
                cookies=self._cookies(),
                timeout=DEFAULT_TIMEOUT,
            )
            response.raise_for_status()

            data = response.json()
            return data.get("js") is True

        except requests.RequestException:
            return False

    def _authenticate_with_device_ids(self) -> bool:
        """Authenticate using device IDs only."""
        if not self._credentials:
            return False

        endpoint = self._get_portal_endpoint()
        url = (
            f"{endpoint}?type=stb&action=get_profile&JsHttpRequest=1-xml&hd=1"
            f"&sn={self._serial_number}"
            f"&stb_type={MAG_MODEL}"
            f"&device_id={self._device_id}"
            f"&device_id2={self._device_id2}"
            f"&auth_second_step=1"
        )

        try:
            response = self._session.get(
                url,
                headers=self._headers(),
                cookies=self._cookies(),
                timeout=DEFAULT_TIMEOUT,
            )
            response.raise_for_status()

            data = response.json()
            profile = data.get("js", {})
            return bool(profile.get("id"))

        except requests.RequestException:
            return False

    def connect(self, credentials: Credentials) -> bool:
        """Connect to Stalker portal with full handshake."""
        self._credentials = credentials

        if not credentials.mac_address:
            raise ValueError("MAC address is required")

        mac = self._normalize_mac(credentials.mac_address)
        self._credentials.mac_address = mac

        self._generate_device_ids(mac)

        if not self._handshake():
            raise ValueError("Failed to handshake")

        if credentials.username and credentials.password:
            if not self._authenticate():
                logger_service.warning("Authentication failed, continuing anyway")
        else:
            self._authenticate_with_device_ids()

        self._start_watchdog()
        return True

    def fetch_categories(self, credentials: Credentials) -> dict[str, list[PlaylistCategory]]:
        """Fetch channel categories."""
        self.connect(credentials)

        endpoint = self._get_portal_endpoint()
        grouped: dict[str, list[PlaylistCategory]] = {
            "Live": [],
            "Movies": [],
            "Series": []
        }

        requests_by_tab = {
            "Live": ("itv", "get_genres"),
            "Movies": ("vod", "get_categories"),
            "Series": ("series", "get_categories"),
        }

        for tab, (portal_type, action) in requests_by_tab.items():
            try:
                response = self._session.get(
                    endpoint,
                    params={
                        "type": portal_type,
                        "action": action,
                        "JsHttpRequest": "1-xml"
                    },
                    headers=self._headers(),
                    cookies=self._cookies(),
                    timeout=DEFAULT_TIMEOUT,
                )
                response.raise_for_status()

                rows = response.json().get("js", [])
                categories = [
                    PlaylistCategory(
                        id=str(row.get("id", "")),
                        name=str(row.get("title", "Unnamed")),
                        media_kind=tab.lower(),
                    )
                    for row in rows
                ]
                grouped[tab] = sorted(categories, key=lambda x: x.name.lower())

            except requests.RequestException as e:
                logger_service.error(f"Failed to fetch {tab} categories: {e}")

        return grouped

    def fetch_items(self, credentials: Credentials, category: PlaylistCategory) -> list[MediaItem]:
        """Fetch media items for a category."""
        self.connect(credentials)

        endpoint = self._get_portal_endpoint()

        if category.media_kind == "live":
            query = {
                "type": "itv",
                "action": "get_ordered_list",
                "genre": category.id
            }
            item_type = "channel"
        else:
            query = {
                "type": "vod",
                "action": "get_ordered_list",
                "category": category.id
            }
            item_type = "vod" if category.media_kind == "movies" else "series"

        response = self._session.get(
            endpoint,
            params={**query, "JsHttpRequest": "1-xml"},
            headers=self._headers(),
            cookies=self._cookies(),
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()

        rows = response.json().get("js", {}).get("data", [])
        items = [
            MediaItem(
                id=str(row.get("id", "")),
                name=str(row.get("name", "Unnamed")),
                media_kind=category.media_kind,
                item_type=item_type,
                metadata=row,
            )
            for row in rows
        ]
        return sorted(items, key=lambda x: x.name.lower())

    def resolve_stream_url(self, credentials: Credentials, item: MediaItem, retry: bool = False) -> str:
        """Resolve stream URL with multiple fallback strategies."""
        self.connect(credentials)

        # Get channel ID from item metadata
        channel_id = str(item.metadata.get("id", item.id))
        cmd = str(item.metadata.get("cmd", "")).strip()

        logger_service.info(f"Resolving stream for channel_id={channel_id}, cmd={cmd[:50] if cmd else 'None'}")

        # Strategy 1: Try the standard create_link endpoint
        try:
            stream_url = self._resolve_via_create_link(credentials, item, channel_id)
            if stream_url:
                logger_service.info(f"Strategy 1 SUCCESS - create_link returned: {stream_url}")
                return stream_url
        except Exception as e:
            logger_service.warning(f"Strategy 1 FAILED - create_link error: {e}")

        # Strategy 2: Try play/live.php format (common in some portals)
        try:
            stream_url = self._resolve_via_play_endpoint(credentials, channel_id)
            if stream_url:
                logger_service.info(f"Strategy 2 SUCCESS - play_endpoint returned: {stream_url}")
                return stream_url
        except Exception as e:
            logger_service.warning(f"Strategy 2 FAILED - play_endpoint error: {e}")

        # Strategy 3: Try direct cmd construction
        if cmd:
            try:
                stream_url = self._extract_from_cmd(cmd, credentials)
                if stream_url:
                    logger_service.info(f"Strategy 3 SUCCESS - cmd extract returned: {stream_url}")
                    return stream_url
            except Exception as e:
                logger_service.warning(f"Strategy 3 FAILED - cmd extract error: {e}")

        raise ValueError("All stream resolution strategies failed")

    def _resolve_via_create_link(self, credentials: Credentials, item: MediaItem, channel_id: str) -> str | None:
        """Resolve stream URL using standard create_link endpoint."""
        endpoint = self._get_portal_endpoint()
        stream_type = "itv" if item.item_type == "channel" else "vod"

        # Build cmd parameter - use the item's cmd field if available
        cmd = str(item.metadata.get("cmd", "")).strip()
        if not cmd:
            cmd = channel_id

        encoded = quote(cmd)
        logger_service.info(f"create_link request: endpoint={endpoint}, type={stream_type}, cmd={cmd[:50]}")

        response = self._session.get(
            endpoint,
            params={
                "type": stream_type,
                "action": "create_link",
                "cmd": encoded,
                "JsHttpRequest": "1-xml",
            },
            headers=self._headers(),
            cookies=self._cookies(),
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()

        js = response.json().get("js", {})
        logger_service.info(f"create_link response: {js}")

        # Try to get URL from response
        raw_url = js.get("url") or js.get("cmd") or ""

        if raw_url:
            cleaned = self._clean_stream_url(str(raw_url), credentials)
            logger_service.info(f"create_link cleaned URL: {cleaned}")
            return cleaned

        return None

    def _resolve_via_play_endpoint(self, credentials: Credentials, channel_id: str) -> str | None:
        """Resolve stream URL using play/live.php endpoint."""
        # Get token
        token = self._token

        if not token:
            logger_service.warning("No token available for play endpoint")
            return None

        # Build play.php URL
        play_url = self._get_play_endpoint()

        # Build URL exactly like IPTV-MAC-STALKER-PLAYER-BY-MY-1 does
        # Format: http://host/play/live.php?mac=XX&stream=XX&extension=ts&play_token=XX
        params = {
            "mac": credentials.mac_address,
            "stream": channel_id,
            "extension": "ts",
            "play_token": token,
        }

        full_url = f"{play_url}?{urlencode(params)}"
        logger_service.info(f"play_endpoint URL: {full_url}")

        return full_url

    def _extract_from_cmd(self, cmd: str, credentials: Credentials) -> str | None:
        """Extract stream URL from cmd field."""
        if not cmd:
            return None

        logger_service.info(f"Extracting from cmd: {cmd}")

        # Remove ffmpeg prefix
        cmd_clean = re.sub(r"(?i)^ffmpeg\s*", "", cmd).strip()
        cmd_clean = cmd_clean.strip("\"'")

        # Check if it's already a valid URL
        if re.match(r"^https?://", cmd_clean, re.IGNORECASE):
            logger_service.info(f"cmd is direct URL: {cmd_clean}")
            return cmd_clean

        # Extract URL from the command
        match = re.search(r"(https?://[^\s\"']+)", cmd_clean, re.IGNORECASE)
        if match:
            extracted = match.group(1)
            logger_service.info(f"cmd extracted URL: {extracted}")
            return extracted

        # If it's just a channel ID, try to construct URL
        if cmd_clean.isdigit():
            logger_service.info(f"cmd is channel ID: {cmd_clean}")
            return self._resolve_via_play_endpoint(credentials, cmd_clean)

        return None

    def _clean_stream_url(self, raw_value: str, credentials: Credentials) -> str:
        """Clean and validate stream URL."""
        if not raw_value:
            return ""

        stream_url = raw_value.strip()
        logger_service.info(f"clean_stream_url raw input: {stream_url}")

        # Remove ffmpeg prefix
        stream_url = re.sub(r"(?i)^ffmpeg\s*", "", stream_url).strip()
        stream_url = stream_url.strip("\"'")

        logger_service.info(f"clean_stream_url after prefix strip: {stream_url}")

        # Extract URL if embedded in command
        match = re.search(r"(https?://[^\s\"']+)", stream_url, re.IGNORECASE)
        if match:
            extracted = match.group(1)
            logger_service.info(f"clean_stream_url extracted: {extracted}")
            return extracted

        # Handle relative paths
        if stream_url.startswith("/"):
            base = credentials.base_url.rstrip("/")
            result = f"{base}{stream_url}"
            logger_service.info(f"clean_stream_url relative path: {result}")
            return result

        # Handle protocol-relative URLs
        if stream_url.startswith("//"):
            result = f"https:{stream_url}"
            logger_service.info(f"clean_stream_url protocol relative: {result}")
            return result

        logger_service.info(f"clean_stream_url returning as-is: {stream_url}")
        return stream_url

    def get_connection_info(self, credentials: Credentials) -> dict[str, str]:
        """Fetch account information."""
        self.connect(credentials)

        endpoint = self._get_portal_endpoint()
        url = f"{endpoint}?type=account_info&action=get_main_info&JsHttpRequest=1-xml"

        try:
            response = self._session.get(
                url,
                headers=self._headers(),
                cookies=self._cookies(),
                timeout=DEFAULT_TIMEOUT,
            )
            response.raise_for_status()

            data = response.json()
            account = data.get("js", {}).get("account", {})
            profile = data.get("js", {}).get("profile", {})

            expiry = (
                account.get("end_date")
                or profile.get("end_date")
                or "Unknown"
            )

            if isinstance(expiry, str) and expiry.isdigit():
                expiry = datetime.fromtimestamp(int(expiry)).strftime("%Y-%m-%d")

            return {
                "Status": str(account.get("status", "Unknown")),
                "Expiry": str(expiry),
                "Active/Max": f"{account.get('active_cons', '?' )}/{account.get('max_online', '?')}",
                "URL": credentials.base_url,
                "MAC": credentials.mac_address,
            }

        except Exception as e:
            return {
                "Status": "Error",
                "Error": str(e),
                "URL": credentials.base_url,
                "MAC": credentials.mac_address,
            }

    def fetch_epg_for_channel(self, credentials: Credentials, channel_item: MediaItem) -> list[EpgEntry]:
        """Fetch EPG data for a channel."""
        self.connect(credentials)

        channel_id = str(channel_item.metadata.get("id", "")).strip()
        if not channel_id:
            return []

        endpoint = self._get_portal_endpoint()

        try:
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
                cookies=self._cookies(),
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

                try:
                    start_at = datetime.fromtimestamp(int(start_ts))
                    end_at = datetime.fromtimestamp(int(stop_ts))
                    title = str(row.get("name") or row.get("title") or "Untitled")
                    desc = str(row.get("descr") or row.get("description") or "")
                    entries.append(EpgEntry(
                        title=title,
                        start_at=start_at,
                        end_at=end_at,
                        description=desc
                    ))
                except (ValueError, TypeError):
                    continue

            entries.sort(key=lambda r: r.start_at)
            return entries

        except requests.RequestException:
            return []

    def fetch_now_playing(self, credentials: Credentials, channel_item: MediaItem) -> str:
        """Fetch currently playing program."""
        self.connect(credentials)

        channel_id = str(channel_item.metadata.get("id", "")).strip()
        if not channel_id:
            return ""

        endpoint = self._get_portal_endpoint()

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
                cookies=self._cookies(),
                timeout=DEFAULT_TIMEOUT,
            )
            response.raise_for_status()

            rows = response.json().get("js", {}).get("data", [])
            if not rows:
                return ""

            now_ts = datetime.now().timestamp()

            for row in rows:
                try:
                    start_ts = float(row.get("start_timestamp") or row.get("time") or 0)
                    stop_ts = float(row.get("stop_timestamp") or row.get("time_to") or 0)

                    if start_ts <= now_ts <= stop_ts:
                        return str(row.get("name") or row.get("title") or "").strip()
                except (TypeError, ValueError):
                    continue

            return str(rows[0].get("name") or rows[0].get("title") or "").strip()

        except requests.RequestException:
            return ""

    def fetch_series_children(self, credentials: Credentials, item: MediaItem) -> list[MediaItem]:
        """Fetch seasons or episodes."""
        self.connect(credentials)

        endpoint = self._get_portal_endpoint()

        if item.item_type == "series":
            try:
                response = self._session.get(
                    endpoint,
                    params={
                        "type": "vod",
                        "action": "get_ordered_list",
                        "movie_id": item.id,
                        "season_id": "0",
                        "episode_id": "0",
                        "JsHttpRequest": "1-xml",
                    },
                    headers=self._headers(),
                    cookies=self._cookies(),
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

            except requests.RequestException:
                return []

        if item.item_type == "season":
            try:
                response = self._session.get(
                    endpoint,
                    params={
                        "type": "vod",
                        "action": "get_ordered_list",
                        "movie_id": item.metadata.get("movie_id", ""),
                        "season_id": item.metadata.get("season_id", ""),
                        "episode_id": "0",
                        "JsHttpRequest": "1-xml",
                    },
                    headers=self._headers(),
                    cookies=self._cookies(),
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
                                "episode_number": episode.get(
                                    "series_number",
                                    episode.get("number", "")
                                ),
                            },
                        ),
                    )
                return children

            except requests.RequestException:
                return []

        return []
