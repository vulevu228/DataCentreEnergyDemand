"""
ENTSO-E Transparency Platform  ->  EU actual total load per bidding zone.

Endpoint: a single URL ({ENTSOE_BASE}) with everything in the query string:
    securityToken, documentType=A65 (system total load),
    processType=A16 (realised / actual),
    outBiddingZone_Domain=<EIC code>,
    periodStart / periodEnd = yyyyMMddHHmm in UTC

Two things make this awkward:
  * the reply is XML (a GL_MarketDocument), not JSON
  * one request may not span more than ~1 year, so long ranges are chunked

Output of fetch_entsoe_load(): a long DataFrame
    columns = ["timestamp" (UTC, tz-aware), "value" (MW), "metric"]
    metric  = "load_mw"
"""
from __future__ import annotations

import time
import xml.etree.ElementTree as ET
from datetime import timedelta

import pandas as pd

import config
from extract import net  # shared HTTP layer; NOT the stdlib "http"


def fetch_entsoe_load(eic_domain: str, start: str, end: str, token: str) -> pd.DataFrame:
    """Pull one bidding zone's actual total load for [start, end] (UTC)."""
    ts_start = pd.to_datetime(start, utc=True)
    ts_end = pd.to_datetime(end, utc=True)

    frames: list[pd.DataFrame] = []
    window_start = ts_start

    # --- chunk the range into <= ENTSOE_MAX_DAYS pieces --------------------
    while window_start < ts_end:
        window_end = min(window_start + timedelta(days=config.ENTSOE_MAX_DAYS), ts_end)

        params = {
            "securityToken": token,
            "documentType": config.ENTSOE_LOAD_DOCTYPE,     # A65
            "processType": config.ENTSOE_PROCESS_ACTUAL,    # A16
            "outBiddingZone_Domain": eic_domain,
            "periodStart": window_start.strftime("%Y%m%d%H%M"),
            "periodEnd": window_end.strftime("%Y%m%d%H%M"),
        }
        print(f"ENTSO-E: {eic_domain}  {window_start.date()} -> {window_end.date()}")

        xml_text = net.get_text(config.ENTSOE_BASE, params=params)
        chunk = _parse_gl_document(xml_text)
        if not chunk.empty:
            frames.append(chunk)

        window_start = window_end
        time.sleep(1)          # stay well under the ~400 requests/min limit

    # --- combine + clean -------------------------------------------------
    if not frames:
        return pd.DataFrame(columns=["timestamp", "value", "metric"])

    df = pd.concat(frames, ignore_index=True)
    df["metric"] = "load_mw"
    df = (
        df.dropna(subset=["timestamp", "value"])
        .drop_duplicates(subset=["timestamp"])
        .sort_values("timestamp")
        .loc[:, ["timestamp", "value", "metric"]]
        .reset_index(drop=True)
    )
    return df


def _parse_gl_document(xml_text: str) -> pd.DataFrame:
    """XML GL_MarketDocument string  ->  DataFrame[timestamp, value] (hourly)."""
    # The API returns a short XML "acknowledgement" doc instead of data when the
    # query matched nothing - treat that as an empty result, not an error.
    if not xml_text.strip() or "No matching data" in xml_text:
        return pd.DataFrame(columns=["timestamp", "value"])

    root = ET.fromstring(xml_text)

    # ElementTree keeps the XML namespace as a "{uri}tag" prefix on every tag.
    # Build a helper that prefixes our searches the same way (or not, if the
    # document has no namespace).
    if "}" in root.tag:
        uri = root.tag.split("}")[0].strip("{")
        ns = {"ns": uri}
        def q(tag: str) -> str:
            return f"ns:{tag}"
    else:
        ns = {}
        def q(tag: str) -> str:
            return tag

    rows: list[tuple] = []
    for series in root.findall(f".//{q('TimeSeries')}", ns):
        for period in series.findall(f".//{q('Period')}", ns):
            start_str = period.find(f".//{q('timeInterval')}/{q('start')}", ns).text
            resolution = period.find(f".//{q('resolution')}", ns).text  # e.g. "PT15M", "PT60M"

            start_dt = pd.to_datetime(start_str, utc=True)
            step = pd.Timedelta(resolution)                # "PT15M" -> 15 minutes

            for point in period.findall(f".//{q('Point')}", ns):
                pos = int(point.find(f".//{q('position')}", ns).text)
                qty = float(point.find(f".//{q('quantity')}", ns).text)
                # position is 1-based: ts = start + (position - 1) * resolution
                rows.append((start_dt + (pos - 1) * step, qty))

    if not rows:
        return pd.DataFrame(columns=["timestamp", "value"])

    df = pd.DataFrame(rows, columns=["timestamp", "value"])
    # Some zones report every 15 min, others hourly - normalise to hourly means
    # so every region lands on the same grid.
    df = df.set_index("timestamp").resample("h").mean().dropna().reset_index()
    return df
