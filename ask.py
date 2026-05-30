"""Cricket NL — an agentic analyst over IPL 2026 ball-by-ball data.

You ask a plain-English question (or hand it a topic). An LLM *investigates*: it
calls a run_sql tool as many times as it needs to explore the data, reasons over
what it finds, draws a chart when that helps, and writes a real analytical answer
— from a one-line fact to a multi-query mini-report.

The LLM writes all its own SQL. It is not a translator over canned queries. What
keeps it correct is (a) the rule-encoding views (v_deliveries / v_innings /
v_matches) that bake in the hard rules once, and (b) the RULEBOOK below — the
cricket conventions a real analyst needs, given as reference, not a cage.

Every query it runs is printed, so you can see (and check) its work.

Run:  uv run python ask.py
Needs OPENROUTER_API_KEY in .env. Override the model with CRICKET_MODEL.
"""
from __future__ import annotations

import json
import os
import subprocess
import time

import duckdb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from openai import OpenAI

DB = "data/cricket.duckdb"
OUT = "out"
MODEL = os.environ.get("CRICKET_MODEL", "deepseek/deepseek-v4-pro")
MAX_STEPS = 10        # cap the investigate loop
MAX_ROWS = 50         # rows returned to the model per query

RULEBOOK = """\
You are a cricket analyst for the IPL 2026 season ('2026'), working over a DuckDB
database of ball-by-ball data. You answer by INVESTIGATING: write SQL, look at the
results, run follow-ups, then explain. You write all your own SQL — there are no
canned queries. Back every number you state with a query you actually ran; never
invent or estimate a number.

## Prefer the rule-encoding VIEWS (they bake in the hard rules correctly)

v_deliveries — one row per legal+illegal ball, super-overs already excluded. Columns:
  match_id, season, innings, batting_team, bowling_team, over, ball,
  batter_id, bowler_id, non_striker_id,
  runs_batter, runs_extras, runs_total, wides, noballs, byes, legbyes, penalty,
  is_legal_ball, phase, wicket_kind, player_out,
  bowler_conceded,                      -- = runs_batter + wides + noballs
  batter_name, batter_hand,             -- batter_name is the FULL name, e.g. 'V Kohli'
  bowler_name, bowler_type, bowler_style

v_innings — one row per innings: match_id, innings, batting_team, bowling_team,
  runs, legal_balls, wickets.

v_matches — one row per match: all match columns plus
  effective_winner = COALESCE(winner, eliminator).

Base tables exist too (matches, deliveries, match_players, player_attributes) but
prefer the views — the base `deliveries` includes super-overs and lacks names.

## Core conventions
- `over` is 0-indexed (0–19). `ball` is 1-based within the over.
- Legal ball = (wides=0 AND noballs=0); use the `is_legal_ball` column. Byes, legbyes
  and penalty do NOT make a ball illegal.
- `phase` is precomputed: 'powerplay' | 'middle' | 'death'. Death overs are over >= 15.
- Super-overs are already excluded from the views. (In base `deliveries`, filter
  is_super_over = FALSE.)
- Data spans every IPL season from 2008 to 2026; v_deliveries has a `season`
  column (values like '2026', '2025', '2012', '2009/10'); season is TEXT, so always
  QUOTE it — `season = '2026'`, never a bare integer `season = 2026` (that throws a
  DuckDB conversion error on values like '2009/10'). DEFAULT to the latest
  season — filter `season = '2026'` — unless the user asks about a different
  season, a span of seasons, or career / all-time / "ever" (then don't filter by
  season). Note: batter_hand / bowler_type enrichment is richest for 2026 and may
  be NULL for older seasons.

## Metric formulas (reference — adapt them, don't just paste them)
- Balls faced/bowled = COUNT(*) FILTER (WHERE is_legal_ball).
- Batting strike rate = 100.0 * SUM(runs_batter) / balls faced.
- Bowling economy = 6.0 * SUM(bowler_conceded) / balls bowled.
  (bowler_conceded excludes byes/legbyes/penalty — already in the column.)
- Run rate = 6.0 * SUM(runs_total) / balls (runs_total includes extras).
- Batting average = SUM(runs_batter) / COUNT(*) FILTER (WHERE player_out = batter_id).
- Dot-ball % = 100.0 * COUNT(*) FILTER (WHERE is_legal_ball AND runs_batter = 0)
                     / balls faced.
- Boundaries: fours = runs_batter = 4, sixes = runs_batter = 6 (off the bat). Count
  them by runs_batter ALONE — do NOT add an is_legal_ball filter: a four or six hit
  off a no-ball still counts (this is also how the dashboard counts, so stay consistent).
- Opening partnership = runs scored before the first dismissal of the innings.
- Win rate (bat-first vs chasing): the team batting in innings 1 (from v_innings)
  is bat-first; compare to v_matches.effective_winner over decided matches
  (effective_winner IS NOT NULL).
- Always guard division with NULLIF(denominator, 0).

## Wickets — bowler attribution (IMPORTANT)
A wicket counts for the BOWLER only when
  wicket_kind IN ('bowled','caught','lbw','caught and bowled','stumped','hit wicket').
Run-outs, retired hurt/out, and 'obstructing the field' do NOT credit the bowler.
For a batter's dismissals, use player_out = batter_id (any wicket_kind).

## Players & names
- Filter or label players by the view's `batter_name` / `bowler_name` (full canonical
  names) with ILIKE, e.g. bowler_name ILIKE '%bumrah%'. registry_id (batter_id/
  bowler_id) is the join key if you ever need the base tables.
- Do NOT use match_players.player_name for name matching — it's abbreviated
  ('B Kumar') and will silently miss. For matches-played counts, join match_players
  by registry_id after resolving the name on the views.
- If a name is ambiguous (matches several players) or a ranking is TIED at the top,
  surface all of them rather than silently picking one. For any top-N list (LIMIT N),
  also check whether the N-th place is tied with the rows just beyond the cutoff
  (peek a few past N) before calling anyone 'alone' at a rank — cutoff ties are easy
  to miss and make a confident claim wrong.

## Sanity self-check (typical valid ranges)
strike_rate 0–400, economy 0–36, run_rate 0–36, dot% 0–100, batting_avg 0–1000,
win_rate 0–100. A rate computed off fewer than 10 legal balls is a SMALL SAMPLE —
say so. If a result looks outside these ranges, re-examine your SQL.

## How to answer
- Match effort to the question. A concrete factual question → usually one query,
  then a crisp answer. An open topic ('analyze X', 'what's interesting about Y') →
  run several queries from different angles, make a chart or two, and write a short
  structured report.
- Use the make_chart tool when a ranking, trend, or comparison benefits from a visual.
- State caveats plainly: small samples, ties, qualification thresholds you chose,
  and anything the data can't answer. If it's out of scope (not in this dataset),
  say so rather than guessing.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_sql",
            "description": "Run a read-only DuckDB SQL query and get the result rows back "
            "as a table. Use it to investigate; call it as many times as you need.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "A single SELECT/WITH query."}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "make_chart",
            "description": "Run a query and render its result as a chart (PNG, opened for "
            "the user). Use for rankings, trends, or comparisons.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Query whose rows to plot."},
                    "kind": {"type": "string", "enum": ["bar", "line"]},
                    "x": {"type": "string", "description": "Column for the x-axis."},
                    "y": {"type": "string", "description": "Numeric column for the y-axis."},
                    "title": {"type": "string"},
                },
                "required": ["query", "kind", "x", "y", "title"],
            },
        },
    },
]


def client() -> OpenAI:
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ["OPENROUTER_API_KEY"],
    )


def tool_run_sql(con, query: str) -> str:
    try:
        df = con.execute(query).df()
    except Exception as e:
        return f"SQL ERROR: {e}"
    if df.empty:
        return "(0 rows)"
    truncated = len(df) > MAX_ROWS
    table = df.head(MAX_ROWS).to_markdown(index=False)
    if truncated:
        table += f"\n... ({len(df)} rows total, showing first {MAX_ROWS})"
    return table


def tool_make_chart(con, query: str, kind: str, x: str, y: str, title: str) -> str:
    try:
        df = con.execute(query).df()
    except Exception as e:
        return f"SQL ERROR: {e}"
    if df.empty:
        return "(0 rows — nothing to chart)"
    if x not in df.columns or y not in df.columns:
        return f"column not found: need '{x}' and '{y}', have {list(df.columns)}"
    fig, ax = plt.subplots(figsize=(9, 5))
    if kind == "bar":
        ax.bar(df[x].astype(str), df[y])
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    else:
        ax.plot(df[x], df[y], marker="o")
    ax.set_xlabel(x)
    ax.set_ylabel(y)
    ax.set_title(title)
    fig.tight_layout()
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"{time.strftime('%Y%m%d-%H%M%S')}.png")
    fig.savefig(path, dpi=120)
    plt.close(fig)
    subprocess.run(["open", path], check=False)
    return f"chart saved and opened: {path}"


def dispatch(con, name: str, args: dict) -> str:
    if name == "run_sql":
        sql = args.get("query", "")
        print("\n  SQL> " + sql.strip().replace("\n", "\n       "))
        return tool_run_sql(con, sql)
    if name == "make_chart":
        print(f"\n  CHART> {args.get('kind')} {args.get('x')} vs {args.get('y')}: "
              f"{args.get('title')}")
        return tool_make_chart(con, **args)
    return f"unknown tool: {name}"


def investigate(cli: OpenAI, con, question: str) -> None:
    messages = [
        {"role": "system", "content": RULEBOOK},
        {"role": "user", "content": question},
    ]
    for _ in range(MAX_STEPS):
        resp = cli.chat.completions.create(
            model=MODEL,
            temperature=0,
            tools=TOOLS,
            tool_choice="auto",
            messages=messages,
        )
        msg = resp.choices[0].message
        messages.append(msg.model_dump(exclude_none=True))

        if not msg.tool_calls:
            print("\nANSWER:\n  " + (msg.content or "(no answer)").replace("\n", "\n  "))
            return

        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            result = dispatch(con, tc.function.name, args)
            messages.append(
                {"role": "tool", "tool_call_id": tc.id, "content": result}
            )

    print("\n(reached the step limit without a final answer — try narrowing the question.)")


def main() -> None:
    load_dotenv()
    if not os.environ.get("OPENROUTER_API_KEY"):
        raise SystemExit("Set OPENROUTER_API_KEY in .env")
    cli = client()
    con = duckdb.connect(DB, read_only=True)
    print(f"Cricket NL (IPL 2026) — agentic analyst. Model: {MODEL}")
    print("Ask a question or hand it a topic ('analyze RCB's death bowling'). 'quit' to exit.")
    while True:
        try:
            q = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not q:
            continue
        if q.lower() in {"quit", "exit", "q"}:
            break
        try:
            investigate(cli, con, q)
        except Exception as e:
            print(f"\nError: {e}")


if __name__ == "__main__":
    main()
