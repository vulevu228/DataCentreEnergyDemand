# ⚡ Data-Centre Energy Demand

> **Is the AI build-out actually bending the electricity demand curve?**
> A multi-source look at load growth in data-centre-heavy grid regions
> (Northern Virginia / PJM, Ireland, Germany) against a proxy for AI-compute
> growth — the demand-side sequel to [`GermanEnergyDashboard`](../GermanEnergyDashboard).

Status: **extraction implemented, not yet run at full scale.** All three
fetchers and the join/panel builder are written; a first real backfill needs
the two API keys below. The analysis stage (pre-2023 trend projection) and the
Power BI report are still to come.
See **[`METHODOLOGY.md`](METHODOLOGY.md)** for what this measures, which regions
and why, the output schema, and the (many) caveats.

---

## The story

Global data-centre electricity use was roughly **415–460 TWh in 2024** and is
projected toward **~945 TWh by 2030** (IEA, *Electricity 2024* / *Energy & AI*
2025). AI-specific load is growing on the order of **~50 % a year**. Utilities
are revising load forecasts upward for the first time in decades, and
interconnection queues are backed up for years.

This repo does not try to re-derive those global numbers. It tries to *see the
fingerprint* in public grid data: if data centres are the cause, then load in
the regions where they cluster should be pulling away from its pre-2023 trend
faster than load everywhere else — on the same timeline as AI compute scaling up.

## External anchors (context only — not in the dataset)

- **IEA** — global DC demand ~415–460 TWh (2024) → ~945 TWh (2030); AI the main driver.
- **EirGrid / CRU (Ireland)** — data centres ~21 % of all metered electricity (2023), heading for ~28–30 % by 2030; new Dublin-area grid connections paused.
- **Dominion Energy (Virginia)** — successive upward revisions to its long-term load forecast, attributed largely to data centres.
- **PJM** — 2024/2025 load-forecast revisions and a multi-year interconnection queue backlog.

*(Figures are as cited in public reporting up to early 2026; treat as
approximate and check the primary source before quoting.)*

---

## Data sources

| Source | Key? | Role |
|---|---|---|
| [EIA Open Data API v2](https://www.eia.gov/opendata/) | free, instant | US hourly demand per balancing authority / sub-region |
| [ENTSO-E Transparency Platform](https://transparency.entsoe.eu) | free, request | EU total load per bidding zone |
| [Hugging Face Hub API](https://huggingface.co/docs/hub/api) | none | public-model growth as an AI-compute proxy |

## Setup

```bash
python -m venv .venv && .venv\Scripts\activate      # Windows
pip install -r requirements.txt
copy .env.example .env                                # then fill in the keys
```

- `EIA_API_KEY` — instant from https://www.eia.gov/opendata/register.php
- `ENTSOE_API_KEY` — create a free account, then email transparency@entsoe.eu
  asking for API access (they enable a "Web API Security Token" on your account)
- Hugging Face needs no key.

## Run

```bash
python run_extract.py --sources eia,entsoe,hf --since 2019-01-01
python run_extract.py --sources hf            # proxy-only top-up, no keys needed
```

Output: one tidy CSV (`data/demand_panel.csv`) — schema in `METHODOLOGY.md` §3.
`--sources hf` works with no keys and is the quickest way to see the pipeline
end to end.

## Layout

```
METHODOLOGY.md      the actual thinking — read this first
config.py           regions, EIC codes, baseline years, REGION_META (reference data)
extract/
  net.py            shared HTTP GET with retry/backoff (not "http" — stdlib clash)
  eia.py            US load fetcher (EIA Open Data v2, JSON, paged)
  entsoe.py         EU load fetcher (ENTSO-E Transparency, XML, year-chunked)
  hf.py             Hugging Face model-growth + downloads proxy
  join.py           reshape to the tidy panel + load_index + yoy_growth
run_extract.py      CLI orchestration (fetch -> join.build_panel -> CSV)
```

## What's left

- [ ] add `EIA_API_KEY` and `ENTSOE_API_KEY` to `.env`, run the first full backfill
- [ ] sanity-check the `(verify)` codes in `config.py` against the live responses
- [ ] analysis stage: fit each region's load trend on pre-2023 data, project it
      forward, and store the projection as `is_forecast=1` rows (METHODOLOGY §4)
- [ ] `datacentre-demand.pbix` — actual vs projected per region, `load_index`
      small multiples, HF proxy on a second axis
