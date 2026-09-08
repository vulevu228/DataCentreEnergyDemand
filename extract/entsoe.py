"""
ENTSO-E Transparency Platform - EU actual total load per zone.

Endpoint: {ENTSOE_BASE}  (single /api, everything is query params)
Params for total load, realised:
    securityToken, documentType=A65, processType=A16,
    outBiddingZone_Domain=<EIC>,
    periodStart=YYYYMMDDHHMM, periodEnd=YYYYMMDDHHMM   (UTC, note the format)

Response: XML GL_MarketDocument. Shape:
    <GL_MarketDocument>
      <TimeSeries>
        <Period>
          <timeInterval><start>..Z</start><end>..Z</end></timeInterval>
          <resolution>PT15M</resolution|PT60M>
          <Point><position>1</position><quantity>3456</quantity></Point>
          ...

Gotchas:
  * one call is capped at ~1 year -> chunk with config.ENTSOE_MAX_DAYS
  * position is an index into the interval at `resolution`, not a timestamp -
    reconstruct: ts = start + (position - 1) * resolution
  * some zones report PT15M, some PT60M; resample to hourly
  * an empty / 'No matching data found' body is a valid "nothing here", not an error

STUB - not implemented.
"""

from __future__ import annotations

import pandas as pd


def fetch_entsoe_load(eic_domain: str, start: str, end: str, token: str) -> pd.DataFrame:
    """Pull one bidding zone's actual total load for [start, end].

    Returns a long DataFrame:
        columns = ["timestamp" (UTC, tz-aware), "value" (MW), "metric"]
        metric  = "load_mw"

    Implementation notes:
      * loop over <=ENTSOE_MAX_DAYS chunks, concat
      * parse XML with xml.etree; mind the default namespace on GL_MarketDocument
      * build timestamps from timeInterval start + position*resolution
    """
    raise NotImplementedError  # TODO(you): chunk the range, GET xml, parse points


def _parse_gl_document(xml_text: str) -> pd.DataFrame:
    """XML GL_MarketDocument string -> DataFrame[timestamp, value]. Helper for above."""
    raise NotImplementedError  # TODO(you)
