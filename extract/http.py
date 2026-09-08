"""
Shared HTTP layer. All three sources are plain GET requests that can rate-limit
or hiccup, so they should go through one helper with retry + backoff instead of
each fetcher rolling its own.

STUB - not implemented. See the German dashboard's fetch_energy_charts.py
`get()` for a working reference of the same idea (429 -> wait -> retry).
"""

from __future__ import annotations

import config


def get_json(url: str, params: dict | None = None, *, headers: dict | None = None) -> dict:
    """GET `url` with `params`, return parsed JSON.

    Should:
      * retry up to config.HTTP_RETRIES times
      * on HTTP 429 / 5xx, sleep config.HTTP_BACKOFF * 2**attempt (honour a
        Retry-After header if present) then retry
      * raise for other 4xx immediately (bad key, bad params - retrying won't help)
      * use config.HTTP_TIMEOUT

    Used by: eia.py, hf.py
    """
    raise NotImplementedError  # TODO(you): implement retry/backoff GET -> .json()


def get_text(url: str, params: dict | None = None, *, headers: dict | None = None) -> str:
    """Same contract as get_json but returns the raw response body as text.

    Used by: entsoe.py (the Transparency API returns an XML GL_MarketDocument,
    not JSON).
    """
    raise NotImplementedError  # TODO(you): implement retry/backoff GET -> .text
