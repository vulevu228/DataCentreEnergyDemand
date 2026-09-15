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

import time
from collections import Counter

import pandas as pd

import config
from extract import net  # shared HTTP layer (retry/back-off, incl. HF's 429s)

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

    # Bucket into a month->count Counter as pages come in, instead of keeping
    # every individual timestamp in a list. A full 2023-> walk is 3M+ models;
    # retaining each one (confirmed live 2026-09-15: killed by the host for
    # system memory pressure around 1.2M models) is needless - only ~40
    # month buckets are ever needed.
    month_counts: Counter[pd.Timestamp] = Counter()
    url = _MODELS_URL
    pages = 0
    total = 0
    oldest_seen: pd.Timestamp | None = None

    while url and pages < _MAX_PAGES:
        pages += 1
        # net.get() (not net.get_json) because we need the Link response
        # header for cursor pagination, and its retry/back-off handles the
        # 429s HF's unauthenticated endpoint throws under sustained paging.
        r = net.get(
            url,
            params=params if "?" not in url else None,   # Link-header URLs already carry the query
        )
        batch = r.json()
        if not batch:
            break

        stop = False
        for m in batch:
            # a few very old models have no createdAt; treat them as pre-history
            c = pd.to_datetime(m.get("createdAt", "2018-01-01T00:00:00.000Z"), utc=True)
            if c >= since_ts:
                month_counts[pd.Timestamp(year=c.year, month=c.month, day=1)] += 1
                total += 1
                oldest_seen = c
            else:
                stop = True          # list is sorted desc -> everything after is older too
        if stop:
            break

        # Link: <https://huggingface.co/api/models?...>; rel="next"
        link = r.headers.get("Link", "")
        url = link.split(";")[0].strip("<> ") if 'rel="next"' in link else None

        if pages % 20 == 0:
            print(f"  hf: {pages} pages ({total:,} models so far, back to "
                  f"{oldest_seen.date() if oldest_seen else '?'})", flush=True)
        # HF's unauthenticated `RateLimit-Policy` header (confirmed live
        # 2026-09-15) is 500 requests / 300s, i.e. a 0.6s floor - 0.3s was
        # guaranteed to trigger periodic 429 backoff under sustained paging.
        time.sleep(0.65)

    if pages >= _MAX_PAGES:
        print(f"  ! hf: stopped at _MAX_PAGES ({_MAX_PAGES}) - counts may be partial")

    if not month_counts:
        return pd.DataFrame(columns=["timestamp", "value", "metric"])

    new = (
        pd.Series(month_counts)
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
    batch = net.get_json(
        _MODELS_URL,
        params={"limit": top_n, "sort": "downloads", "direction": -1},
    )
    total = sum(m.get("downloads", 0) for m in batch)

    return pd.DataFrame(
        [{
            "timestamp": pd.Timestamp.now(tz="UTC"),
            "value": float(total),
            "metric": "hf_downloads_topN",
        }]
    )
