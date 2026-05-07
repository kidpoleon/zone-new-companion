"""HTTP helpers."""

from __future__ import annotations

from urllib.parse import urljoin

import requests

DEFAULT_TIMEOUT = 15


def normalize_url(base_url: str, path: str = "") -> str:
    """Normalize base url + path into one absolute URL."""
    cleaned = base_url.strip()
    if not cleaned.startswith(("http://", "https://")):
        cleaned = f"http://{cleaned}"
    return urljoin(f"{cleaned.rstrip('/')}/", path.lstrip("/"))


def create_session() -> requests.Session:
    """Create shared requests session with stable user-agent."""
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(pool_connections=50, pool_maxsize=50, max_retries=0)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (QtEmbedded; U; Linux; C) "
                "AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp"
            ),
            "Accept": "*/*",
        },
    )
    return session
