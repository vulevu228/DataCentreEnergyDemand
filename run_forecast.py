"""
Analysis stage (METHODOLOGY.md sec 4): fit each region's load_index trend on
pre-AI data (up to config.FORECAST_SPLIT), project it forward, and append the
projection as is_forecast=1 rows in the panel. This is what makes the
"actual vs projected" gap chart possible in Power BI.

Uses Prophet (yearly + weekly seasonality - daily load is strongly seasonal,
a naive straight line would confound seasonal swings with the AI-era bend)
fit per region on data up to FORECAST_SPLIT only, then projected through the
last actual date available for that region.

    python run_forecast.py
"""
from __future__ import annotations

import logging

import pandas as pd

import config

logging.getLogger("cmdstanpy").setLevel(logging.WARNING)
logging.getLogger("prophet").setLevel(logging.WARNING)

from prophet import Prophet  # noqa: E402 - import after logger config to suppress its init chatter


def _fit_and_project(series: pd.DataFrame) -> pd.DataFrame:
    """series: ['ds','y'] tz-aware daily load_index, full actual history for one region.

    Fits on rows up to and including FORECAST_SPLIT, projects daily from the
    day after the split through the last actual date in `series`.
    """
    split = pd.Timestamp(config.FORECAST_SPLIT, tz="UTC")
    train = series[series["ds"] <= split]
    if len(train) < 365:
        return pd.DataFrame(columns=["timestamp", "value"])

    horizon_end = series["ds"].max().tz_localize(None)
    train_fit = train.assign(ds=train["ds"].dt.tz_localize(None))

    m = Prophet(yearly_seasonality=True, weekly_seasonality=True, daily_seasonality=False)
    m.fit(train_fit)

    future = pd.DataFrame({
        "ds": pd.date_range(split.tz_localize(None) + pd.Timedelta(days=1), horizon_end, freq="D")
    })
    if future.empty:
        return pd.DataFrame(columns=["timestamp", "value"])

    fcst = m.predict(future)
    return pd.DataFrame({
        "timestamp": pd.to_datetime(fcst["ds"], utc=True),
        "value": fcst["yhat"],
    })


def main() -> int:
    # pandas 3.x's read_csv(parse_dates=...) no longer reliably yields a
    # datetime dtype (confirmed live 2026-09-15: comes back as plain str) -
    # convert explicitly instead of trusting the parse_dates kwarg.
    panel = pd.read_csv(config.PANEL_CSV)
    panel["timestamp"] = pd.to_datetime(panel["timestamp"], utc=True, format="ISO8601")
    panel["retrieved_at"] = pd.to_datetime(panel["retrieved_at"], utc=True, format="ISO8601")
    load_index = panel[(panel["metric"] == "load_index") & (panel["is_forecast"] == 0)]
    if load_index.empty:
        raise SystemExit("no load_index rows in the panel - run run_extract.py first")

    projected_blocks = []
    for region_id, grp in load_index.groupby("region_id", sort=False):
        series = (
            grp[["timestamp", "value"]]
            .rename(columns={"timestamp": "ds", "value": "y"})
            .sort_values("ds")
        )
        proj = _fit_and_project(series)
        if proj.empty:
            print(f"  ! {region_id}: not enough pre-{config.FORECAST_SPLIT} history, skipped")
            continue

        block = proj.copy()
        block["region_id"] = region_id
        block["region_label"] = grp["region_label"].iloc[0]
        block["metric"] = "load_index"
        block["source"] = grp["source"].iloc[0]
        block["is_forecast"] = 1
        block["retrieved_at"] = pd.Timestamp.now(tz="UTC")
        projected_blocks.append(block[config.PANEL_COLUMNS])
        print(f"  {region_id}: projected {len(block)} days from {config.FORECAST_SPLIT}")

    if not projected_blocks:
        raise SystemExit("no projections produced - nothing to add")

    existing = panel[panel["is_forecast"] == 0]  # drop any prior projection, recompute clean
    updated = (
        pd.concat([existing, *projected_blocks], ignore_index=True)
        .sort_values(["region_id", "metric", "is_forecast", "timestamp"])
        .reset_index(drop=True)
    )

    updated.to_csv(config.PANEL_CSV, index=False)
    n_forecast = int((updated["is_forecast"] == 1).sum())
    print(f"\n{len(updated):,} rows | {n_forecast:,} forecast rows -> {config.PANEL_CSV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
