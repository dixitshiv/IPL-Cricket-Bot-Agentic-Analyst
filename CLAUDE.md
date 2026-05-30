# CLAUDE.md

Guidance for Claude Code (claude.ai/code) when working in this repo.

## What this is

A natural-language + dashboard analytics tool over IPL ball-by-ball data (**all
seasons 2008–2026, ~1,239 matches**; the web app defaults to season 2026). Ask a
plain-English cricket question and an LLM analyst investigates with live SQL and
charts; or explore a dashboard of leaderboards, player profiles, scatter
quadrants, and head-to-head matchups.

The LLM writes its own SQL over rule-encoding DuckDB views, grounded by a
comprehensive cricket rulebook — it is an **agentic analyst**, not a set of canned
queries.

## The three entrypoints (all share data/cricket.duckdb)

- **`server.py` + `web/`** — PRIMARY. FastAPI backend + a bespoke vanilla-JS SPA
  ("Command Center" dashboard). Deterministic `/api/*` JSON endpoints query the
  views directly; `/api/ask` streams the agent over SSE. Run: `uv run python
  server.py` → http://localhost:8765.
- **`ask.py`** — the same agent in the terminal (CLI REPL). Run: `uv run python ask.py`.
- **`app.py`** — a Streamlit version of the dashboard. Run: `uv run streamlit run app.py`.

`ask.py` is the source of truth for the agent: `RULEBOOK` (the cricket rules in the
system prompt), `TOOLS` (`run_sql` + `make_chart`), `client()` (OpenAI SDK →
OpenRouter), and the `investigate()` loop. `server.py` imports `RULEBOOK` / `TOOLS`
/ `client` from it, so a rulebook change updates every surface at once.

## Commands

```bash
uv sync                                 # install deps (Python 3.13)
uv run python server.py                 # web app (dashboard + AI analyst)
uv run python ask.py                    # CLI analyst
uv run streamlit run app.py             # Streamlit dashboard
uv run pytest -q                        # tests
uv run python -m ingest.load            # (re)build data/cricket.duckdb from ipl_json/ (all seasons)
uv run python -m scripts.build_player_attributes   # (re)build the 2026 batting-hand / bowling-type enrichment
```

Needs `OPENROUTER_API_KEY` in `.env` for the AI analyst (dashboard panels work
without it). Override the model with `CRICKET_MODEL` (default `deepseek/deepseek-v4-pro`).

## Architecture

- **Data layer** (`ingest/`): `load.py` flattens Cricsheet JSON into four base
  tables; `views.sql` builds the rule-encoding views `v_deliveries` / `v_innings`
  / `v_matches`. **All queries hit the views, never the base tables** — the views
  encode the domain rules once so everything inherits them. `core/config.py` +
  `core/db.py` hold the shared DB path and the read-only/read-write connection
  factory used by the build and the apps.
- **Agent** (`ask.py`): an LLM with a `run_sql` tool loops to investigate; the
  `RULEBOOK` carries the cricket conventions that keep it correct.
- **Dashboard** (`server.py`): deterministic view-query JSON, cached via
  `@lru_cache` (the DB is read-only); the SPA renders custom SVG/CSS charts.
  `/api/health` reports DB reachability, season coverage, and whether the API key
  is set (the frontend shows an "AI offline" notice when it isn't).

## Critical invariants (encoded once in `ingest/views.sql` — don't re-derive ad hoc)

- `is_legal_ball = (wides=0 AND noballs=0)`; byes/legbyes/penalty are legal balls.
- `bowler_conceded = runs_batter + wides + noballs` (byes/legbyes/penalty excluded).
- Overs are 0-indexed; death overs = `over >= 15`. Phase comes from each innings'
  explicit `powerplays` array.
- Super-over rows are excluded from the views; `effective_winner = COALESCE(winner, eliminator)`.
- `v_deliveries` **inner-joins `matches`** to expose `season` and COALESCEs
  canonical names, so every season has readable batter/bowler names. (A delivery
  with no matching `matches` row is dropped — see `tests/test_views.py`.)
- `season` is **TEXT** (e.g. `'2026'`, `'2009/10'`) — always quote it: `season =
  '2026'`, never the bare integer `season = 2026` (that throws a conversion error).
- Count boundaries by `runs_batter` alone (a four/six off a no-ball still counts) —
  do NOT add an `is_legal_ball` filter; that keeps the agent consistent with the dashboard.
- Bowler wicket attribution: only `wicket_kind IN ('bowled','caught','lbw','caught
  and bowled','stumped','hit wicket')` credits the bowler. Run-outs etc. do not.
- Resolve player names with `ILIKE` against the view's `batter_name` / `bowler_name`
  (full canonical names); surface ties/ambiguity rather than guessing.

## Safety

- Every DB connection the apps use is `read_only=True`; the agent's `run_sql` runs
  against a read-only connection — that is the real safety guarantee, not a string check.
- `.env` (the API key) is gitignored, and `.dockerignore` keeps it out of the image.

## Tests

`tests/test_server.py` + `tests/test_agent.py` cover the web backend and the agent
plumbing (the latter mocks the model — no network/key). `tests/test_views.py`,
`tests/test_db.py`, `tests/test_config.py` cover the shared data layer. `uv run
pytest -q` should be all green. (Rebuild-from-raw tests aren't shipped — they need
the `ipl_json/` corpus, which isn't included.)
