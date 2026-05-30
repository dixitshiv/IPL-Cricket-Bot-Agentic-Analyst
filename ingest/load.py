# ingest/load.py
"""Load flattened Cricsheet matches into DuckDB, idempotently.

`load_match` deletes any rows for a match_id then bulk-inserts the freshly
flattened rows, so re-running ingestion never duplicates data.
"""
from __future__ import annotations

import json
from pathlib import Path

from core.config import JSON_DIR, SEASON
from core.db import connect
from ingest.flatten import flatten_match

_SCHEMA_SQL = Path(__file__).resolve().parent / "schema.sql"
_VIEWS_SQL = Path(__file__).resolve().parent / "views.sql"

# Column order per table — drives both the INSERT statement and the row tuples.
_MATCH_COLS = [
    "match_id", "match_date", "season", "event_name", "match_number",
    "venue", "city", "team_a", "team_b", "toss_winner", "toss_decision",
    "winner", "outcome_by_runs", "outcome_by_wickets", "eliminator",
    "result", "method", "player_of_match", "is_super_over_match",
]
_DELIVERY_COLS = [
    "match_id", "innings", "batting_team", "bowling_team", "over", "ball",
    "batter_id", "bowler_id", "non_striker_id", "runs_batter", "runs_extras",
    "runs_total", "wides", "noballs", "byes", "legbyes", "penalty",
    "is_legal_ball", "phase", "wicket_kind", "player_out", "is_super_over",
]
_PLAYER_COLS = ["match_id", "team", "player_name", "registry_id"]


def create_schema(con) -> None:
    """Execute ingest/schema.sql (idempotent DDL with IF NOT EXISTS)."""
    con.execute(_SCHEMA_SQL.read_text())


def create_views(con) -> None:
    """Execute ingest/views.sql (CREATE OR REPLACE VIEW)."""
    con.execute(_VIEWS_SQL.read_text())


def _insert(con, table: str, cols: list[str], rows: list[dict]) -> None:
    if not rows:
        return
    placeholders = ", ".join(["?"] * len(cols))
    col_list = ", ".join(cols)
    sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"
    params = [[row[c] for c in cols] for row in rows]
    con.executemany(sql, params)


def load_match(con, raw: dict, match_id: int) -> None:
    """Idempotently load one match: DELETE existing rows then INSERT fresh."""
    flat = flatten_match(raw, match_id)   # pure; raises before any DB write
    con.execute("BEGIN")
    try:
        con.execute("DELETE FROM deliveries WHERE match_id = ?", [match_id])
        con.execute("DELETE FROM match_players WHERE match_id = ?", [match_id])
        con.execute("DELETE FROM matches WHERE match_id = ?", [match_id])
        _insert(con, "matches", _MATCH_COLS, [flat["match"]])
        _insert(con, "deliveries", _DELIVERY_COLS, flat["deliveries"])
        _insert(con, "match_players", _PLAYER_COLS, flat["players"])
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise


def build_database(con, json_dir: str = JSON_DIR, season: str | None = SEASON) -> dict:
    """Load matches under `json_dir` into `con`.

    `season=None` loads every season; otherwise only matches of that season.
    match_id is the filename stem (INTEGER). Idempotent: each match is loaded
    via load_match (DELETE-then-INSERT), so re-running does not duplicate rows.
    Files that fail to parse/flatten (older formats) are counted and skipped so
    one bad file never aborts the build.
    """
    loaded = failed = 0
    for path in sorted(Path(json_dir).glob("*.json")):
        try:
            with open(path) as fh:
                raw = json.load(fh)
            if season is not None and str(raw["info"].get("season")) != str(season):
                continue
            load_match(con, raw, int(path.stem))
            loaded += 1
        except Exception:
            failed += 1
    return {
        "loaded": loaded,
        "failed": failed,
        "matches": con.execute("SELECT COUNT(*) FROM matches").fetchone()[0],
        "deliveries": con.execute("SELECT COUNT(*) FROM deliveries").fetchone()[0],
        "players": con.execute("SELECT COUNT(*) FROM match_players").fetchone()[0],
    }


def main() -> None:
    """Build data/cricket.duckdb from ALL seasons and print the row counts."""
    con = connect()
    try:
        create_schema(con)
        counts = build_database(con, season=None)   # None = every season
        create_views(con)
        seasons = con.execute("SELECT COUNT(DISTINCT season) FROM matches").fetchone()[0]
        print(
            f"Loaded {counts['loaded']} matches across {seasons} seasons "
            f"({counts['failed']} files skipped): "
            f"{counts['matches']} matches, {counts['deliveries']} deliveries, "
            f"{counts['players']} player rows."
        )
    finally:
        con.close()


if __name__ == "__main__":
    main()
