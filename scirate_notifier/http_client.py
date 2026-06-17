"""HTTP client for fetching SciRate pages with browser-like fingerprints."""

from __future__ import annotations

import logging

import requests

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 20
BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
BROWSER_HEADERS = {
    "User-Agent": BROWSER_USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}


def fetch_html(url: str, session: requests.Session | None = None) -> str:
    """Fetch HTML, preferring curl_cffi TLS impersonation for datacenter IPs."""
    last_error: Exception | None = None

    try:
        return _fetch_with_curl_cffi(url)
    except Exception as exc:
        last_error = exc
        logger.warning("curl_cffi fetch failed, falling back to requests: %s", exc)

    http = session or requests.Session()
    http.trust_env = False
    response = http.get(
        url,
        headers=BROWSER_HEADERS,
        timeout=REQUEST_TIMEOUT,
        proxies={"http": None, "https": None},
    )
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        if last_error is not None:
            raise requests.HTTPError(
                f"{exc} (curl_cffi also failed: {last_error})",
                response=response,
            ) from exc
        raise
    return response.text


def _fetch_with_curl_cffi(url: str) -> str:
    from curl_cffi import requests as curl_requests

    response = curl_requests.get(
        url,
        impersonate="chrome120",
        headers=BROWSER_HEADERS,
        timeout=REQUEST_TIMEOUT,
        proxies={"http": None, "https": None},
    )
    response.raise_for_status()
    return response.text
