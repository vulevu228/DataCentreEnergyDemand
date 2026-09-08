"""
Turn the per-source fetcher outputs into the one tidy panel (METHODOLOGY.md
sec 3) and derive the comparison metrics.

Every fetcher returns the same 3 columns: ["timestamp", "value", "metric"].
This module:
  1. to_panel_rows()  - stamps region/source/bookkeeping columns onto one
                        fetcher frame and (optionally) resamples load to daily.
  2. add_load_index() - per region, appends "load_index" = value / baseline-year
                        mean * 100, so differently sized regions share a y-axis.
  3. add_yoy_growth() - per region, appends "yoy_growth_pct" (this month vs the
                        same month a year earlier).
  4. build_panel()    - runs 1 on every frame, concatenates, then 2 and 3.

Nothing here calls the network.
"""
from __future__ import annotations

import pandas as pd

import config

_NOW = lambda: pd.Timestamp.now(tz="UTC")   # noqa: E731 - short helper for retrieved_at


def to_panel_rows(
    df: pd.DataFrame,
    *,
    region_id: str,
    region_label: str,
    source: str,
) -> pd.DataFrame:
    """One fetcher frame ([timestamp, value, metric]) -> rows in PANEL_COLUMNS.

    Load metrics are resampled to config.RESAMPLE (default "D" = daily mean);
    already-monthly proxy metrics are passed through untouched.
    """
    if df.empty:
        return pd.DataFrame(columns=config.PANEL_COLUMNS)

    # Fetchers disagree on tz: EIA/ENTSO-E are tz-aware UTC, HF month buckets are
    # tz-naive. Force the whole column to tz-aware UTC so the panel can be sorted
    # and compared. (naive values are read as UTC, aware values are converted.)
    df = df.assign(timestamp=pd.to_datetime(df["timestamp"], utc=True))

    out_parts = []
    for metric, grp in df.groupby("metric", sort=False):
        s = grp.set_index("timestamp")["value"].sort_index()
        if metric in config.LOAD_METRICS and config.RESAMPLE:
            s = s.resample(config.RESAMPLE).mean().dropna()
        out_parts.append(pd.DataFrame({"timestamp": s.index, "value": s.values, "metric": metric}))

    out = pd.concat(out_parts, ignore_index=True)
    out["region_id"] = region_id
    out["region_label"] = region_label
    out["source"] = source
    out["is_forecast"] = 0
    out["retrieved_at"] = _NOW()
    return out[config.PANEL_COLUMNS]


def add_load_index(panel: pd.DataFrame, baseline_year: int = config.BASELINE_YEAR) -> pd.DataFrame:
    """Append a 'load_index' metric per region: value / mean(baseline_year) * 100."""
    load = panel[panel["metric"].isin(config.LOAD_METRICS)]
    if load.empty:
        return panel

    new_blocks = []
    for region_id, grp in load.groupby("region_id", sort=False):
        base = grp.loc[grp["timestamp"].dt.year == baseline_year, "value"].mean()
        if not base or pd.isna(base):
            print(f"  ! load_index skipped for {region_id}: no data in {baseline_year}")
            continue
        block = grp.copy()
        block["value"] = block["value"] / base * 100.0
        block["metric"] = "load_index"
        new_blocks.append(block)

    if not new_blocks:
        return panel
    return pd.concat([panel, *new_blocks], ignore_index=True)


def add_yoy_growth(panel: pd.DataFrame) -> pd.DataFrame:
    """Append a 'yoy_growth_pct' metric per region: monthly mean load vs 12 months back."""
    load = panel[panel["metric"].isin(config.LOAD_METRICS)]
    if load.empty:
        return panel

    new_blocks = []
    for region_id, grp in load.groupby("region_id", sort=False):
        monthly = (
            grp.set_index("timestamp")["value"].sort_index()
            .resample("MS").mean()
        )
        yoy = monthly.pct_change(12) * 100.0
        yoy = yoy.dropna()
        if yoy.empty:
            continue
        label = grp["region_label"].iloc[0]
        src = grp["source"].iloc[0]
        new_blocks.append(pd.DataFrame({
            "region_id": region_id,
            "region_label": label,
            "metric": "yoy_growth_pct",
            "timestamp": yoy.index,
            "value": yoy.values,
            "source": src,
            "is_forecast": 0,
            "retrieved_at": _NOW(),
        })[config.PANEL_COLUMNS])

    if not new_blocks:
        return panel
    return pd.concat([panel, *new_blocks], ignore_index=True)


def build_panel(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """{region_id: fetcher_output_df} -> the full panel, ready for PANEL_CSV.

    region_label + source come from config.REGION_META; an unknown region_id
    falls back to (region_id, "unknown") with a warning.
    """
    rows = []
    for region_id, df in frames.items():
        label, source = config.REGION_META.get(region_id, (region_id, "unknown"))
        if source == "unknown":
            print(f"  ! {region_id} not in config.REGION_META - labelling it 'unknown'")
        rows.append(to_panel_rows(df, region_id=region_id, region_label=label, source=source))

    panel = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=config.PANEL_COLUMNS)
    panel = add_load_index(panel)
    panel = add_yoy_growth(panel)

    return (
        panel.dropna(subset=["value"])
        .sort_values(["region_id", "metric", "timestamp"])
        .reset_index(drop=True)
    )
