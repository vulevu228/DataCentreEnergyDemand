"""
Turn the per-source DataFrames into the one tidy panel (METHODOLOGY.md §3)
and derive the comparison metrics.

STUB - not implemented.
"""

from __future__ import annotations

import pandas as pd

import config


def to_panel_rows(
    df: pd.DataFrame,
    *,
    region_id: str,
    region_label: str,
    source: str,
) -> pd.DataFrame:
    """Reshape a fetcher's [timestamp, value, metric] frame into PANEL_COLUMNS.

    Adds region_id, region_label, source, is_forecast=0, retrieved_at=now.
    Optionally resamples to config.RESAMPLE (daily mean) here.
    """
    raise NotImplementedError  # TODO(you): assign cols, resample, reorder to config.PANEL_COLUMNS


def add_load_index(panel: pd.DataFrame, baseline_year: int = config.BASELINE_YEAR) -> pd.DataFrame:
    """For every region with a load_* metric, append a 'load_index' metric:
    value / mean(value in baseline_year for that region) * 100.

    Lets Northern Virginia and Ireland sit on the same chart axis despite very
    different absolute sizes.
    """
    raise NotImplementedError  # TODO(you): groupby region, normalise, concat back


def add_yoy_growth(panel: pd.DataFrame) -> pd.DataFrame:
    """Append a 'yoy_growth_pct' metric per region from the load series
    (this month vs the same month a year earlier)."""
    raise NotImplementedError  # TODO(you)


def build_panel(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """frames: {region_id: fetcher_output_df}. Run to_panel_rows on each,
    concat, add_load_index, add_yoy_growth, sort, return the full panel
    ready to write to config.PANEL_CSV."""
    raise NotImplementedError  # TODO(you): orchestrate the helpers above
