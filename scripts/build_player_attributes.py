"""Build, load, and validate the player_attributes enrichment table.

player_attributes is NOT present in Cricsheet (which has no batting-hand /
bowling-type fields). This module:

  1. roster_to_enrich / season_bowler_ids  -- read which season-2026 players
     need attributes, and which of them actually bowled.
  2. (auto-draft, executed offline -- see module docstring section below)
     produces data/player_attributes.csv with the columns in CSV_HEADER.
  3. load_player_attributes  -- deterministic, idempotent CSV -> table load.
  4. validate_player_attributes -- fail-closed checks over the loaded table.

AUTO-DRAFT EXECUTION SUB-PROCEDURE (run once; output is the CSV this module loads)
--------------------------------------------------------------------------------
The auto-draft is a one-time data-entry pass, not part of the import-time code.
The executor runs `roster_to_enrich(con)` to get the (registry_id,
canonical_name) list, then for each registry_id fills batting_hand,
bowling_type, bowling_style by research (a Workflow / web lookup of the player's
known role) and writes data/player_attributes.csv with header == CSV_HEADER.

CSV CONTRACT (exact):
  registry_id   -- the Cricsheet people id; the JOIN key. MUST match roster.
  canonical_name-- the cricsheet short name (e.g. "SS Iyer").
  batting_hand  -- "RHB" or "LHB" (required, never blank).
  bowling_type  -- "pace" | "spin" | "" (empty -> NULL: pure batter / never bowls).
  bowling_style -- free text role code (RF, RFM, LF, OB, LBG, SLA, ...) or "".
  source        -- provenance string (e.g. "espncricinfo", "cricsheet-register",
                   "llm-draft"); used by validate / explain to flag low trust.
  confidence    -- float in [0.0, 1.0].

Example rows (registry_ids verified from ipl_json/1529311.json):
  85ec8e33,SS Iyer,RHB,,,espncricinfo,0.99            # POTM, pure batter (RHB)
  57ee1fde,YS Chahal,RHB,spin,LBG,espncricinfo,0.99   # leg-spinner
  8cf9814c,Mohammed Shami,RHB,pace,RF,espncricinfo,0.99  # right-arm fast

VERIFICATION GATE (must pass before the table is trusted):
  After load, validate_player_attributes(con).ok MUST be True AND
  .uncovered_bowlers MUST be empty -- i.e. every registry_id that bowled a ball
  in season 2026 has a non-NULL bowling_type. Any bowler the auto-draft left
  blank is reported and blocks the gate until the CSV is corrected (or the row
  is given bowling_type with a low confidence + source="llm-draft" for review).
"""
from __future__ import annotations

import csv
import sys
from dataclasses import dataclass

from core.db import connect

PLAYER_ATTRIBUTES_CSV = "data/player_attributes.csv"

CSV_HEADER = [
    "registry_id",
    "canonical_name",
    "batting_hand",
    "bowling_type",
    "bowling_style",
    "source",
    "confidence",
]


def roster_to_enrich(con) -> list[dict]:
    """Distinct (registry_id, canonical_name) for every season-2026 player.

    Reads match_players (squads). canonical_name is the player_name as it
    appears in Cricsheet; one name per id (picked deterministically via MIN).
    """
    rows = con.execute(
        """
        SELECT registry_id, MIN(player_name) AS canonical_name
        FROM match_players
        WHERE registry_id IS NOT NULL
        GROUP BY registry_id
        ORDER BY registry_id
        """
    ).fetchall()
    return [{"registry_id": r[0], "canonical_name": r[1]} for r in rows]


def season_bowler_ids(con) -> set[str]:
    """Distinct bowler_id that bowled any ball (legal or not) in season 2026."""
    rows = con.execute(
        """
        SELECT DISTINCT bowler_id
        FROM deliveries
        WHERE bowler_id IS NOT NULL
        """
    ).fetchall()
    return {r[0] for r in rows}


def load_player_attributes(con, csv_path: str = PLAYER_ATTRIBUTES_CSV) -> int:
    """Load data/player_attributes.csv into the player_attributes table.

    Idempotent: clears the table then inserts every CSV row. Empty
    bowling_type / bowling_style cells become NULL; confidence is parsed to
    float. Returns the number of rows inserted.
    """
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        if list(reader.fieldnames) != CSV_HEADER:
            raise ValueError(
                f"player_attributes.csv header {reader.fieldnames!r} "
                f"does not match required {CSV_HEADER!r}"
            )
        records = []
        for row in reader:
            records.append(
                (
                    row["registry_id"].strip(),
                    row["canonical_name"].strip(),
                    row["batting_hand"].strip(),
                    row["bowling_type"].strip() or None,
                    row["bowling_style"].strip() or None,
                    row["source"].strip(),
                    float(row["confidence"]),
                )
            )

    con.execute("DELETE FROM player_attributes")
    if records:
        con.executemany(
            """
            INSERT INTO player_attributes
              (registry_id, canonical_name, batting_hand, bowling_type,
               bowling_style, source, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            records,
        )
    return len(records)


@dataclass
class AttrValidationResult:
    ok: bool
    flags: list[str]
    uncovered_bowlers: list[str]
    n_rows: int


def validate_player_attributes(con) -> AttrValidationResult:
    """Fail-closed validation of the loaded player_attributes table.

    Hard flags (set ok=False):
      - batting_hand not in {RHB, LHB}
      - bowling_type not in {pace, spin} and not NULL
      - confidence outside [0.0, 1.0]
    Separately reports uncovered_bowlers: registry_ids that bowled a ball in
    season 2026 but whose row has NULL bowling_type (or has no row at all).
    The verification gate requires ok AND not uncovered_bowlers.
    """
    flags: list[str] = []

    n_rows = con.execute("SELECT COUNT(*) FROM player_attributes").fetchone()[0]

    bad_hand = con.execute(
        "SELECT registry_id, batting_hand FROM player_attributes "
        "WHERE batting_hand IS NULL OR batting_hand NOT IN ('RHB', 'LHB')"
    ).fetchall()
    for rid, val in bad_hand:
        flags.append(f"batting_hand invalid for {rid}: {val!r}")

    bad_type = con.execute(
        "SELECT registry_id, bowling_type FROM player_attributes "
        "WHERE bowling_type IS NOT NULL AND bowling_type NOT IN ('pace', 'spin')"
    ).fetchall()
    for rid, val in bad_type:
        flags.append(f"bowling_type invalid for {rid}: {val!r}")

    bad_conf = con.execute(
        "SELECT registry_id, confidence FROM player_attributes "
        "WHERE confidence IS NULL OR confidence < 0.0 OR confidence > 1.0"
    ).fetchall()
    for rid, val in bad_conf:
        flags.append(f"confidence out of [0,1] for {rid}: {val!r}")

    uncovered = [
        r[0]
        for r in con.execute(
            """
            SELECT DISTINCT d.bowler_id
            FROM deliveries d
            LEFT JOIN player_attributes pa ON pa.registry_id = d.bowler_id
            WHERE d.bowler_id IS NOT NULL
              AND (pa.registry_id IS NULL OR pa.bowling_type IS NULL)
            ORDER BY d.bowler_id
            """
        ).fetchall()
    ]

    ok = not flags and not uncovered
    return AttrValidationResult(
        ok=ok, flags=flags, uncovered_bowlers=uncovered, n_rows=n_rows
    )


def main() -> None:
    """Load data/player_attributes.csv into data/cricket.duckdb and gate it.

    Prints a summary and exits non-zero if the verification gate fails so the
    phase-3 check / CI catches an incomplete or invalid CSV.
    """
    con = connect(read_only=False)
    try:
        n = load_player_attributes(con, PLAYER_ATTRIBUTES_CSV)
        print(f"player_attributes: {n} rows loaded from {PLAYER_ATTRIBUTES_CSV}")
        res = validate_player_attributes(con)
        if res.flags:
            print(f"FLAGS ({len(res.flags)}):")
            for f in res.flags:
                print(f"  - {f}")
        if res.uncovered_bowlers:
            print(f"UNCOVERED BOWLERS ({len(res.uncovered_bowlers)}):")
            for rid in res.uncovered_bowlers:
                print(f"  - {rid}")
        if res.ok:
            print("GATE OK")
        else:
            print("GATE FAILED")
            sys.exit(1)
    finally:
        con.close()


if __name__ == "__main__":
    main()
