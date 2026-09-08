"""
CLI entry point. Wires the fetchers in extract/ to the region config in
config.py and writes the tidy panel to data/demand_panel.csv.

    python run_extract.py --sources eia,entsoe,hf --since 2019-01-01
    python run_extract.py --sources hf            # just the proxy top-up

Keys are read from a local .env (see .env.example):
    EIA_API_KEY     - instant from https://www.eia.gov/opendata/register.php
    ENTSOE_API_KEY  - free account + email request to transparency@entsoe.eu
Hugging Face needs no key.
"""
from __future__ import annotations

import argparse
import os
from datetime import date

import pandas as pd
from dotenv import load_dotenv

import config
from extract import eia, entsoe, hf, join


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Extract the data-centre demand panel.")
    p.add_argument("--sources", default="eia,entsoe,hf",
                   help="comma list of: eia, entsoe, hf")
    p.add_argument("--since", default="2019-01-01",
                   help="start date (YYYY-MM-DD) for the load backfill")
    p.add_argument("--until", default=date.today().isoformat(),
                   help="end date (YYYY-MM-DD), default today")
    p.add_argument("--out", default=str(config.PANEL_CSV), help="output CSV path")
    return p.parse_args(argv)


def _require(var: str) -> str:
    """Read an env var or exit with a readable message instead of a KeyError."""
    val = os.environ.get(var)
    if not val:
        raise SystemExit(f"missing {var} - add it to .env (see .env.example)")
    return val


def collect(sources: set[str], since: str, until: str) -> dict[str, pd.DataFrame]:
    """Run each requested fetcher and return {region_id: [timestamp, value, metric]}."""
    frames: dict[str, pd.DataFrame] = {}

    # --- EIA: US load, one call per region / sub-BA ----------------------
    if "eia" in sources:
        key = _require("EIA_API_KEY")
        for region_id, respondent, sub_ba, label, role in config.EIA_REGIONS:
            frames[region_id] = eia.fetch_eia_demand(
                respondent=respondent, start=since, end=until,
                api_key=key, sub_ba=sub_ba, demand_type=config.EIA_DEMAND_TYPE,
            )

    # --- ENTSO-E: EU load, one call per bidding zone (chunked internally) ---
    if "entsoe" in sources:
        token = _require("ENTSOE_API_KEY")
        for region_id, eic_domain, label, role in config.ENTSOE_ZONES:
            frames[region_id] = entsoe.fetch_entsoe_load(
                eic_domain=eic_domain, start=since, end=until, token=token,
            )

    # --- Hugging Face: one global proxy series (no key) -----------------
    if "hf" in sources:
        proxy = hf.fetch_hf_model_counts(since=since)
        # append the point-in-time downloads snapshot so history builds up over runs
        proxy = pd.concat([proxy, hf.snapshot_hf_downloads()], ignore_index=True)
        frames[config.HF_PROXY_REGION_ID] = proxy

    return frames


def main(argv=None) -> int:
    args = parse_args(argv)
    load_dotenv()
    sources = {s.strip() for s in args.sources.split(",") if s.strip()}
    unknown = sources - {"eia", "entsoe", "hf"}
    if unknown:
        raise SystemExit(f"unknown source(s): {', '.join(sorted(unknown))}")

    frames = collect(sources, args.since, args.until)
    frames = {rid: df for rid, df in frames.items() if df is not None and not df.empty}
    if not frames:
        raise SystemExit("no data fetched - nothing to write")

    panel = join.build_panel(frames)

    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    panel.to_csv(args.out, index=False)

    span = f"{panel['timestamp'].min()} -> {panel['timestamp'].max()}"
    print(f"\n{len(panel):,} rows | {panel['region_id'].nunique()} regions "
          f"| metrics: {', '.join(sorted(panel['metric'].unique()))}\n{span}\n-> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
