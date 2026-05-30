# Cricket Bot

Natural-language + dashboard analytics over **all 19 IPL seasons (2008–2026)** of
Cricsheet ball-by-ball data (~1,239 matches). Ask a plain-English question and an
LLM analyst investigates with live SQL and charts; or explore a bespoke dashboard
of leaderboards, player profiles, scatter quadrants, and head-to-head matchups.

The LLM writes its own SQL over rule-encoding DuckDB views, grounded by a
comprehensive cricket rulebook — every number is computed deterministically and
every query the agent runs is shown.

## Quick start

```bash
uv sync                          # install deps (Python 3.13)

uv run python server.py          # web app — dashboard + AI analyst → http://localhost:8765
uv run python ask.py             # CLI analyst (terminal)
uv run streamlit run app.py      # Streamlit dashboard

uv run pytest -q                 # tests
```

The database (`data/cricket.duckdb`) is **included prebuilt**, so it runs
immediately. The AI analyst needs `OPENROUTER_API_KEY` in `.env` (the dashboard
panels work without it). Override the model with `CRICKET_MODEL` (default
`deepseek/deepseek-v4-pro`).

## The three apps

| Entry | What it is |
|-------|------------|
| **`server.py` + `web/`** | Primary: FastAPI backend + bespoke vanilla-JS SPA ("Command Center" dashboard). Multi-season filters, player drilldowns, scatter quadrants, matchups, and a streaming AI-analyst console with thread memory. |
| **`ask.py`** | CLI agentic analyst — the same agent, in the terminal. |
| **`app.py`** | Streamlit dashboard. |

## How it works

- **Data** (`ingest/`): `load.py` flattens Cricsheet JSON into four base tables;
  `views.sql` builds the rule-encoding views (`v_deliveries` / `v_innings` /
  `v_matches`) that encode the domain rules once — legal balls, `bowler_conceded`,
  phases, super-over exclusion, `effective_winner`, season, and player names.
  `core/config.py` + `core/db.py` hold the shared DB path and connection factory.
- **Agent** (`ask.py`): an LLM with a `run_sql` tool loops to investigate, armed
  with a `RULEBOOK` of cricket conventions. It writes all its own SQL; it is not a
  fixed set of canned queries. `server.py` reuses its `RULEBOOK`/`TOOLS`/`client`.
- **Dashboard** (`server.py`): deterministic JSON endpoints query the views
  directly; the SPA renders custom SVG/CSS charts. Filters (season, team, opponent,
  venue, innings, phase, vs pace/spin, batter hand, qualifier) cross-apply to every
  panel and can optionally scope the AI analyst. `/api/health` reports DB + key status.

## Deploy (Docker)

```bash
docker build -t cricket-bot .
docker run -p 8765:8765 cricket-bot     # dashboard works without a key
# add the analyst: docker run -p 8765:8765 -e OPENROUTER_API_KEY=sk-or-... cricket-bot
```

The image bakes in the prebuilt DB; `.env` is excluded so no secret is baked in.

## Rebuilding the database

The prebuilt DB is included. To rebuild from raw data you need the Cricsheet
`ipl_json/` corpus (not shipped — download from [cricsheet.org](https://cricsheet.org)),
then:

```bash
uv run python -m ingest.load                      # all seasons → data/cricket.duckdb
uv run python -m scripts.build_player_attributes  # 2026 batting-hand / bowling-type enrichment
```
