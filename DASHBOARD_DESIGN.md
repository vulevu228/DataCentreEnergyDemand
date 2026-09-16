# Dashboard design — `datacentre-demand.pbix`

Design pass done ahead of the data import so we can go straight to DAX once
the CSV is in Power BI. Applies the two standing principles from
Lukas Reese's feedback (see `feedback_powerbi_dashboard_design` memory):
a compact top KPI strip instead of a KPI row, secondary detail pushed behind
a bookmark instead of a taller page, and every KPI paired with a comparison
instead of a raw point-in-time value.

---

## 1. Theme — "Grid Amber"

Moves off the navy dark theme used on DWD / GermanWaterLevels. Concept: an
energy-control-room panel — warm dark base, amber/gold as the "live signal"
color, cool desaturated slate for baseline/control regions, so color itself
carries meaning instead of just decorating.

Importable theme file: **`theme/grid-amber-theme.json`**
(Power BI Desktop → **View → Themes → Browse for themes...**)

| Role | Hex | Used for |
|---|---|---|
| Canvas background | `#1C1410` | Page background (warm near-black, not navy) |
| Outspace | `#140D0A` | Area outside the page |
| Card / panel fill | `#241A14` | Card, multi-row card, slicer backgrounds |
| Primary signal (amber) | `#F5A623` | DC-heavy regions, headline KPI numbers, callouts |
| Growth gold | `#FFC94D` | Positive deltas, "good" |
| Burnt orange | `#E8590C` | Forecast/projected series accent |
| Copper | `#C97C3D` | Secondary DC-heavy region |
| Muted slate (cool) | `#5C7A80` / `#3E5C61` | Control/baseline regions — deliberately cool and desaturated so they visually recede against the warm DC regions |
| Warm gray | `#8C7B6B` | Neutral, "center" of diverging scales |
| Rust (bad) | `#C0453A` | Negative deltas only, kept desaturated — not neon red |
| Text primary | `#F5EFE6` | Titles, values |
| Text secondary | `#B8A992` | Axis labels, captions |
| Gridlines | `#3A2E24` | Low-contrast gridlines |

**Color-codes-meaning rule:** warm (amber/gold/copper/orange) = data-centre-dense
regions (`US-PJM-DOM`, `EU-IE-SEM`, `US-ERCO`, `EU-DE-LU`); cool slate = control
regions (`US-SWPP`, `EU-PT`); the HF proxy series gets its own bright gold
(`#FFC94D`) since it's the AI-compute signal, not a grid region.
Actual = solid line, forecast/projected = dashed line, same color — never a
separate hue for forecast, so the eye tracks "same region, different mode."

## 2. Fonts

Decided: **nostalgic** direction (Rockwell), per your pick.

| Text class | Font | Notes |
|---|---|---|
| Titles / page header | Rockwell, Bold, tracked caps | WPA-era power-plant-poster feel |
| KPI callout numbers | Rockwell, Bold | Large, amber `#F5A623` |
| Body / axis / legend | Segoe UI | Keeps small text crisp — Rockwell only for display sizes |
| Slicer header | Rockwell SemiBold | Small, amber |

Both are Windows built-ins — no font install needed on either machine.

## 3. Data model additions (small, needed before DAX)

The CSV is long/tidy (`region_id, region_label, metric, timestamp, value,
source, is_forecast, retrieved_at`). Two small additions make the DAX below
work cleanly — neither is scope creep, both are required for time
intelligence and the warm/cool color rule:

1. **Date table**, marked as the official date table, related to
   `demand_panel[timestamp]`. Needed for `SAMEPERIODLASTYEAR` /
   year-over-year comparisons.
2. **RegionMeta table** (5 columns, entered manually — 8 rows, one per
   `region_id`): `region_id, region_label, role (DC-Heavy / Control /
   Proxy), sort_order`. Relates 1:many to `demand_panel[region_id]`. Drives
   the warm/cool color split and the region-role slicer (visual #9 below).

## 4. Layout — one main page + one bookmarked detail panel

1920×1080, `FitToPage`. Per Lukas Reese: KPI strip stays compact at the top,
the hero chart gets real room, and the source/unit breakdown is pushed
behind a button instead of adding a fourth row.

```
┌─────────────────────────────────────────────────────────────────┐
│ DATA-CENTRE ENERGY DEMAND            [date slicer]  [role slicer]│ ← header, not counted in the 10
├───────┬───────┬───────┬───────┬──────────────────────────────────┤
│ KPI 1 │ KPI 2 │ KPI 3 │ KPI 4 │  (compact strip, ~120px tall)     │
├───────┴───────┴───────┴────────────────────────────[detail btn]─┤
│                                                                   │
│   Hero: Actual vs Projected Load Index — small multiples by      │
│   region (solid = actual, dashed = forecast)                     │
│                                                                   │
├───────────────────────────────┬─────────────────────────────────┤
│  HF model growth (AI-compute   │  Latest YoY growth % by region   │
│  proxy, 2023 inflection)       │  (warm DC vs cool control bars)  │
└───────────────────────────────┴─────────────────────────────────┘
```

## 5. The 10 visuals

| # | Visual | Type | Fields | Comparative framing |
|---|---|---|---|---|
| 1 | DC-Heavy Load Index | Card | `[Load Index (Actual)]` filtered `role="DC-Heavy"` | subtitle: YoY Δ |
| 2 | Control Load Index | Card | same, filtered `role="Control"` | subtitle: YoY Δ |
| 3 | Trend Gap | Card | `[Trend Gap %]` | *the headline number* — how far actual sits above the pre-2023 projected trend |
| 4 | AI-Compute Proxy | Card | `[HF Cumulative Models]` | subtitle: MoM growth % |
| 5 | Actual vs Projected Load Index | Line chart, small multiples by `region_label` | `timestamp`, `[Load Index (Actual)]`, `[Load Index (Forecast)]` | solid vs dashed = the whole story on one visual |
| 6 | AI-Compute Growth | Line chart | `timestamp`, `[HF Cumulative Models]`, `[HF New Models]` (secondary axis) | annotated 2023 inflection line |
| 7 | Latest YoY Growth by Region | Clustered bar, sorted desc | `region_label`, `[YoY Growth %]`, colored by `RegionMeta[role]` | region vs region at a glance |
| 8 | Date range | Slicer (between) | `Date[Date]` | — |
| 9 | Region role toggle | Slicer (buttons) | `RegionMeta[role]` | lets you isolate DC-heavy vs control instantly |
| 10 | "Show source breakdown" | Button → bookmark | reveals a hidden table/stacked-bar of `source` × `metric` unit (`load_mw` vs `load_mwh`) | keeps the detail off the main page per Lukas Reese |

## 6. DAX measures to start with

Table names assumed `demand_panel` / `Date` / `RegionMeta` — adjust to match
whatever Power Query names them on import.

```dax
Load Index (Actual) =
CALCULATE(
    SUM(demand_panel[value]),
    demand_panel[metric] = "load_index",
    demand_panel[is_forecast] = 0
)

Load Index (Forecast) =
CALCULATE(
    SUM(demand_panel[value]),
    demand_panel[metric] = "load_index",
    demand_panel[is_forecast] = 1
)

Trend Gap % =
DIVIDE(
    [Load Index (Actual)] - [Load Index (Forecast)],
    [Load Index (Forecast)]
)

Load Index YoY Δ =
[Load Index (Actual)] -
CALCULATE([Load Index (Actual)], SAMEPERIODLASTYEAR('Date'[Date]))

YoY Growth % =
CALCULATE(
    SUM(demand_panel[value]),
    demand_panel[metric] = "yoy_growth_pct",
    demand_panel[is_forecast] = 0
)

HF Cumulative Models =
CALCULATE(SUM(demand_panel[value]), demand_panel[metric] = "hf_models_cumulative")

HF New Models =
CALCULATE(SUM(demand_panel[value]), demand_panel[metric] = "hf_models_new")

HF MoM Growth % =
VAR CurrentVal = [HF Cumulative Models]
VAR PriorVal =
    CALCULATE([HF Cumulative Models], DATEADD('Date'[Date], -1, MONTH))
RETURN
    DIVIDE(CurrentVal - PriorVal, PriorVal)
```

`[Load Index (Actual)]` / `[Load Index (Forecast)]` filtered by
`RegionMeta[role]` (via slicer or explicit `CALCULATE(..., RegionMeta[role]
= "DC-Heavy")`) drive KPI cards #1–#2.

## 7. Open item for our DAX session

`Trend Gap %` currently compares the *global* actual vs forecast sum, which
mixes DC-heavy and control regions. Once the CSV is in, we should decide
whether the headline gap card is DC-heavy-only (cleaner "bend" story) or
all-regions (more honest baseline-included number) — flag this when we sit
down to build it.
