"""
Hugging Face Hub API  ->  public-model growth, used as an AI-compute proxy.

No key needed. Two things are collected:
  * fetch_hf_model_counts()  - walk the model catalogue newest-first, bucket by
    createdAt month, emit "hf_models_new" (per month) and
    "hf_models_cumulative" (running total).
  * snapshot_hf_downloads()  - one point-in-time total of downloads on the
    top-N models. The API only gives a rolling figure, so history has to be
    built by appending a snapshot on every run.

Both return the tidy shape used everywhere else:
    columns = ["timestamp", "value", "metric"]

Caveat (see METHODOLOGY.md sec 5): HF is the OPEN-model slice only. It shows the
field scaling, it is not proportional to energy use.
"""
from __future__ import annotations

import pandas as pd
import requests

import config

_MODELS_URL = f"{config.HF_BASE}/models"
_MAX_PAGES = 3000          # safety valve; 3000 * 1000 = 3,000,000 models


def fetch_hf_model_counts(since: str = "2020-01-01") -> pd.DataFrame:
    """Page the model list newest-first, stop once we pass `since`, bucket by month."""
    since_ts = pd.to_datetime(since, utc=True)

    params = {
        "limit": 1000,
        "sort": "createdAt",
        "direction": -1,            # newest first, so we can stop early at `since`
        "expand[]": "createdAt",    # the list endpoint omits createdAt unless asked
    }

    created: list[pd.Timestamp] = []
    url = _MODELS_URL
    pages = 0

    while url and pages < _MAX_PAGES:
        pages += 1
        # requests directly (not net.get_json) because we need the Link header
        # for pagination. HF is reliable and key-less, so a plain call is fine.
        r = requests.get(
            url,
            params=params if "?" not in url else None,   # Link-header URLs already carry the query
            timeout=config.HTTP_TIMEOUT,
        )
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break

        stop = False
        for m in batch:
            # a few very old models have no createdAt; treat them as pre-history
            c = pd.to_datetime(m.get("createdAt", "2018-01-01T00:00:00.000Z"), utc=True)
            if c >= since_ts:
                created.append(c)
            else:
                stop = True          # list is sorted desc -> everything after is older too
        if stop:
            break

        # Link: <https://huggingface.co/api/models?...>; rel="next"
        link = r.headers.get("Link", "")
        url = link.split(";")[0].strip("<> ") if 'rel="next"' in link else None

    if pages >= _MAX_PAGES:
        print(f"  ! hf: stopped at _MAX_PAGES ({_MAX_PAGES}) - counts may be partial")

    if not created:
        return pd.DataFrame(columns=["timestamp", "value", "metric"])

    # bucket every creation date to the first of its month. Drop the tz first so
    # to_period() doesn't warn; join.py normalises the panel back to UTC.
    months = pd.Series(created).dt.tz_localize(None).dt.to_period("M").dt.to_timestamp()

    new = (
        months.value_counts()
        .sort_index()
        .rename_axis("timestamp")
        .reset_index(name="value")
    )
    new["metric"] = "hf_models_new"

    cum = new.copy()
    cum["value"] = cum["value"].cumsum()
    cum["metric"] = "hf_models_cumulative"

    return pd.concat([new, cum], ignore_index=True)


def snapshot_hf_downloads(top_n: int = 500) -> pd.DataFrame:
    """One row: total downloads across the current top-N models, stamped now (UTC)."""
    r = requests.get(
        _MODELS_URL,
        params={"limit": top_n, "sort": "downloads", "direction": -1},
        timeout=config.HTTP_TIMEOUT,
    )
    r.raise_for_status()
    total = sum(m.get("downloads", 0) for m in r.json())

    return pd.DataFrame(
        [{
            "timestamp": pd.Timestamp.now(tz="UTC"),
            "value": float(total),
            "metric": "hf_downloads_topN",
        }]
    )
