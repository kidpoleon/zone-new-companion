"""Stalker portal service implementation - Enhanced with stalkerhek proven methods."""

from __future__ import annotations

import hashlib
import re
import secrets
import string
import threading
import time
from datetime import datetime
from typing import Any
from urllib.parse import quote

import requests

from zone_new_companion.models import Credentials, EpgEntry, MediaItem, PlaylistCategory
from zone_new_companion.services.base import PortalService
from zone_new_companion.services.logger_service import logger_service
from zone_new_companion.services.network import DEFAULT_TIMEOUT, normalize_url


# MAG Box emulation constants from stalkerhek
MAG_USER_AGENT = (
    "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) "
    "MAG200 stbapp ver: 4 rev: 2116 Mobile Safari/533.3"
)
MAG_MODEL = "MAG254"
X_USER_AGENT = f"Model: {MAG_MODEL}; Link: Ethernet"
WATCHDOG_INTERVAL = 120  # seconds - keepalive interval (must be < typical 88s * 2)


class StalkerService(PortalService):
    """Enhanced Stalker service with stalkerhek proven methods.
    
    Implements:
    - Proper MAG box headers (User-Agent, X-User-Agent)
    - Automatic watchdog/keepalive for session persistence
    - Token-based authentication with Bearer header
    - Automatic re-authentication on token expiry
    - Link refresh for expired stream URLs
    """

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
        
        # Watchdog thread for keepalive
        self._watchdog_thread: threading.Thread | None = None
        self._watchdog_stop = threading.Event()
        self._watchdog_lock = threading.Lock()

    def _generate_device_ids(self, mac_address: str) -> None:
        """Generate deterministic device IDs from MAC address (like stalkerhek)."""
        # Generate device_id and device_id2 from MAC
        mac_clean = mac_address.replace(":", "").upper()
        
        # device_id: first 12 chars of SHA256 in uppercase hex
        self._device_id = hashlib.sha256(f"{mac_clean}:device_id".encode()).hexdigest()[:12].upper()
        
        # device_id2: next 12 chars 
        self._device_id2 = hashlib.sha256(f"{mac_clean}:device_id2".encode()).hexdigest()[12:24].upper()
        
        # serial_number: 12 char alphanumeric
        self._serial_number = hashlib.sha256(f"{mac_clean}:sn".encode()).hexdigest()[:12].upper()
        
        # signature: 64 char hex
        self._signature = hashlib.sha256(f"{mac_clean}:sig".encode()).hexdigest()
        
        logger_service.debug(f"Generated device_id: {self._device_id}, device_id2: {self._device_id2}")

    def _cookies(self) -> dict[str, str]:
        """Build proper Stalker cookies (stalkerhek format)."""
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

    def _validate_mac_address(self, mac: str) -> bool:
        """Validate MAC address format (AA:BB:CC:DD:EE:FF)."""
        if not mac:
            return False
        pattern = r"^[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}$"
        return bool(re.match(pattern, mac.strip()))

    def _normalize_mac(self, mac: str) -> str:
        """Normalize MAC to colon-separated uppercase format."""
        mac = mac.strip().upper()
        # Remove existing separators
        mac_clean = mac.replace(":", "").replace("-", "").replace(".", "")
        # Re-insert colons
        return ":".join(mac_clean[i:i+2] for i in range(0, 12, 2))

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
        logger_service.info("Started Stalker watchdog keepalive")

    def _send_watchdog(self) -> None:
        """Send watchdog keepalive to prevent session timeout."""
        if not self._credentials or not self._token:
            return
            
        endpoint = self._get_portal_endpoint()
        url = f"{endpoint}?action=get_events&event_active_id=0&init=0&type=watchdog&cur_play_type=1&JsHttpRequest=1-xml"
        
        try:
            response = self._session.get(
                url,
                headers=self._headers(),
                cookies=self._cookies(),
                timeout=DEFAULT_TIMEOUT,
            )
            response.raise_for_status()
            logger_service.debug("Watchdog update successful")
        except requests.RequestException as e:
            logger_service.warning(f"Watchdog request failed: {e}")

    def _get_portal_endpoint(self) -> str:
        """Get the portal endpoint URL."""
        if not self._credentials:
            raise ValueError("No credentials set")
        
        base = self._credentials.base_url.rstrip("/")
        
        # Try portal.php first, then fallback to load.php
        if "/c" in base:
            root = base.split("/c", 1)[0].rstrip("/")
            return f"{root}/portal.php"
        
        return f"{base}/portal.php"

    def _handshake(self) -> bool:
        """Perform Stalker handshake to obtain/validate token."""
        if not self._credentials:
            raise ValueError("No credentials set")
            
        endpoint = self._get_portal_endpoint()
        url = f"{endpoint}?type=stb&action=handshake&token={self._token}&JsHttpRequest=1-xml"
        
        logger_service.info(f"Performing Stalker handshake for MAC: {self._credentials.mac_address}")
        
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
                # Server provided new token, use it
                self._token = token
                logger_service.info(f"Received new token from server: {self._token[:8]}...")
            else:
                # Token accepted, keep using current token
                if not self._token:
                    # Generate fallback token if none provided
                    mac_clean = self._credentials.mac_address.replace(":", "").upper()
                    self._token = hashlib.sha1(mac_clean.encode()).hexdigest().upper()[:32]
                    logger_service.warning(f"Using generated fallback token: {self._token[:8]}...")
                else:
                    logger_service.info("Current token accepted by server")
            
            return True
            
        except requests.RequestException as e:
            logger_service.error(f"Handshake failed: {e}")
            return False

    def _authenticate(self) -> bool:
        """Authenticate with username/password if provided."""
        if not self._credentials or not self._credentials.username:
            logger_service.info("No username provided, skipping authentication")
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
        
        logger_service.info(f"Authenticating user: {self._credentials.username}")
        
        try:
            response = self._session.get(
                url,
                headers=self._headers(),
                cookies=self._cookies(),
                timeout=DEFAULT_TIMEOUT,
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get("js") == True:
                logger_service.info("Authentication successful")
                return True
            else:
                logger_service.error(f"Authentication failed: {data.get('text', 'Unknown error')}")
                return False
                
        except requests.RequestException as e:
            logger_service.error(f"Authentication request failed: {e}")
            return False

    def _authenticate_with_device_ids(self) -> bool:
        """Authenticate using device IDs only (for MAC-based auth)."""
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
        
        logger_service.info("Authenticating with device IDs...")
        
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
            
            if profile.get("id"):
                fname = profile.get("fname", "Unknown")
                logger_service.info(f"Authenticated as: {fname}")
                return True
            else:
                logger_service.error(f"Device ID auth failed: {data.get('text', 'Unknown error')}")
                return False
                
        except requests.RequestException as e:
            logger_service.error(f"Device ID auth request failed: {e}")
            return False

    def connect(self, credentials: Credentials) -> bool:
        """Connect to Stalker portal with full handshake and authentication."""
        self._credentials = credentials
        
        if not credentials.mac_address:
            raise ValueError("MAC address is required for Stalker portals")
        
        # Normalize MAC address
        mac = self._normalize_mac(credentials.mac_address)
        if not self._validate_mac_address(mac):
            raise ValueError(f"Invalid MAC address format: {credentials.mac_address}")
        
        self._credentials.mac_address = mac
        
        # Generate device IDs
        self._generate_device_ids(mac)
        
        # Perform handshake
        if not self._handshake():
            raise ValueError("Failed to handshake with Stalker portal")
        
        # Authenticate
        if credentials.username and credentials.password:
            if not self._authenticate():
                raise ValueError("Authentication failed")
        else:
            if not self._authenticate_with_device_ids():
                logger_service.warning("Device ID auth failed, but continuing anyway")
        
        # Start watchdog to keep session alive
        self._start_watchdog()
        
        return True

    def fetch_categories(self, credentials: Credentials) -> dict[str, list[PlaylistCategory]]:
        """Fetch channel categories from Stalker portal."""
        self.connect(credentials)
        
        endpoint = self._get_portal_endpoint()
        grouped: dict[str, list[PlaylistCategory]] = {"Live": [], "Movies": [], "Series": []}
        
        requests_by_tab = {
            "Live": ("itv", "get_genres"),
            "Movies": ("vod", "get_categories"),
            "Series": ("series", "get_categories"),
        }
        
        for tab, (portal_type, action) in requests_by_tab.items():
            try:
                response = self._session.get(
                    endpoint,
                    params={"type": portal_type, "action": action, "JsHttpRequest": "1-xml"},
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
                continue
        
        return grouped

    def fetch_items(self, credentials: Credentials, category: PlaylistCategory) -> list[MediaItem]:
        """Fetch media items for a category."""
        self.connect(credentials)
        
        endpoint = self._get_portal_endpoint()
        
        if category.media_kind == "live":
            query = {"type": "itv", "action": "get_ordered_list", "genre": category.id}
            item_type = "channel"
        else:
            query = {"type": "vod", "action": "get_ordered_list", "category": category.id}
            item_type = "vod" if category.media_kind == "movies" else "series"
        
        try:
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
            
        except requests.RequestException as e:
            logger_service.error(f"Failed to fetch items: {e}")
            raise ValueError(f"Failed to fetch items: {e}")

    def resolve_stream_url(self, credentials: Credentials, item: MediaItem, retry: bool = False) -> str:
        """Resolve stream URL with automatic re-authentication on failure."""
        self.connect(credentials)
        
        cmd = str(item.metadata.get("cmd", "")).strip()
        
        if item.item_type == "episode" and not cmd:
            series_cmd = str(item.metadata.get("series_cmd", "")).strip()
            episode_number = str(item.metadata.get("episode_number", "")).strip()
            if series_cmd and episode_number:
                cmd = f"{series_cmd}{episode_number}"
        
        if not cmd:
            raise ValueError("Missing stream command in selected item")
        
        encoded = quote(cmd)
        stream_type = "itv" if item.item_type == "channel" else "vod"
        endpoint = self._get_portal_endpoint()
        
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
                cookies=self._cookies(),
                timeout=DEFAULT_TIMEOUT,
            )
            response.raise_for_status()
            
            js = response.json().get("js", {})
            raw_url = str(js.get("cmd", js.get("url", ""))).strip()
            
            if not raw_url:
                raise ValueError("Empty stream URL from server")
            
            # Extract actual URL from ffmpeg command format
            stream_url = self._extract_stream_url(raw_url, credentials)
            
            if stream_url:
                return stream_url
            else:
                raise ValueError("Failed to extract valid stream URL")
                
        except (requests.RequestException, ValueError, KeyError, TypeError) as e:
            # Try re-authenticating once if not already retrying
            if not retry and self._credentials:
                logger_service.warning(f"Stream resolve failed, attempting re-authentication: {e}")
                
                # Reset token and re-handshake
                self._token = ""
                if self._handshake():
                    if self._credentials.username:
                        self._authenticate()
                    else:
                        self._authenticate_with_device_ids()
                    
                    # Retry once
                    return self.resolve_stream_url(credentials, item, retry=True)
            
            raise ValueError(f"Unable to create stream link: {e}")

    def _extract_stream_url(self, raw_value: str, credentials: Credentials) -> str:
        """Extract actual stream URL from ffmpeg command or raw string."""
        if not raw_value:
            return ""
        
        stream_url = raw_value.strip()
        
        # Remove ffmpeg prefix and clean up
        stream_url = re.sub(r"(?i)^ffmpeg\\s*", "", stream_url).strip()
        stream_url = stream_url.strip("\"'")
        
        # Try to find HTTP/HTTPS URLs first
        http_match = re.search(r"(https?://[^\\s\"']+)", stream_url, flags=re.IGNORECASE)
        if http_match:
            return http_match.group(1)
        
        # Handle relative paths
        if stream_url.startswith("/"):
            base = credentials.base_url.rstrip("/")
            return f"{base}{stream_url}"
        
        # Handle protocol-relative URLs
        if stream_url.startswith("//"):
            return f"https:{stream_url}"
        
        return stream_url

    def get_connection_info(self, credentials: Credentials) -> dict[str, str]:
        """Fetch account information from Stalker portal."""
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
                or account.get("expire_billing_date")
                or "Unknown"
            )
            
            if isinstance(expiry, str) and expiry.isdigit():
                expiry = datetime.fromtimestamp(int(expiry)).strftime("%Y-%m-%d %H:%M")
            
            return {
                "Status": str(account.get("status", profile.get("status", "Unknown"))),
                "Expiry": str(expiry),
                "Active/Max Connections": f"{account.get('active_cons', 'Unknown')}/{account.get('max_online', 'Unknown')}",
                "Real URL": credentials.base_url,
                "MAC": credentials.mac_address,
                "Timezone": str(profile.get("default_timezone", "Europe/London")),
            }
            
        except Exception as e:
            logger_service.error(f"Failed to fetch connection info: {e}")
            return {
                "Status": "Error",
                "Error": str(e),
                "Real URL": credentials.base_url,
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
                    description = str(row.get("descr") or row.get("description") or "")
                    entries.append(EpgEntry(title=title, start_at=start_at, end_at=end_at, description=description))
                except (ValueError, TypeError):
                    continue
            
            entries.sort(key=lambda row: row.start_at)
            return entries
            
        except requests.RequestException as e:
            logger_service.error(f"Failed to fetch EPG: {e}")
            return []

    def fetch_now_playing(self, credentials: Credentials, channel_item: MediaItem) -> str:
        """Fetch currently playing program for a channel."""
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
                except (ValueError, TypeError):
                    continue
            
            # Return first entry if no match
            return str(rows[0].get("name") or rows[0].get("title") or "").strip()
            
        except requests.RequestException:
            return ""

    def fetch_series_children(self, credentials: Credentials, item: MediaItem) -> list[MediaItem]:
        """Fetch seasons or episodes for a series."""
        self.connect(credentials)
        
        endpoint = self._get_portal_endpoint()
        
        if item.item_type == "series":
            # Fetch seasons
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
                
            except requests.RequestException as e:
                logger_service.error(f"Failed to fetch seasons: {e}")
                return []
        
        if item.item_type == "season":
            # Fetch episodes
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
                                "episode_number": episode.get("series_number", episode.get("number", "")),
                            },
                        ),
                    )
                return children
                
            except requests.RequestException as e:
                logger_service.error(f"Failed to fetch episodes: {e}")
                return []
        
        return []
