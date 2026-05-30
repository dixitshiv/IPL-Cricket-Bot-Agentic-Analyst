"""IPL 2026 — Command Center backend.

A thin FastAPI layer over the existing pieces:
  • Deterministic dashboard data (JSON) computed live over the rule-encoding
    DuckDB views — no LLM, instant.
  • The agentic analyst (ask.py) streamed over Server-Sent Events, so the
    bespoke frontend can render the investigation as it happens.

Run:  uv run python server.py     (then open http://localhost:8765)
"""
from __future__ import annotations

import json
import os
from functools import lru_cache

import duckdb
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from ask import MAX_STEPS, MODEL, RULEBOOK, TOOLS, client

load_dotenv()

DB = "data/cricket.duckdb"
WICKET = "('bowled','caught','lbw','caught and bowled','stumped','hit wicket')"
WEB = os.path.join(os.path.dirname(__file__), "web")

app = FastAPI(title="IPL 2026 Command Center")
_con = duckdb.connect(DB, read_only=True)


# ───────────────────────── data helpers ─────────────────────────
def esc(v: str) -> str:
    return v.replace("'", "''")


def wc(F, perspective="batting", use_phase=True, use_team=True, use_opp=True) -> str:
    """Build a v_deliveries WHERE clause from the full filter set.

    perspective picks which side `team`/`opponent` bind to: a batting panel
    reads team=batting_team, a bowling panel reads team=bowling_team. The other
    dimensions (venue/innings/phase/bowler_type/batter_hand) apply to both.
    """
    tcol, ocol = ("bowling_team", "batting_team") if perspective == "bowling" else ("batting_team", "bowling_team")
    p = []
    if F.get("season", "All") != "All":
        p.append(f"season = '{esc(F['season'])}'")
    if use_team and F["team"] != "All":
        p.append(f"{tcol} = '{esc(F['team'])}'")
    if use_opp and F["opponent"] != "All":
        p.append(f"{ocol} = '{esc(F['opponent'])}'")
    if use_phase and F["phase"] != "All":
        p.append(f"phase = '{esc(F['phase'])}'")
    if F["innings"] != "All":
        p.append(f"innings = {int(F['innings'])}")
    if F["bowltype"] != "All":
        p.append(f"bowler_type = '{esc(F['bowltype'])}'")
    if F["bathand"] != "All":
        p.append(f"batter_hand = '{esc(F['bathand'])}'")
    if F["venue"] != "All":
        p.append(f"match_id IN (SELECT match_id FROM v_matches WHERE city = '{esc(F['venue'])}')")
    return " AND ".join(p) or "TRUE"


def mwc(F, alias="m") -> str:
    """Match-level (v_matches) clause — season + venue apply to whole matches."""
    parts = []
    if F.get("season", "All") != "All":
        parts.append(f"{alias}.season = '{esc(F['season'])}'")
    if F["venue"] != "All":
        parts.append(f"{alias}.city = '{esc(F['venue'])}'")
    return " AND ".join(parts) or "TRUE"


def match_count(F) -> int:
    p = []
    if F.get("season", "All") != "All":
        p.append(f"season = '{esc(F['season'])}'")
    if F["team"] != "All":
        p.append(f"(batting_team='{esc(F['team'])}' OR bowling_team='{esc(F['team'])}')")
    if F["opponent"] != "All":
        p.append(f"(batting_team='{esc(F['opponent'])}' OR bowling_team='{esc(F['opponent'])}')")
    if F["innings"] != "All":
        p.append(f"innings = {int(F['innings'])}")
    if F["venue"] != "All":
        p.append(f"match_id IN (SELECT match_id FROM v_matches WHERE city='{esc(F['venue'])}')")
    w = " AND ".join(p) or "TRUE"
    return int(one(f"SELECT COUNT(DISTINCT match_id) m FROM v_deliveries WHERE {w}").get("m", 0))


@lru_cache(maxsize=1024)
def _cached_json(sql: str) -> str:
    # DB is static (read-only) so query results are safely cacheable by SQL text.
    return _con.cursor().execute(sql).df().to_json(orient="records")


def rows(sql: str):
    return json.loads(_cached_json(sql))


def one(sql: str):
    r = rows(sql)
    return r[0] if r else {}


# ───────────────────────── API: filters ─────────────────────────
@app.get("/api/filters")
def filters():
    return {
        "seasons": [r["season"] for r in
                    rows("SELECT DISTINCT season FROM v_matches WHERE season IS NOT NULL ORDER BY season DESC")],
        "teams": ["All"] + [r["batting_team"] for r in
                  rows("SELECT DISTINCT batting_team FROM v_deliveries ORDER BY 1")],
        "venues": ["All"] + [r["city"] for r in
                   rows("SELECT DISTINCT city FROM v_matches WHERE city IS NOT NULL ORDER BY 1")],
    }


# ───────────────────────── API: health ─────────────────────────
@app.get("/api/health")
def health():
    """Readiness probe: is the DB reachable, what season coverage exists, and is the
    AI key present. The frontend reads `has_key` to surface an 'AI offline' notice up
    front instead of only failing when a question is asked; deploys can poll this too.
    """
    try:
        seasons = [r["season"] for r in rows(
            "SELECT DISTINCT season FROM v_matches WHERE season IS NOT NULL ORDER BY season DESC")]
        db_ok = True
    except Exception:  # pragma: no cover - the DB should always be present
        seasons, db_ok = [], False
    return {
        "status": "ok" if db_ok else "degraded",
        "db": db_ok,
        "seasons": len(seasons),
        "latest_season": seasons[0] if seasons else None,
        "has_key": bool(os.environ.get("OPENROUTER_API_KEY")),
        "model": MODEL,
    }


# ───────────────────────── API: dashboard ─────────────────────────
@app.get("/api/dashboard")
def dashboard(season: str = "2026", team: str = "All", opponent: str = "All", venue: str = "All",
              innings: str = "All", phase: str = "All", bowltype: str = "All",
              bathand: str = "All", min_balls: int = 30):
    F = {"season": season, "team": team, "opponent": opponent, "venue": venue, "innings": innings,
         "phase": phase, "bowltype": bowltype, "bathand": bathand}
    wb = wc(F, "batting")
    wbowl = wc(F, "bowling")
    mb = int(min_balls)

    bat = one(f"""SELECT COALESCE(SUM(runs_total),0) runs,
                    COALESCE(ROUND(6.0*SUM(runs_total)/NULLIF(COUNT(*) FILTER(WHERE is_legal_ball),0),2),0) rr,
                    COUNT(*) FILTER(WHERE runs_batter=6) sixes
                  FROM v_deliveries WHERE {wb}""")
    wk = one(f"SELECT COUNT(*) w FROM v_deliveries WHERE {wbowl} AND wicket_kind IN {WICKET}")
    matches = match_count(F)

    return {
        "kpis": {
            "matches": int(matches),
            "runs": int(bat.get("runs", 0)),
            "wickets": int(wk.get("w", 0)),
            "sixes": int(bat.get("sixes", 0)),
            "run_rate": float(bat.get("rr", 0) or 0),
        },
        "run_scorers": rows(f"""SELECT batter_name player, SUM(runs_batter) AS "value"
            FROM v_deliveries WHERE {wb} GROUP BY 1 ORDER BY "value" DESC LIMIT 10"""),
        "wicket_takers": rows(f"""SELECT bowler_name player, COUNT(*) AS "value"
            FROM v_deliveries WHERE {wbowl} AND wicket_kind IN {WICKET}
            GROUP BY 1 ORDER BY "value" DESC LIMIT 10"""),
        "runs_by_phase": rows(f"""SELECT phase, SUM(runs_total) AS "value" FROM v_deliveries
            WHERE {wc(F, 'batting', use_phase=False)} GROUP BY 1"""),
        "bat_vs_chase": rows(f"""WITH fb AS (SELECT match_id, batting_team FROM v_innings WHERE innings=1)
            SELECT CASE WHEN m.effective_winner=f.batting_team THEN 'Bat First' ELSE 'Chasing' END AS "label",
                   COUNT(*) AS "value"
            FROM v_matches m JOIN fb f ON f.match_id=m.match_id
            WHERE m.effective_winner IS NOT NULL AND {mwc(F)} GROUP BY 1"""),
        "strike_rate": rows(f"""SELECT batter_name player,
              ROUND(100.0*SUM(runs_batter)/NULLIF(COUNT(*) FILTER(WHERE is_legal_ball),0),1) AS "value"
            FROM v_deliveries WHERE {wb} GROUP BY 1
            HAVING COUNT(*) FILTER(WHERE is_legal_ball) >= {mb} ORDER BY "value" DESC LIMIT 10"""),
        "sixes": rows(f"""SELECT batter_name player, COUNT(*) AS "value" FROM v_deliveries
            WHERE {wb} AND runs_batter=6 GROUP BY 1 ORDER BY "value" DESC LIMIT 10"""),
        "average": rows(f"""SELECT batter_name player,
              ROUND(SUM(runs_batter)*1.0/NULLIF(COUNT(*) FILTER(WHERE player_out=batter_id),0),1) AS "value"
            FROM v_deliveries WHERE {wb} GROUP BY 1
            HAVING COUNT(*) FILTER(WHERE is_legal_ball) >= {mb}
               AND COUNT(*) FILTER(WHERE player_out=batter_id) > 0
            ORDER BY "value" DESC LIMIT 10"""),
        "economy": rows(f"""SELECT bowler_name player,
              ROUND(6.0*SUM(bowler_conceded)/NULLIF(COUNT(*) FILTER(WHERE is_legal_ball),0),2) AS "value"
            FROM v_deliveries WHERE {wbowl} GROUP BY 1
            HAVING COUNT(*) FILTER(WHERE is_legal_ball) >= {mb} ORDER BY "value" ASC LIMIT 10"""),
        "dot_pct": rows(f"""SELECT bowler_name player,
              ROUND(100.0*COUNT(*) FILTER(WHERE is_legal_ball AND runs_batter=0)
                    /NULLIF(COUNT(*) FILTER(WHERE is_legal_ball),0),1) AS "value"
            FROM v_deliveries WHERE {wbowl} GROUP BY 1
            HAVING COUNT(*) FILTER(WHERE is_legal_ball) >= {mb} ORDER BY "value" DESC LIMIT 10"""),
        "econ_by_phase": rows(f"""SELECT phase,
              ROUND(6.0*SUM(bowler_conceded)/NULLIF(COUNT(*) FILTER(WHERE is_legal_ball),0),2) AS "value"
            FROM v_deliveries WHERE {wc(F, 'bowling', use_phase=False)} GROUP BY 1"""),
        "team_wins": rows(f"""SELECT m.effective_winner player, COUNT(*) AS "value" FROM v_matches m
            WHERE m.effective_winner IS NOT NULL AND {mwc(F)} GROUP BY 1 ORDER BY "value" DESC"""),
        "team_runs": rows(f"""SELECT batting_team player, SUM(runs_total) AS "value" FROM v_deliveries
            WHERE {wc(F, 'batting', use_team=False)} GROUP BY 1 ORDER BY "value" DESC"""),
        "team_rr": rows(f"""SELECT batting_team player,
              ROUND(6.0*SUM(runs_total)/NULLIF(COUNT(*) FILTER(WHERE is_legal_ball),0),2) AS "value"
            FROM v_deliveries WHERE {wc(F, 'batting', use_team=False)} GROUP BY 1 ORDER BY "value" DESC"""),
    }


# ───────────────────────── API: player drilldown ─────────────────────────
@app.get("/api/player")
def player(name: str, season: str = "2026"):
    raw = esc(name)
    hit = one(f"""SELECT nm, COUNT(*) c FROM (
        SELECT batter_name nm FROM v_deliveries WHERE batter_name ILIKE '%{raw}%'
        UNION ALL SELECT bowler_name FROM v_deliveries WHERE bowler_name ILIKE '%{raw}%'
    ) WHERE nm IS NOT NULL GROUP BY nm ORDER BY c DESC LIMIT 1""")
    name = hit.get("nm") or name      # resolve to the canonical stored name
    nm = esc(name)
    seas = "" if season == "All" else f"AND season = '{esc(season)}'"
    bat = one(f"""SELECT
        COUNT(DISTINCT match_id) matches,
        COALESCE(SUM(runs_batter),0) runs,
        COUNT(*) FILTER(WHERE is_legal_ball) balls,
        ROUND(100.0*SUM(runs_batter)/NULLIF(COUNT(*) FILTER(WHERE is_legal_ball),0),1) sr,
        ROUND(SUM(runs_batter)*1.0/NULLIF(COUNT(*) FILTER(WHERE player_out=batter_id),0),1) bat_avg,
        COUNT(*) FILTER(WHERE runs_batter=6) sixes,
        COUNT(*) FILTER(WHERE runs_batter=4) fours,
        ROUND(100.0*COUNT(*) FILTER(WHERE is_legal_ball AND runs_batter=0)
              /NULLIF(COUNT(*) FILTER(WHERE is_legal_ball),0),1) dot
      FROM v_deliveries WHERE batter_name = '{nm}' {seas}""")
    bowl = one(f"""SELECT
        COUNT(*) FILTER(WHERE is_legal_ball) balls,
        COUNT(*) FILTER(WHERE wicket_kind IN {WICKET}) wickets,
        ROUND(6.0*SUM(bowler_conceded)/NULLIF(COUNT(*) FILTER(WHERE is_legal_ball),0),2) econ,
        ROUND(100.0*COUNT(*) FILTER(WHERE is_legal_ball AND runs_batter=0)
              /NULLIF(COUNT(*) FILTER(WHERE is_legal_ball),0),1) dot
      FROM v_deliveries WHERE bowler_name = '{nm}' {seas}""")
    return {
        "name": name,
        "teams": [r["t"] for r in rows(
            f"SELECT DISTINCT batting_team t FROM v_deliveries WHERE batter_name='{nm}' ORDER BY 1")],
        "seasons": [r["s"] for r in rows(
            f"SELECT DISTINCT season s FROM v_deliveries WHERE batter_name='{nm}' OR bowler_name='{nm}' ORDER BY season")],
        "season": season,
        "batting": bat,
        "bowling": bowl,
        "is_bowler": int(bowl.get("balls") or 0) >= 30,
        "runs_by_season": rows(f"""SELECT season player, SUM(runs_batter) AS "value"
            FROM v_deliveries WHERE batter_name='{nm}' GROUP BY 1 ORDER BY season"""),
        "sr_by_phase": rows(f"""SELECT phase player,
              ROUND(100.0*SUM(runs_batter)/NULLIF(COUNT(*) FILTER(WHERE is_legal_ball),0),1) AS "value"
            FROM v_deliveries WHERE batter_name='{nm}' {seas} GROUP BY 1"""),
        "sr_vs_type": rows(f"""SELECT bowler_type player,
              ROUND(100.0*SUM(runs_batter)/NULLIF(COUNT(*) FILTER(WHERE is_legal_ball),0),1) AS "value"
            FROM v_deliveries WHERE batter_name='{nm}' {seas} AND bowler_type IS NOT NULL GROUP BY 1"""),
        "runs_by_venue": rows(f"""SELECT m.city player, SUM(d.runs_batter) AS "value"
            FROM v_deliveries d JOIN v_matches m ON m.match_id=d.match_id
            WHERE d.batter_name='{nm}' {seas.replace('season', 'd.season')}
            GROUP BY 1 ORDER BY "value" DESC LIMIT 6"""),
        "econ_by_season": rows(f"""SELECT season player,
              ROUND(6.0*SUM(bowler_conceded)/NULLIF(COUNT(*) FILTER(WHERE is_legal_ball),0),2) AS "value"
            FROM v_deliveries WHERE bowler_name='{nm}' GROUP BY 1 ORDER BY season"""),
        "wkts_by_season": rows(f"""SELECT season player,
              COUNT(*) FILTER(WHERE wicket_kind IN {WICKET}) AS "value"
            FROM v_deliveries WHERE bowler_name='{nm}' GROUP BY 1 ORDER BY season"""),
    }


# ───────────────────────── API: insights & matchups ─────────────────────────
def _resolve(name: str, col: str) -> str:
    raw = esc(name)
    hit = one(f"SELECT {col} nm, COUNT(*) c FROM v_deliveries WHERE {col} ILIKE '%{raw}%' "
              f"AND {col} IS NOT NULL GROUP BY 1 ORDER BY c DESC LIMIT 1")
    return hit.get("nm") or name


@app.get("/api/insights")
def insights(season: str = "2026"):
    seas = "" if season == "All" else f"AND season = '{esc(season)}'"
    mseas = "" if season == "All" else f"AND m.season = '{esc(season)}'"
    minb = 600 if season == "All" else 60
    bowlers = rows(f"""SELECT bowler_name player,
        ROUND(6.0*SUM(bowler_conceded)/NULLIF(COUNT(*) FILTER(WHERE is_legal_ball),0),2) x,
        COUNT(*) FILTER(WHERE wicket_kind IN {WICKET}) y
      FROM v_deliveries WHERE bowler_name IS NOT NULL {seas}
      GROUP BY 1 HAVING COUNT(*) FILTER(WHERE is_legal_ball) >= {minb}
      ORDER BY y DESC LIMIT 40""")
    batters = rows(f"""SELECT batter_name player,
        ROUND(SUM(runs_batter)*1.0/NULLIF(COUNT(*) FILTER(WHERE player_out=batter_id),0),1) x,
        ROUND(100.0*SUM(runs_batter)/NULLIF(COUNT(*) FILTER(WHERE is_legal_ball),0),1) y
      FROM v_deliveries WHERE batter_name IS NOT NULL {seas}
      GROUP BY 1 HAVING COUNT(*) FILTER(WHERE is_legal_ball) >= {minb}
         AND COUNT(*) FILTER(WHERE player_out=batter_id) > 0
      ORDER BY y DESC LIMIT 40""")
    venues = rows(f"""SELECT m.city player, ROUND(AVG(i.runs),0) AS "value"
      FROM v_matches m JOIN v_innings i ON i.match_id=m.match_id AND i.innings=1
      WHERE m.city IS NOT NULL {mseas} GROUP BY 1 ORDER BY "value" DESC""")
    return {"bowlers": bowlers, "batters": batters, "venues": venues, "minb": minb}


@app.get("/api/matchup")
def matchup(batter: str, bowler: str, season: str = "All"):
    bat, bowl = _resolve(batter, "batter_name"), _resolve(bowler, "bowler_name")
    seas = "" if season == "All" else f"AND season = '{esc(season)}'"
    r = one(f"""SELECT
        COUNT(*) FILTER(WHERE is_legal_ball) balls,
        COALESCE(SUM(runs_batter),0) runs,
        ROUND(100.0*SUM(runs_batter)/NULLIF(COUNT(*) FILTER(WHERE is_legal_ball),0),1) sr,
        COUNT(*) FILTER(WHERE player_out=batter_id AND wicket_kind IN {WICKET}) dismissals,
        COUNT(*) FILTER(WHERE runs_batter=6) sixes,
        COUNT(*) FILTER(WHERE runs_batter=4) fours,
        ROUND(100.0*COUNT(*) FILTER(WHERE is_legal_ball AND runs_batter=0)
              /NULLIF(COUNT(*) FILTER(WHERE is_legal_ball),0),1) dot
      FROM v_deliveries WHERE batter_name='{esc(bat)}' AND bowler_name='{esc(bowl)}' {seas}""")
    return {"batter": bat, "bowler": bowl, "season": season, "stats": r,
            "found": int(r.get("balls") or 0) > 0}


# ───────────────────────── API: agent (SSE) ─────────────────────────
def sse(obj) -> str:
    return f"data: {json.dumps(obj)}\n\n"


def filter_context(F) -> str | None:
    """Turn active dashboard filters into a soft scoping note for the agent.

    Returned as guidance the agent folds into its own SQL — the user can still
    override any of it in their wording. Returns None if no filters are active.
    """
    names = {"team": "team (the side in focus)", "opponent": "opponent",
             "venue": "venue", "innings": "innings", "phase": "phase",
             "bowltype": "bowling type faced (bowler_type)", "bathand": "batter hand (batter_hand)"}
    active = [f"{label} = {F[k]}" for k, label in names.items() if F.get(k, "All") not in (None, "All")]
    season = F.get("season", "2026")
    if season == "All":
        active.insert(0, "season = all seasons (treat as career / all-time; do NOT filter by season)")
    else:
        active.insert(0, f"season = {season} (filter v_deliveries.season = '{season}')")
    return (
        "The user has dashboard filters active and wants this question scoped to them. "
        "Translate each into SQL WHERE conditions on v_deliveries: season→v_deliveries.season, "
        "team→batting_team or bowling_team depending on whether the metric is batting- or "
        "bowling-centric, opponent→the other team column, venue→matches.city (join/subquery on "
        "match_id), innings→innings, bowltype→bowler_type, bathand→batter_hand. "
        "The user MAY override any of these if their wording says so. Active filters: "
        + "; ".join(active) + ".")


# In-memory conversation sessions: sid -> compact [user/assistant] history.
SESSIONS: dict[str, list] = {}


def agent_events(messages: list):
    """Run the agent loop over `messages` (mutated in place); yield dict events."""
    con = _con.cursor()
    cli = client()
    try:
        for _ in range(MAX_STEPS):
            resp = cli.chat.completions.create(
                model=MODEL, temperature=0, tools=TOOLS, tool_choice="auto", messages=messages)
            msg = resp.choices[0].message
            messages.append(msg.model_dump(exclude_none=True))
            if not msg.tool_calls:
                yield {"type": "answer", "text": msg.content or ""}
                return
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                if tc.function.name == "run_sql":
                    sql = args.get("query", "")
                    try:
                        df = con.execute(sql).df()
                        result = df.head(50).to_markdown(index=False) if len(df) else "(0 rows)"
                        yield {"type": "sql", "query": sql, "columns": list(df.columns),
                               "rows": json.loads(df.head(12).to_json(orient="records"))}
                    except Exception as e:
                        result = f"SQL ERROR: {e}"
                        yield {"type": "sql", "query": sql, "error": str(e)}
                else:
                    sql = args.get("query", "")
                    try:
                        df = con.execute(sql).df()
                        result = f"chart rendered: {args.get('title')}"
                        yield {"type": "chart", "kind": args.get("kind", "bar"), "x": args.get("x"),
                               "y": args.get("y"), "title": args.get("title"),
                               "data": json.loads(df.to_json(orient="records"))}
                    except Exception as e:
                        result = f"SQL ERROR: {e}"
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
        yield {"type": "answer", "text": "_(reached the step limit — try narrowing the question.)_"}
    except Exception as e:
        yield {"type": "error", "text": str(e)}


@app.get("/api/ask")
def ask(q: str, sid: str = "", scope: int = 0, season: str = "2026", team: str = "All",
        opponent: str = "All", venue: str = "All", innings: str = "All", phase: str = "All",
        bowltype: str = "All", bathand: str = "All"):
    if not os.environ.get("OPENROUTER_API_KEY"):
        def nokey():
            yield sse({"type": "error", "text": "OPENROUTER_API_KEY not set in .env"})
            yield sse({"type": "done"})
        return StreamingResponse(nokey(), media_type="text/event-stream")
    F = {"season": season, "team": team, "opponent": opponent, "venue": venue, "innings": innings,
         "phase": phase, "bowltype": bowltype, "bathand": bathand}
    ctx = filter_context(F) if scope else None
    # A session carries compact prior Q&A so follow-ups ("now vs pace") work.
    history = SESSIONS.setdefault(sid, []) if sid else []
    messages = ([{"role": "system", "content": RULEBOOK}] + history
                + [{"role": "user", "content": f"{ctx}\n\nQuestion: {q}" if ctx else q}])

    def gen():
        final = ""
        for ev in agent_events(messages):
            if ev.get("type") == "answer":
                final = ev["text"]
            yield sse(ev)
        if sid:
            history.append({"role": "user", "content": q})
            history.append({"role": "assistant", "content": final})
            if len(history) > 12:          # keep ~6 turns of memory
                del history[: len(history) - 12]
        yield sse({"type": "done"})
    return StreamingResponse(gen(), media_type="text/event-stream")


# ───────────────────────── static frontend ─────────────────────────
@app.get("/")
def index():
    return FileResponse(os.path.join(WEB, "index.html"))


app.mount("/", StaticFiles(directory=WEB), name="web")


if __name__ == "__main__":
    uvicorn.run(app, host=os.environ.get("HOST", "127.0.0.1"),
                port=int(os.environ.get("PORT", "8765")), log_level="warning")
