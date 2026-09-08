"""
Shared HTTP layer for all three sources.

Every source (EIA, ENTSO-E, Hugging Face) is a plain GET that can rate-limit
(HTTP 429) or hiccup (HTTP 5xx, dropped connection). Instead of each fetcher
rolling its own retry loop, they all call through here.

The module is called `net` and not `http` on purpose: `http` is a Python
standard-library package, so `import http` inside this package would import the
stdlib, not this file.

Reference for the same idea: GermanEnergyDashboard/fetch_energy_charts.py `get()`
(429 -> wait -> retry).
"""
from __future__ import annotations

import time

import requests

import config  # resolves because run_extract.py (repo root) is the entry point


def _sleep_for_retry(response: requests.Response | None, attempt: int) -> None:
    """Wait before the next attempt.

    Exponential back-off: HTTP_BACKOFF * 2**attempt  ->  2s, 4s, 8s, 16s, ...
    If the server sent a `Retry-After` header (429 responses often do), honour
    that instead because it is the server telling us exactly how long to wait.
    """
    backoff = config.HTTP_BACKOFF * (2 ** attempt)
    wait = backoff
    if response is not None:
        try:
            wait = int(response.headers.get("Retry-After", backoff))
        except (TypeError, ValueError):
            wait = backoff
    print(f"  retry in {wait}s (attempt {attempt + 1}/{config.HTTP_RETRIES})")
    time.sleep(wait)


def _request(url: str, params: dict | None, headers: dict | None) -> requests.Response:
    """GET `url` with retry/back-off, return the raw Response.

    Retries on 429, on 5xx, and on connection/timeout errors. Any other 4xx
    (e.g. 400 bad query, 401 bad key) is a real answer and is raised at once by
    `raise_for_status()` - retrying would not help.
    """
    last = ""
    for attempt in range(config.HTTP_RETRIES):
        try:
            r = requests.get(
                url, params=params, headers=headers, timeout=config.HTTP_TIMEOUT
            )
            if r.status_code == 429 or r.status_code >= 500:
                last = f"HTTP {r.status_code}: {r.text[:200]}"
                _sleep_for_retry(r, attempt)
                continue
            r.raise_for_status()
            return r
        except (requests.ConnectionError, requests.Timeout) as e:
            # network-level failure: no response object to inspect
            last = str(e)
            if attempt == config.HTTP_RETRIES - 1:
                raise
            print(f"  connection error: {e}")
            _sleep_for_retry(None, attempt)

    # every attempt was a 429/5xx - report what the server actually said
    raise RuntimeError(f"gave up after {config.HTTP_RETRIES} attempts: {url}\n  last: {last}")


def get_json(url: str, params: dict | None = None, *, headers: dict | None = None) -> dict | list:
    """GET `url` and return the parsed JSON body. Used by eia.py and hf.py."""
    return _request(url, params, headers).json()


def get_text(url: str, params: dict | None = None, *, headers: dict | None = None) -> str:
    """GET `url` and return the raw body as text.

    Used by entsoe.py: the Transparency API replies with an XML
    GL_MarketDocument, not JSON.
    """
    return _request(url, params, headers).text
