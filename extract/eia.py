"""
EIA Open Data API v2  ->  US hourly electricity demand.

Two routes, picked by whether we want a whole region or one sub-area:
  * region level :  {EIA_BASE}/electricity/rto/region-data/data
        facets: respondent=PJM, type=D              (D = demand)
  * sub-BA level :  {EIA_BASE}/electricity/rto/region-sub-ba-data/data
        facets: parent=PJM, subba=DOM               (DOM = Dominion / N. Virginia)

Common query params:
    api_key, frequency=hourly, data[0]=value,
    start=YYYY-MM-DDTHH, end=YYYY-MM-DDTHH,
    sort[0][column]=period, sort[0][direction]=asc,
    offset, length            (max 5000 rows per call -> page on offset)

Response JSON: rows live under response["response"]["data"], each row has
    period  (LOCAL clock time, e.g. "2024-03-01T05"), respondent, type, value

Output of fetch_eia_demand(): a long DataFrame
    columns = ["timestamp" (UTC, tz-aware), "value" (MWh), "metric"]
    metric  = "load_mwh"
"""
from __future__ import annotations

import pandas as pd

import config
from extract import net  # shared HTTP layer (retry/back-off); NOT the stdlib "http"

# EIA "respondent" codes do not carry a timezone, so map the ones we use to a
# real IANA zone. Anything not listed falls back to UTC (and is flagged by the
# fact that its local/UTC offset will look wrong - add it here when needed).
_TZ_BY_RESPONDENT = {
    "PJM": "America/New_York",
    "ERCO": "America/Chicago",
    "SWPP": "America/Chicago",
    "MISO": "America/Chicago",
    "SPP": "America/Chicago",
    "NYIS": "America/New_York",
    "SOCO": "America/Chicago",
}

_PAGE = 5000          # EIA hard cap on rows per call
_MAX_PAGES = 400      # safety valve: 400 * 5000 = 2,000,000 rows ~= 200 years hourly


def _period_to_utc(period: str, respondent: str) -> pd.Timestamp:
    """'2024-03-01T05' + respondent  ->  tz-aware UTC Timestamp.

    Steps: parse as naive -> attach the respondent's local zone -> convert to
    UTC. During the autumn DST fold one local hour happens twice; `ambiguous`
    then can't be resolved, so we mark it NaT and drop it upstream.
    """
    tz = _TZ_BY_RESPONDENT.get(respondent, "UTC")
    naive = pd.to_datetime(period, format="%Y-%m-%dT%H", errors="coerce")
    if pd.isna(naive):
        return pd.NaT
    try:
        return naive.tz_localize(tz, ambiguous="NaT", nonexistent="NaT").tz_convert("UTC")
    except Exception:            # noqa: BLE001 - any tz failure -> unusable timestamp
        return pd.NaT


def fetch_eia_demand(
    respondent: str,
    start: str,
    end: str,
    api_key: str,
    *,
    sub_ba: str | None = None,
    demand_type: str = "D",
) -> pd.DataFrame:
    """Pull one region's (or one sub-BA's) hourly demand series for [start, end].

    Pagination: keep asking with offset += length until the API returns an empty
    data[] page (or the safety cap is hit).
    """
    # 1. params shared by both routes ---------------------------------------
    params = {
        "api_key": api_key,
        "frequency": "hourly",
        "data[0]": "value",
        "start": start,
        "end": end,
        "sort[0][column]": "period",
        "sort[0][direction]": "asc",
        "offset": 0,
        "length": _PAGE,
    }

    # 2. route + facets (filters) -----------------------------------------
    # EIA v2 facets are ARRAYS: the key must end with "[]". A scalar
    # "facets[respondent]=PJM" makes the API answer HTTP 500.
    if sub_ba is None:
        url = f"{config.EIA_BASE}/electricity/rto/region-data/data"
        params["facets[respondent][]"] = respondent
        params["facets[type][]"] = demand_type
    else:
        url = f"{config.EIA_BASE}/electricity/rto/region-sub-ba-data/data"
        params["facets[parent][]"] = respondent
        params["facets[subba][]"] = sub_ba
        # the sub-BA route only knows the 'parent' and 'subba' facets; it is
        # demand-only, so there is no 'type' to pass (adding one -> HTTP 400).

    print(f"EIA: {respondent} sub_ba={sub_ba}  {start} -> {end}")

    # 3. page through the result ----------------------------------------
    all_rows: list[dict] = []
    for _ in range(_MAX_PAGES):
        payload = net.get_json(url, params=params)
        rows = payload.get("response", {}).get("data", [])
        if not rows:
            break
        all_rows.extend(rows)
        print(f"  {len(all_rows)} rows ...")
        params["offset"] += _PAGE
    else:
        print("  ! hit _MAX_PAGES - series may be truncated")

    # 4. shape into the tidy frame ------------------------------------
    if not all_rows:
        return pd.DataFrame(columns=["timestamp", "value", "metric"])

    df = pd.DataFrame(all_rows)
    df["timestamp"] = df["period"].map(lambda p: _period_to_utc(p, respondent))
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["metric"] = "load_mwh"

    df = (
        df.dropna(subset=["timestamp", "value"])
        .drop_duplicates(subset=["timestamp"])     # DST fold can repeat an hour
        .sort_values("timestamp")
        .loc[:, ["timestamp", "value", "metric"]]
        .reset_index(drop=True)
    )
    return df
