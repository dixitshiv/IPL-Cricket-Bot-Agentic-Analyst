"""Static configuration constants for the cricket NL analytics tool.

No I/O here beyond reading environment variables; importing this module is cheap
and side-effect-free.
"""

import os

# --- Data / corpus -----------------------------------------------------------
DB_PATH = "data/cricket.duckdb"
JSON_DIR = "ipl_json"
SEASON = "2026"

# --- Models (OpenRouter slugs; overridable via env) --------------------------
MODEL = os.getenv("CRICKET_MODEL", "deepseek/deepseek-v4-pro")
ROUTE_MODEL = os.getenv("CRICKET_ROUTE_MODEL", MODEL)
EXPLAIN_MODEL = os.getenv("CRICKET_EXPLAIN_MODEL", MODEL)

# --- Render ------------------------------------------------------------------
VL_SCHEMA = "https://vega.github.io/schema/vega-lite/v5.json"

# --- Analytic thresholds -----------------------------------------------------
MIN_LEGAL_BALLS = 10   # below this, strike-rate/economy answers get a small-sample caveat
DEATH_OVER_START = 15  # 0-indexed; overs 16-20

# --- OpenRouter attribution headers ------------------------------------------
APP_URL = "https://github.com/local/cricket-nl"
APP_TITLE = "Cricket NL"
