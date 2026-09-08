"""
Hugging Face Hub API - public-model growth as an AI-compute proxy. No key.

Endpoint: {HF_BASE}/models
Useful params:
    full=false, limit=1000, sort=createdAt, direction=-1,
    expand[]=downloads&expand[]=createdAt   (or just parse what comes back)
Pagination: follow the RFC-5988 `Link: <...>; rel="next"` response header.

Each model object has at least: id, createdAt (ISO), downloads, likes, tags.

Two ways to get a time series out of a fundamentally "current snapshot" API:
  1. createdAt is historical -> page the whole catalogue once, bucket by
     month -> models_new_monthly and models_cumulative back to ~2018. One
     expensive backfill, then cheap monthly top-ups.
  2. downloads is point-in-time only -> the collector must snapshot it each
     run and we build history forward.

STUB - not implemented.
"""

from __future__ import annotations

import pandas as pd


def fetch_hf_model_counts(since: str = "2018-01-01") -> pd.DataFrame:
    """Page the model catalogue, bucket by createdAt month.

    Returns a long DataFrame:
        columns = ["timestamp" (month start, UTC), "value", "metric"]
        metric in {"hf_models_new", "hf_models_cumulative"}

    Implementation notes:
      * this is a big paginate - be polite, honour the Link header, maybe cache
        the raw pages under .cache/ so re-runs don't re-hit everything
      * createdAt can be missing on very old repos - drop or floor to 2018
    """
    raise NotImplementedError  # TODO(you): paginate models, groupby month


def snapshot_hf_downloads(top_n: int = 500) -> pd.DataFrame:
    """One-shot snapshot of downloads on the top-N models, for logging forward.

    Returns a long DataFrame:
        columns = ["timestamp" (now, UTC), "value", "metric"]
        metric  = "hf_downloads_topN"
    """
    raise NotImplementedError  # TODO(you): GET sort=downloads, sum top_n, stamp now
