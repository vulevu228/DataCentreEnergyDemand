"""
CLI entry point. Wires the fetchers in extract/ to the region config and
writes data/demand_panel.csv.

    python run_extract.py --sources eia,entsoe,hf --since 2019-01-01
    python run_extract.py --sources hf            # just the daily proxy top-up

STUB - argument parsing is real so the shape is visible; the orchestration
body is not implemented.
"""

from __future__ import annotations

import argparse
import os
from datetime import date

from dotenv import load_dotenv

import config


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Extract the data-centre demand panel.")
    p.add_argument(
        "--sources",
        default="eia,entsoe,hf",
        help="comma list of: eia, entsoe, hf",
    )
    p.add_argument(
        "--since",
        default="2019-01-01",
        help="start date (YYYY-MM-DD) for the load backfill",
    )
    p.add_argument(
        "--until",
        default=date.today().isoformat(),
        help="end date (YYYY-MM-DD), default today",
    )
    p.add_argument(
        "--out",
        default=str(config.PANEL_CSV),
        help="output CSV path",
    )
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    load_dotenv()
    sources = {s.strip() for s in args.sources.split(",") if s.strip()}

    # TODO(you): the orchestration -
    #   if "eia" in sources:
    #       key = os.environ["EIA_API_KEY"]
    #       for region_id, respondent, sub_ba, label, role in config.EIA_REGIONS:
    #           df = eia.fetch_eia_demand(respondent, args.since, args.until, key, sub_ba=sub_ba)
    #           frames[region_id] = df
    #   ...same for entsoe (ENTSOE_API_KEY) and hf (no key)...
    #   panel = join.build_panel(frames)
    #   merge with any existing CSV at args.out (dedupe on
    #       [region_id, metric, timestamp]), write.
    raise NotImplementedError


if __name__ == "__main__":
    raise SystemExit(main())
