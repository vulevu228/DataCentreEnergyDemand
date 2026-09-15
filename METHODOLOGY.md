# Methodology & caveats

> **The question.** Is electricity demand in data-centre-heavy regions actually
> bending upward, and does that bend line up in time with the explosion in AI
> compute? This project tries to *show* that with public data instead of just
> citing headlines — while being honest that no single dataset answers it.

The German grid dashboard (`GermanEnergyDashboard`) looked at the **supply**
side of the energy transition — how the generation mix is changing. This is the
sequel on the **demand** side: the argument that demand growth, led by data
centres, is becoming the binding constraint on the grid.

---

## 1. Why this is a mash-up and not one feed

There is **no public API anywhere that reports "data-centre electricity
demand"** as a line item. Utilities know it (it's in their interconnection
queues and rate cases), but it is not published as a clean time series. So the
approach is to triangulate from three imperfect angles:

| Angle | Source | What it actually measures | What it does **not** measure |
|---|---|---|---|
| Regional load | **EIA Open Data API v2** (US) | Total hourly electricity demand for a balancing authority / sub-region | Data-centre load specifically — DC is a *share* of this, mixed with everything else |
| Regional load | **ENTSO-E Transparency Platform** (EU) | Actual total load per bidding zone / control area, hourly | Same — total load, not DC load |
| AI-compute proxy | **Hugging Face Hub API** (no key) | Count of public models over time, download/like volume | Training + inference energy, or closed-model compute (OpenAI, Anthropic, Google) — HF is only the open slice |

The analysis is the join: **does load growth in regions we independently know
to be data-centre-dense outpace load growth elsewhere, on the same timeline as
the AI-compute proxy turning up?** That is suggestive, not causal — see §5.

---

## 2. Regions and why each one is in

Region selection is the whole ballgame: we need places where data centres are a
*large, known* share of load, plus controls where they are not.

### United States (EIA)
| Region | EIA code | Why |
|---|---|---|
| PJM Interconnection | `PJM` | Largest US grid operator; contains Northern Virginia |
| Dominion (Virginia) sub-region | parent `PJM`, sub-BA `DOM` | **"Data Center Alley"** — Loudoun County, VA is the densest data-centre cluster on earth. DC is a double-digit and fast-rising share of DOM load |
| ERCOT (Texas) | `ERCO` | Fast-growing DC + crypto load, useful second case |
| A low-DC control | e.g. `SWPP` / `SOCO` | Baseline: what "normal" load growth looks like without a DC boom |

> Caveat: even `DOM` is not DC-only. It is the *best available* proxy because the
> DC share there is unusually high and well documented in Dominion Energy's own
> load forecasts.

### Europe (ENTSO-E)
| Region | EIC domain | Why |
|---|---|---|
| Ireland (SEM) | `10Y1001A1001A59C` | **The cleanest case in the world.** EirGrid / CRU officially report data centres at ~21% of all metered electricity (2023), projected ~28–30% by 2030. Ireland has paused new grid connections in the Dublin region because of it |
| Germany–Luxembourg | `10Y1001A1001A82H` | Ties back to the prequel dashboard; Frankfurt is a major DC hub, though DC is a smaller national share than in Ireland |
| A control zone | e.g. Portugal `10YPT-REN------W` | Low DC density baseline |

> Ireland is the anchor: it is the one place where an official body publishes the
> DC share, so we can calibrate "how much of this load bump is data centres"
> against a real number instead of guessing.

### AI-compute proxy (Hugging Face)
Not a region — a global time series. Candidate metrics, in rough order of
signal quality:
1. **Cumulative public models by month** (`createdAt` bucketed) — cleanest, monotonic, clearly inflecting from ~2023.
2. **New models per month** — the growth *rate*.
3. **Download volume on top-N models** — noisier, API only gives a rolling figure, not history, so this has to be logged forward over time by the collector.

> Caveat: HF is the open-model ecosystem only. The biggest compute consumers
> (frontier labs) are invisible here. Treat this as a **direction-of-travel**
> indicator — "the field is scaling fast" — not a magnitude.

---

## 3. What one row of the output means

Target: a single tidy panel that all three sources feed, so Power BI can slice it.

```
region_id      e.g. "US-PJM-DOM", "EU-IE-SEM", "PROXY-HF"
region_label   human name
metric         "load_mwh" | "load_index" | "yoy_growth_pct"
               | "hf_models_cumulative" | "hf_models_new"
timestamp      UTC, hourly for load, monthly for the proxy
value          float
source         "eia" | "entsoe" | "huggingface"
is_forecast    0 = actual, 1 = projected-from-pre-2023-trend (see §4)
retrieved_at   UTC timestamp of the API call
```

Design notes to settle before coding (this is a good place for you to decide):
- **Resampling.** Keep raw hourly load, or resample to daily/monthly means in the
  extractor? Recommendation: store daily means — hourly is 24× the volume for
  little analytical gain at this timescale, and keeps the CSV git-friendly.
- **Indexing.** `load_index` = load ÷ (mean load in a chosen baseline year, e.g.
  2019 or 2021) × 100. Makes regions of very different absolute size comparable
  on one chart. Decide the baseline year and whether it's per-region.
- **Weather.** Raw load is heavily weather-driven (heating/cooling). A proper
  comparison would weather-normalise (regress load on heating/cooling degree
  days, compare residual trends). v1 can skip this but **must say so** — see §5.

---

## 4. The "forecast vs actual" angle

Reuses the idea from the gold/oil forecaster (`tracking_metals/forecasting_gold`):

1. Fit a trend model (naive linear, plus Prophet for seasonality) on each
   region's load using **only data up to the end of 2022** — before ChatGPT.
2. Project that trend forward to the present.
3. Plot projected vs actual. The **gap** is the visual headline: in DC-heavy
   regions the actual line should peel away above the pre-AI trend; in the
   control regions it should stay on trend.

This is deliberately simple. It is not a real counterfactual (many things
changed after 2022), but it makes the "bend" legible on one chart.

---

## 5. Honest caveats

- **Attribution.** We cannot prove data centres *caused* any load bump. Load also
  moves with weather, electrification (EVs, heat pumps), reshoring/industry,
  crypto, and post-COVID economic recovery. The claim is *consistency* — the
  timing and geography line up — not causation.
- **Only Ireland is calibrated.** Everywhere else, "DC share of load" is
  inferred. Numbers for the US rely on utility filings quoted in the README's
  external anchors, not on anything in these feeds.
- **The proxy is qualitative.** HF model growth shows the field scaling; it is
  not proportional to energy use.
- **No weather normalisation in v1.** Cross-region and pre/post comparisons are
  affected by weather-year differences. Flagged, not fixed.
- **Isolated bad EIA readings are dropped, not imputed.** Confirmed live
  2026-09-15: PJM and PJM-DOM both carried a single day (2021-10-19) at
  2,000-8,000x their normal load, and SWPP one day (2023-06-13) at ~4x its
  next-highest - one bad upstream read each, not real demand events (those
  ramp over days, not spike on one isolated day). `join.py` drops any daily
  value more than 5x the centred 7-day rolling median before it can distort
  `load_index`'s baseline-year mean or the forecast fit. A handful of days
  are simply absent from the panel for these three regions as a result.
- **Time zones.** EIA returns local-time-with-offset; ENTSO-E returns UTC in
  a `GL_MarketDocument`. Everything is converted to UTC on ingest. DST folds
  are handled by using tz-aware parsing, not naive strings.
- **Rate limits / history depth.** EIA v2 caps rows per call (paginate with
  `offset`). ENTSO-E limits each query to a max interval (≈1 year) and ~400
  requests/min. HF paginates; download counts are point-in-time only.
- **External anchor figures** (IEA global DC TWh, Dominion load-forecast
  revisions, interconnection-queue backlog) are cited for context in the README
  and used only as chart annotations — they are not part of the dataset.

---

## 6. Data lineage

| Source | Endpoint (base) | Auth | Pull | Cadence | Attribution / licence |
|---|---|---|---|---|---|
| EIA Open Data v2 | `https://api.eia.gov/v2/electricity/rto/` | free instant key (`EIA_API_KEY`) | hourly demand + day-ahead forecast per region / sub-BA | daily backfill | U.S. EIA, public domain |
| ENTSO-E Transparency | `https://web-api.tp.entsoe.eu/api` | free token (`ENTSOE_API_KEY`, request via account) | A65 total load, actual (A16) per zone | daily backfill | ENTSO-E, free re-use with attribution |
| Hugging Face Hub | `https://huggingface.co/api/models` | none | model list w/ `createdAt`, `downloads`, `likes` | daily snapshot appended | per HF terms; data is public metadata |

---

## 7. Open decisions (for you to make before we implement)

1. Daily means, or keep hourly? *(rec: daily)*
2. Baseline year for `load_index`? *(rec: 2021 — post-COVID-normal, pre-AI)*
3. Which US control region — `SWPP`, `SOCO`, national?
4. HF proxy: cumulative model count only, or also start logging download volume forward?
5. Store outputs as one wide CSV, one long/tidy CSV, or Parquet like the German dashboard? *(rec: one long/tidy CSV — matches the row schema in §3, easy Power BI)*
6. Forecast split year — end of 2022, or mid-2022?
