"""
EIA Open Data API v2 - US hourly electricity demand.

Two routes matter:
  * region-level:  {EIA_BASE}/electricity/rto/region-data/data
        facets: respondent=PJM, type=D          (D = demand)
  * sub-BA level:  {EIA_BASE}/electricity/rto/region-sub-ba-data/data
        facets: parent=PJM, subba=DOM           (DOM = Dominion / N. Virginia)

Common query params:
    api_key, frequency=hourly, data[0]=value,
    start=YYYY-MM-DDTHH, end=YYYY-MM-DDTHH,
    sort[0][column]=period, sort[0][direction]=asc,
    offset, length (max 5000 rows per call -> paginate on offset)

Response: JSON, rows under response.data[], each row has
    period (local time, e.g. "2024-03-01T05"), respondent, type, value, ...

STUB - not implemented.
"""

from __future__ import annotations

import pandas as pd


def fetch_eia_demand(
    respondent: str,
    start: str,
    end: str,
    api_key: str,
    *,
    sub_ba: str | None = None,
    demand_type: str = "D",
) -> pd.DataFrame:
    """Pull one region's (or sub-BA's) hourly series for [start, end].

    Returns a long DataFrame:
        columns = ["timestamp" (UTC, tz-aware), "value" (MWh), "metric"]
        metric  = "load_mwh"

    Implementation notes:
      * pick the route from whether sub_ba is None
      * paginate: keep requesting with offset += length until data[] is empty
      * EIA 'period' is local clock time; convert to UTC. The row also carries a
        timezone facet you can request, or map respondent -> tz yourself.
      * de-dup on timestamp (DST fall-back gives a repeated hour)
    """
    raise NotImplementedError  # TODO(you): build params, paginate, normalise to UTC


def _period_to_utc(period: str, respondent: str) -> pd.Timestamp:
    """'2024-03-01T05' + a respondent -> tz-aware UTC Timestamp. Helper for above."""
    raise NotImplementedError  # TODO(you)
