# Cricket Bot

An agentic cricket analyst over **all 19 IPL seasons (2008–2026)** of Cricsheet ball-by-ball data (~1,239 matches). Ask a plain-English question — *"who's the best death-overs bowler this season?"*, *"analyze RCB's powerplay batting"* — and an LLM investigates: it writes its own SQL, looks at the results, runs follow-ups, draws a chart when it helps, and writes a real analytical answer. Or skip the chat and explore a bespoke "Command Center" dashboard of leaderboards, player profiles, scatter quadrants, and head-to-head matchups. Every number is computed deterministically from the data, and every query the agent runs is shown.

**Built with:** Python 3.13 · FastAPI · DuckDB · OpenAI SDK (→ OpenRouter) · DeepSeek · Vanilla-JS SPA · Streamlit · Matplotlib · Docker

---

## Demo

<!-- Add screenshots/video link here -->

---

## Screenshots

<!-- Add dashboard + AI-analyst console screenshots here -->

---

## Features & Architecture

- **Agentic Analyst, Not Canned Queries:** The LLM writes all of its own SQL in a `run_sql` → observe → follow-up loop (up to 10 steps). It decides how many queries a question needs — a one-line fact takes one; an open topic ("what's interesting about X") fans out into several angles plus a chart and a short structured report.
- **Rule-Encoding DuckDB Views:** The hard cricket rules are baked once into `v_deliveries` / `v_innings` / `v_matches` — legal balls, `bowler_conceded`, innings phases, super-over exclusion, `effective_winner`, canonical player names. Every query (agent *and* dashboard) hits the views, so both surfaces inherit the same correct domain logic and never disagree.
- **Grounded by a Cricket Rulebook:** A comprehensive `RULEBOOK` in the system prompt carries the conventions a real analyst needs — metric formulas, bowler wicket attribution, 0-indexed overs, small-sample and tie caveats, season-is-TEXT quoting — given as reference, not a cage. It's what keeps free-form SQL correct.
- **Streaming AI Console (SSE):** `/api/ask` streams the agent's tool calls, queries, and final answer live over Server-Sent Events into the dashboard console, with per-session thread memory so follow-ups keep context.
- **Cross-Filtering Command Center:** A bespoke vanilla-JS SPA renders custom SVG/CSS charts. Filters — season, team, opponent, venue, innings, phase, vs pace/spin, batter hand, qualifier — cross-apply to every panel at once, and can optionally scope the AI analyst to the current view.
- **Three Entrypoints, One Brain:** The web app, a CLI REPL, and a Streamlit dashboard all share `data/cricket.duckdb`; `server.py` and `app.py` import the agent's `RULEBOOK`/`TOOLS`/`client` from `ask.py`, so a single rulebook change updates every surface.
- **Read-Only by Construction:** Every DB connection the apps open is `read_only=True` — the agent physically cannot mutate data, which is the real safety guarantee rather than a string check. Dashboard JSON is `@lru_cache`d since the DB never changes at runtime.

---

## Local Setup

**Prerequisites:** Python 3.13+ · [uv](https://docs.astral.sh/uv/)

```bash
uv sync                          # install deps

uv run python server.py          # web app — dashboard + AI analyst → http://localhost:8765
uv run python ask.py             # CLI analyst (terminal REPL)
uv run streamlit run app.py      # Streamlit dashboard

uv run pytest -q                 # tests
```

The database (`data/cricket.duckdb`) ships **prebuilt**, so it runs immediately. The AI analyst needs `OPENROUTER_API_KEY` in `.env` (the dashboard panels work fully without it — the frontend just shows an "AI offline" notice). Override the model with `CRICKET_MODEL` (default `deepseek/deepseek-v4-pro`).

**Deploy (Docker)**
```bash
docker build -t cricket-bot .
docker run -p 8765:8765 cricket-bot                                  # dashboard only
docker run -p 8765:8765 -e OPENROUTER_API_KEY=sk-or-... cricket-bot  # + AI analyst
```
The image bakes in the prebuilt DB; `.env` is excluded via `.dockerignore` so no secret is baked in.

---

## Agent Architecture

### Request Flow

```
Plain-English question  ──▶  /api/ask (SSE)        or        ask.py REPL
                                   │                              │
                                   ▼                              ▼
                        ┌────────────────────────────────────────────┐
                        │  investigate() loop  (≤ 10 steps)           │
                        │                                            │
                        │  system = RULEBOOK (cricket conventions)   │
                        │  LLM (DeepSeek via OpenRouter) decides:     │
                        │   ┌──────────────────────────────────────┐ │
                        │   │ run_sql    — read-only DuckDB query   │ │
                        │   │ make_chart — query + render PNG/SVG   │ │
                        │   └──────────────────────────────────────┘ │
                        │                                            │
                        │  Model → Tool → Model → ... → Final answer │
                        └────────────────────┬───────────────────────┘
                                             │
                                             ▼
                        Read-only connection → rule-encoding VIEWS
                        (v_deliveries · v_innings · v_matches)
                                             │
                                             ▼
                        Streamed answer + every query shown
```

### Design Patterns

| Pattern | File | Why this pattern |
|---------|------|-----------------|
| Tool-use investigation loop | `ask.py` (`investigate`) | The agent calls `run_sql` as many times as a question needs — a reasoning loop, not a NL→SQL translator over canned queries |
| Rulebook-as-system-prompt | `ask.py` (`RULEBOOK`) | Cricket conventions (formulas, wicket attribution, tie/small-sample caveats) ground free-form SQL so the LLM stays correct without hardcoding queries |
| Rule-encoding views | `ingest/views.sql` | Legal balls, `bowler_conceded`, phases, super-over exclusion, `effective_winner`, names — encoded once so agent and dashboard inherit identical logic |
| Shared agent core | `server.py`, `app.py` import from `ask.py` | One `RULEBOOK`/`TOOLS`/`client` powers web, CLI, and Streamlit — a rulebook change updates every surface at once |
| Read-only connection factory | `core/db.py`, `core/config.py` | `read_only=True` everywhere — the agent *cannot* mutate data; safety is structural, not a string filter |
| SSE streaming + thread memory | `server.py` (`/api/ask`, `agent_events`) | Long-running multi-query investigations stream tool calls and answers live; per-session history keeps follow-ups in context |
| Cached deterministic endpoints | `server.py` (`@lru_cache` `_cached_json`) | Dashboard JSON queries the views directly and is memoized — the DB is read-only, so results never go stale |

---

## Data Layer

`ingest/load.py` flattens raw Cricsheet match JSON into four base tables (`matches`, `deliveries`, `match_players`, `player_attributes`); `ingest/views.sql` builds the three rule-encoding views on top. A few invariants encoded there once, so nothing re-derives them ad hoc:

- `is_legal_ball = (wides=0 AND noballs=0)` — byes/legbyes/penalty are legal balls.
- `bowler_conceded = runs_batter + wides + noballs` (byes/legbyes/penalty excluded).
- Overs are 0-indexed; `phase` ∈ `powerplay`/`middle`/`death`; death overs are `over >= 15`.
- Super-over rows are excluded; `effective_winner = COALESCE(winner, eliminator)`.
- `season` is **TEXT** (`'2026'`, `'2009/10'`) — always quoted.
- Bowler wickets credit only `bowled`/`caught`/`lbw`/`caught and bowled`/`stumped`/`hit wicket`.

**Rebuilding from raw data** (the prebuilt DB ships ready; raw rebuild needs the Cricsheet `ipl_json/` corpus, not included — download from [cricsheet.org](https://cricsheet.org)):

```bash
uv run python -m ingest.load                      # all seasons → data/cricket.duckdb
uv run python -m scripts.build_player_attributes  # 2026 batting-hand / bowling-type enrichment
```

---

## Tests

`uv run pytest -q` should be all green. `tests/test_server.py` and `tests/test_agent.py` cover the web backend and the agent plumbing (the latter mocks the model — no network or API key needed); `tests/test_views.py`, `tests/test_db.py`, and `tests/test_config.py` cover the shared data layer.

---

## Production Gaps

This is a portfolio project running locally. A production deployment would additionally require:

- **Auth & rate limiting** — the AI analyst endpoint is open; per-user throttling of LLM calls and request auth
- **Observability** — structured logging, tracing of every tool call/LLM hop, and error alerting on the investigate loop
- **Cost controls** — caching of common analyst questions; token budgeting and step-cap tuning per request
- **Live data refresh** — an ingestion pipeline that pulls new Cricsheet matches and rebuilds views, instead of a baked-in snapshot
- **Richer enrichment coverage** — batting-hand / bowling-type attributes are densest for 2026 and sparse for older seasons
- **Hardening** — query timeouts and result-size guards on agent SQL beyond the current row cap; prompt-injection review for the free-form question input
