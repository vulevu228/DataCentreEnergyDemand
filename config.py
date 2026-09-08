"""
Reference data for the extraction: which regions, their API identifiers,
baseline years, and source endpoints.

This file is deliberately just constants - the fetch logic lives in extract/.
Codes marked (verify) should be checked against the live API docs before first
use; they are from memory and the platforms do rename things.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
PANEL_CSV = DATA_DIR / "demand_panel.csv"

# --- analysis knobs (see METHODOLOGY.md §7 - you decide these) -----------------
BASELINE_YEAR = 2021          # load_index = load / mean(load in BASELINE_YEAR) * 100
FORECAST_SPLIT = "2022-12-31"  # fit the pre-AI trend on data up to here
RESAMPLE = "D"                # "D" daily means, or "H" to keep hourly

# --- EIA (US) ----------------------------------------------------------------
EIA_BASE = "https://api.eia.gov/v2"
# region-level demand: /electricity/rto/region-data/data
# sub-BA level:        /electricity/rto/region-sub-ba-data/data
EIA_REGIONS = [
    # region_id,        respondent, sub_ba, label,                    role
    ("US-PJM",          "PJM",      None,   "PJM Interconnection",     "dc_heavy"),
    ("US-PJM-DOM",      "PJM",      "DOM",  "Dominion / N. Virginia",  "dc_core"),
    ("US-ERCO",         "ERCO",     None,   "ERCOT (Texas)",           "dc_growing"),
    ("US-SWPP",         "SWPP",     None,   "Southwest Power Pool",    "control"),  # (verify choice)
]
EIA_DEMAND_TYPE = "D"        # D=demand, DF=day-ahead forecast, NG=net generation, TI=interchange

# --- ENTSO-E (EU) ----------------------------------------------------------
ENTSOE_BASE = "https://web-api.tp.entsoe.eu/api"
ENTSOE_LOAD_DOCTYPE = "A65"  # System total load
ENTSOE_PROCESS_ACTUAL = "A16"  # realised
ENTSOE_ZONES = [
    # region_id,     eic_domain,             label,                 role
    ("EU-IE-SEM",   "10Y1001A1001A59C",     "Ireland (SEM)",        "dc_core"),      # (verify)
    ("EU-DE-LU",    "10Y1001A1001A82H",     "Germany-Luxembourg",   "dc_heavy"),     # (verify)
    ("EU-PT",       "10YPT-REN------W",     "Portugal",             "control"),      # (verify)
]
# ENTSO-E rejects intervals longer than ~1 year per call - chunk requests.
ENTSOE_MAX_DAYS = 365

# Calibration anchor: the one region with an official DC-share number.
# EirGrid / CRU: data centres ~21% of metered electricity in 2023.
IE_DC_SHARE_2023 = 0.21

# --- Hugging Face (AI-compute proxy) --------------------------------------
HF_BASE = "https://huggingface.co/api"
HF_PROXY_REGION_ID = "PROXY-HF"
# metric ideas: models_cumulative (by createdAt month), models_new_monthly,
# downloads_topN (must be logged forward - API gives point-in-time only)

# --- HTTP behaviour ------------------------------------------------------
HTTP_TIMEOUT = 90
HTTP_RETRIES = 5
HTTP_BACKOFF = 2.0           # seconds, exponential: BACKOFF * 2**attempt

# --- output panel schema (METHODOLOGY.md §3) ---------------------------------
PANEL_COLUMNS = [
    "region_id", "region_label", "metric", "timestamp",
    "value", "source", "is_forecast", "retrieved_at",
]

# region_id -> (human label, source tag). Assembled from the lists above so
# join.build_panel() can label a fetcher's output without extra plumbing.
REGION_META: dict[str, tuple[str, str]] = {}
REGION_META.update({rid: (label, "eia") for rid, _resp, _sub, label, _role in EIA_REGIONS})
REGION_META.update({rid: (label, "entsoe") for rid, _eic, label, _role in ENTSOE_ZONES})
REGION_META[HF_PROXY_REGION_ID] = ("Hugging Face model growth", "huggingface")

# metrics that represent a raw electricity-load time series (as opposed to the
# HF proxy or a derived index) - used by join.py to decide what to resample and
# what to build indices / growth rates from.
LOAD_METRICS = ("load_mwh", "load_mw")
