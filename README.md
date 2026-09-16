# ⚡ Data-Centre Energy Demand

> **Is the AI build-out actually bending the electricity demand curve?**
> A multi-source look at load growth in data-centre-heavy grid regions
> (Northern Virginia / PJM, Ireland, Germany) against a proxy for AI-compute
> growth — the demand-side sequel to [`GermanEnergyDashboard`](../GermanEnergyDashboard).

Status: **done end-to-end.** All three sources (EIA, ENTSO-E, Hugging Face)
are backfilled from 2019-01-01, the pre-2023 trend projection (Prophet,
`is_forecast=1` rows) is in, and the Power BI report (`datacentre-demand.pbip`)
is built — see [below](#the-dashboard) for what it shows.
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

## The Dashboard

`datacentre-demand.pbip` (open with Power BI Desktop — File → Open → the
`.pbip` file; it pulls from `data/demand_panel.xlsx`, a straight export of
the CSV, since Desktop imports Excel more reliably than a 48k-row CSV).
Dark amber "Grid Amber" theme, Rockwell for titles/KPI numbers, two pages.

A rendered PDF/PNG export lives alongside the `.pbip` for anyone without
Power BI Desktop — `datacentre-demand.png` / `.pdf`.

### Page 1 — Overview

**KPI strip (top).** Four cards, each a number *plus* its own comparison —
never a bare figure:

- **Data-Centre-Heavy Regions — Load Index.** The combined load level across
  the five DC-heavy regions (Northern Virginia, Ireland, Texas/ERCOT,
  Germany-Luxembourg, PJM), indexed so 2021 = 100, with the change vs. a year
  ago. On the most recent day all five regions had reported, this read
  **~145, up ~40% vs. a year earlier** — a sharp climb.
- **Control Regions — Load Index.** The same, for the two low-DC baseline
  regions (Southwest Power Pool, Portugal): **~132, up ~26%.** Growth is up
  here too, not flat — see the honest caveat below on what this does and
  doesn't prove.
- **Data-Centre Regions: Actual vs. Pre-AI Trend.** The headline number for
  the whole project: DC-heavy load today is running **~21% above** where a
  trend fit only on pre-2023 (pre-ChatGPT) data would have put it. This is
  the "bend" the project set out to find — actual load pulling away from its
  own historical trajectory, on the same timeline AI compute took off.
- **AI-Compute Proxy — Public Models on Hugging Face.** ~3.0 million public
  models hosted, still growing (~+1.6% in the latest month) — the open-model
  ecosystem is not slowing down. This is a *direction-of-travel* indicator
  only (frontier labs like OpenAI/Anthropic/Google aren't on Hugging Face),
  not a magnitude.

**Deduction:** both DC-heavy *and* control regions are growing YoY right now
— overall electricity demand is up broadly (this is a real macro trend:
electrification, post-2022 recovery, AI). What's distinctive to the DC-heavy
story isn't "control regions are flat and DC regions aren't" — it's the
**trend-gap card**: DC-heavy load is running further above its *own* pre-AI
trajectory than a simple YoY comparison alone would suggest.

**Hero chart — Load Index by Region.** All regions' indexed load over time,
solid line per region. Click a tile in "Region role" (top right) to isolate
DC-Heavy or Control and declutter — with all 8 lines on screen it's genuinely
hard to read at a glance, that's expected, use the filter.
**Deduction:** Ireland and Northern Virginia/PJM-DOM show the clearest
post-2022 upward bend of any region in the set; that lines up with Ireland
being the one place with an *official*, audited data-centre load share
(~21%, EirGrid/CRU) and Virginia being the densest known data-centre cluster
in the world ("Data Center Alley").

**Latest Year-over-Year Load Growth by Region (bar chart).** Every region's
own most recent monthly YoY reading, colour-coded green/red by sign.
**Deduction — and an honest complication, not a clean story:** this
cross-section does *not* neatly separate DC-heavy from control. Southwest
Power Pool (control) posted the **highest** YoY growth of any region
(~+26.5%), on par with Dominion/N. Virginia (~+26.0%). Meanwhile
Germany-Luxembourg — tagged DC-heavy for this project — is the **only
region with negative growth** (~-0.5%, shown in red). Plausible reason:
Germany's *total* grid load has been dragged down by a well-documented
post-2022 industrial slowdown (high energy prices pushed heavy industry to
cut output), which likely outweighs any Frankfurt data-centre growth at the
whole-country level — the dataset can't isolate Frankfurt specifically from
national German demand, so a real local DC signal could simply be swamped
here. This is exactly the kind of confound METHODOLOGY.md §5 warns about:
region-level load reflects *everything* happening on that grid, not data
centres in isolation. Don't over-read a single month's YoY number per region
— it's noisy; the trend-gap KPI (aggregated, trend-based) is the more
robust signal.

**AI-Compute Proxy chart.** Cumulative public models on Hugging Face,
monthly. **Deduction:** the curve visibly inflects upward around
late 2022/2023 — the same window ChatGPT launched and the "AI build-out"
narrative took off publicly. Correlated timing with the load-index bend
above; not proof of causation (METHODOLOGY.md §5).

**Filters.** Date-range slicer (top right) restricts every visual to a
window; Region-role slicer isolates DC-Heavy vs. Control on the two
region-comparison visuals (Hugging Face isn't a grid region, so it's
excluded from that filter and always shows).

**Glossary panel** (top right): plain-language definitions for DC, idx,
YoY, MoM, and what Hugging Face is, for anyone landing on this without
context.

### Page 2 — Source & Unit Detail

Load broken down by data source (EIA vs. ENTSO-E) and native unit
(`load_mw` vs. `load_mwh`). **Deduction / why this page exists:** EU regions
report in **MW**, US regions in **MWh/day** — genuinely different units at
genuinely different scales, which is *why* every other page uses the
indexed `load_index` instead of raw values. This page is the receipt for
that choice.

### A caveat worth stating plainly

The KPI strip's DC-Heavy/Control averages are computed on whichever day is
the most recent date **any** region reported — EIA (daily) and ENTSO-E
(also daily, but not always same-day) don't always land on the identical
calendar day, so on some days the "5-region" DC-Heavy average is really an
average of however many of the five happened to report that exact day.
Treat the KPI strip as directionally right and re-check the underlying
per-region numbers (bar chart, hero chart) before quoting a precise figure
from it.

## Layout

```
METHODOLOGY.md              the actual thinking — read this first
DASHBOARD_DESIGN.md         dashboard design spec: theme, fonts, visuals, DAX
config.py                   regions, EIC codes, baseline years, REGION_META (reference data)
extract/
  net.py                    shared HTTP GET with retry/backoff (not "http" — stdlib clash)
  eia.py                    US load fetcher (EIA Open Data v2, JSON, paged)
  entsoe.py                 EU load fetcher (ENTSO-E Transparency, XML, year-chunked)
  hf.py                     Hugging Face model-growth + downloads proxy
  join.py                   reshape to the tidy panel + load_index + yoy_growth +
                            isolated-outlier filtering (METHODOLOGY §5)
run_extract.py              CLI orchestration (fetch -> join.build_panel -> CSV)
run_forecast.py             analysis stage: Prophet trend fit per region on pre-2023
                            load_index, projected forward as is_forecast=1 rows
theme/grid-amber-theme.json importable Power BI theme (View → Themes → Browse)
datacentre-demand.pbip      Power BI project — data model + report (see "The Dashboard")
datacentre-demand.png/.pdf  static export of the report, for viewing without Desktop
```

## What's left

- [x] add `EIA_API_KEY` and `ENTSOE_API_KEY` to `.env`, run the first full backfill
- [x] sanity-check the `(verify)` codes in `config.py` against the live responses
- [x] analysis stage: fit each region's load trend on pre-2023 data, project it
      forward, and store the projection as `is_forecast=1` rows (METHODOLOGY §4)
- [x] `datacentre-demand.pbip` — KPI strip, actual-vs-projected trend gap,
      per-region load index, YoY growth by region, HF proxy growth
      (see [The Dashboard](#the-dashboard))
