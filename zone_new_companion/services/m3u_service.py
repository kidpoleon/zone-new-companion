"""M3U playlist service."""

from __future__ import annotations

import re
from typing import Any

import requests
from requests import RequestException

from zone_new_companion.models import Credentials, MediaItem, PlaylistCategory
from zone_new_companion.services.base import PortalService
from zone_new_companion.services.network import DEFAULT_TIMEOUT, create_session
from zone_new_companion.services.network_optimizer import OptimizedSession
from zone_new_companion.services.logger_service import logger_service


class M3UService(PortalService):
    """Service for M3U playlist parsing and streaming."""

    def __init__(self) -> None:
        self._session = OptimizedSession()

    def fetch_categories(self, credentials: Credentials) -> dict[str, list[PlaylistCategory]]:
        """Extract categories from M3U playlist."""
        try:
            content = self._fetch_playlist_content(credentials.base_url)
            categories = self._parse_categories(content)
            return {"Live": categories, "Movies": [], "Series": []}
        except (RequestException, ValueError) as e:
            raise RuntimeError(f"Failed to fetch M3U categories: {e}")

    def fetch_items(self, credentials: Credentials, category: PlaylistCategory) -> list[MediaItem]:
        """Extract items for a specific category from M3U playlist."""
        try:
            content = self._fetch_playlist_content(credentials.base_url)
            items = self._parse_category_items(content, category.id)
            return items
        except (RequestException, ValueError) as e:
            raise RuntimeError(f"Failed to fetch M3U items: {e}")

    def resolve_stream_url(self, credentials: Credentials, item: MediaItem) -> str:
        """Return the stream URL for the media item."""
        return item.stream_url or ""

    def fetch_now_playing(self, credentials: Credentials, item: MediaItem) -> str:
        """M3U playlists don't support now playing information."""
        return ""

    def fetch_epg_for_channel(self, credentials: Credentials, item: MediaItem) -> list[Any]:
        """M3U playlists don't support EPG."""
        return []

    def fetch_connection_info(self, credentials: Credentials) -> dict[str, str]:
        """M3U playlists don't have account info."""
        return {"Type": "M3U Playlist", "URL": credentials.base_url}

    def _fetch_playlist_content(self, url: str) -> str:
        """Fetch M3U playlist content with enhanced error handling."""
        if not url:
            raise ValueError("URL cannot be empty")
        
        logger_service.info(f"Fetching M3U playlist from: {url}")
        
        # Handle XTREAM get.php URLs
        if "get.php" in url:
            # Extract credentials from get.php URL and use XTREAM-like parsing
            return self._fetch_from_get_php(url)
        
        # Handle short URLs and redirects
        if "s.id/" in url or "bit.ly/" in url or "tinyurl.com/" in url:
            return self._fetch_with_redirect_handling(url)
        
        # Standard M3U URL
        try:
            response = self._session.session.get(url, timeout=DEFAULT_TIMEOUT)
            response.raise_for_status()
            
            # Validate content looks like M3U
            content = response.text
            if not content.strip():
                raise ValueError("Empty playlist content")
            
            # Check if it's a valid M3U or try to parse anyway
            if not any(line.strip().startswith('#EXTM3U') for line in content.split('\n')[:10]):
                logger_service.warning("No M3U header found, attempting to parse anyway")
            
            logger_service.info(f"Successfully fetched M3U content: {len(content)} characters")
            return content
            
        except requests.RequestException as e:
            logger_service.error(f"Failed to fetch playlist: {e}")
            raise RuntimeError(f"Failed to fetch playlist: {e}")

    def _fetch_with_redirect_handling(self, url: str) -> str:
        """Handle short URLs and redirects with proper user agents."""
        try:
            # Use a more permissive session for redirects
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/plain, application/x-mpegurl, application/vnd.apple.mpegurl, */*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive'
            }
            
            response = self._session.session.get(
                url, 
                timeout=15,  # Longer timeout for redirects
                headers=headers,
                allow_redirects=True
            )
            response.raise_for_status()
            
            content = response.text
            if not content.strip():
                raise ValueError("Empty playlist content after redirect")
            
            logger_service.info(f"Successfully fetched M3U content via redirect: {len(content)} characters")
            return content
            
        except requests.RequestException as e:
            logger_service.error(f"Failed to fetch playlist via redirect: {e}")
            raise RuntimeError(f"Failed to fetch playlist via redirect: {e}")

    def _fetch_from_get_php(self, url: str) -> str:
        """Handle XTREAM get.php URLs for M3U format."""
        # This is a simplified implementation - in a real scenario, you might need
        # to parse the get.php URL and make appropriate API calls
        # For now, we'll try to fetch it as a direct M3U URL
        response = self._session.session.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        return response.text

    def _parse_categories(self, content: str) -> list[PlaylistCategory]:
        """Parse categories from M3U content and sort alphabetically."""
        categories = set()
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith('#EXTINF:'):
                # Extract category from group-title attribute
                match = re.search(r'group-title="([^"]*)"', line)
                if match:
                    categories.add(match.group(1))
        
        # Sort categories alphabetically and convert to PlaylistCategory objects
        sorted_categories = sorted(categories, key=lambda x: x.lower())
        return [
            PlaylistCategory(
                id=str(i),
                name=category if category else "Uncategorized",
                media_kind="live"
            )
            for i, category in enumerate(sorted_categories)
        ]

    def _parse_category_items(self, content: str, category_id: str) -> list[MediaItem]:
        """Parse items for a specific category from M3U content and sort alphabetically."""
        items = []
        lines = content.split('\n')
        i = 0
        
        # Find the category name by ID
        categories = self._parse_categories(content)
        target_category = ""
        for cat in categories:
            if cat.id == category_id:
                target_category = cat.name
                break
        
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith('#EXTINF:'):
                # Extract metadata
                name_match = re.search(r',(.+)$', line)
                category_match = re.search(r'group-title="([^"]*)"', line)
                
                if name_match and (not target_category or 
                    (category_match and category_match.group(1) == target_category)):
                    
                    name = name_match.group(1).strip()
                    # Get the URL from the next line
                    if i + 1 < len(lines):
                        url = lines[i + 1].strip()
                        if url and not url.startswith('#'):
                            items.append(MediaItem(
                                id=f"m3u_{len(items)}",
                                name=name,
                                media_kind="live",
                                item_type="channel",
                                stream_url=url
                            ))
            i += 1
        
        # Sort items alphabetically (case-insensitive)
        sorted_items = sorted(items, key=lambda x: x.name.lower())
        return sorted_items
