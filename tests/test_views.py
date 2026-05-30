from pathlib import Path

import duckdb
import pytest

from core.config import DB_PATH
from core.db import connect
from ingest.load import build_database, create_schema, create_views

REPO_ROOT = Path(__file__).resolve().parents[1]
DB_FILE = REPO_ROOT / DB_PATH


_VIEW_NAMES = {"v_deliveries", "v_innings", "v_matches"}


@pytest.fixture(scope="session")
def db_built():
    """Return the path to data/cricket.duckdb, building it (and its views) only if
    missing or incomplete.

    The shipped DB already has the views, so in the normal case this opens ONLY a
    read-only connection. That matters: other tests (test_server / test_agent)
    import server.py, which holds a process-wide read-only handle on the same file,
    and DuckDB forbids a read-write connection alongside a read-only one in one
    process. So we avoid taking a write lock unless we genuinely must build.
    """
    if not DB_FILE.exists():
        DB_FILE.parent.mkdir(parents=True, exist_ok=True)
        con = connect(read_only=False)
        try:
            create_schema(con)
            build_database(con)
            create_views(con)
        finally:
            con.close()
        return str(DB_FILE)

    # DB present: check (read-only) whether the views exist; only self-heal via a
    # write connection if they are actually missing.
    ro_con = connect(read_only=True)
    try:
        have = {r[0] for r in ro_con.execute(
            "SELECT view_name FROM duckdb_views() WHERE NOT internal").fetchall()}
    finally:
        ro_con.close()
    if not _VIEW_NAMES <= have:
        con = connect(read_only=False)
        try:
            create_views(con)
        finally:
            con.close()

    return str(DB_FILE)


@pytest.fixture()
def ro(db_built):
    """A fresh read-only connection per test."""
    con = connect(read_only=True)
    yield con
    con.close()


# ---------------------------------------------------------------------------
# Task 3.1 — views exist and are queryable
# ---------------------------------------------------------------------------

def test_views_exist_and_are_queryable(ro):
    names = {
        row[0]
        for row in ro.execute(
            "SELECT view_name FROM duckdb_views() WHERE NOT internal"
        ).fetchall()
    }
    assert {"v_deliveries", "v_innings", "v_matches"} <= names
    # Each view must return at least one row from the loaded 2026 corpus.
    assert ro.execute("SELECT COUNT(*) FROM v_deliveries").fetchone()[0] > 0
    assert ro.execute("SELECT COUNT(*) FROM v_innings").fetchone()[0] > 0
    assert ro.execute("SELECT COUNT(*) FROM v_matches").fetchone()[0] > 0


# ---------------------------------------------------------------------------
# Task 3.2 — legal-ball count differs from raw delivery count when wides present
# ---------------------------------------------------------------------------

def test_legal_ball_count_differs_from_raw_when_wides_present(ro):
    # Match 1529311 innings 1 = Lucknow Super Giants batting.
    # Actual data: 128 raw deliveries, 8 wides, 0 noballs → 120 legal balls.
    # (The plan description quotes 239/11/228 which reflects a different file
    # version; the authoritative truth is the loaded DuckDB / raw JSON.)
    raw_deliveries, legal_balls = ro.execute(
        """
        SELECT
            COUNT(*) AS raw_deliveries,
            COUNT(*) FILTER (WHERE is_legal_ball) AS legal_balls
        FROM v_deliveries
        WHERE match_id = 1529311 AND innings = 1
        """
    ).fetchone()
    assert raw_deliveries == 128
    assert legal_balls == 120
    # The whole point: extras inflate the raw count past the legal count.
    assert legal_balls < raw_deliveries
    assert raw_deliveries - legal_balls == 8  # 8 wides, 0 noballs

    # v_innings must report the same legal-ball figure via the FILTER rule.
    vi_legal = ro.execute(
        "SELECT legal_balls FROM v_innings WHERE match_id = 1529311 AND innings = 1"
    ).fetchone()[0]
    assert vi_legal == 120


# ---------------------------------------------------------------------------
# Task 3.3 — bowler_conceded excludes byes + legbyes + penalty
# ---------------------------------------------------------------------------

def _build_inmemory_with_views() -> duckdb.DuckDBPyConnection:
    """Throwaway in-memory DB using the real schema.sql + views.sql."""
    con = duckdb.connect(":memory:")
    con.execute((REPO_ROOT / "ingest" / "schema.sql").read_text())
    con.execute((REPO_ROOT / "ingest" / "views.sql").read_text())
    return con


def test_bowler_conceded_excludes_byes_legbyes_penalty():
    con = _build_inmemory_with_views()
    try:
        _insert_match(con, 99, winner="A", eliminator=None)  # v_deliveries inner-joins matches
        # Ball A: 0 off the bat, but 4 byes + 2 legbyes + 5 penalty conceded.
        # Ball B: 2 off the bat + 1 wide (a legal extra that IS charged).
        con.execute(
            """
            INSERT INTO deliveries (
                match_id, innings, batting_team, bowling_team, over, ball,
                batter_id, bowler_id, non_striker_id,
                runs_batter, runs_extras, runs_total,
                wides, noballs, byes, legbyes, penalty,
                is_legal_ball, phase, wicket_kind, player_out, is_super_over
            ) VALUES
            -- Ball A: is_legal_ball=TRUE is correct — a bye/legbye is a legal,
            -- faced delivery (only wides and no-balls are illegal). The test
            -- verifies that byes/legbyes are excluded from bowler_conceded
            -- even though the ball itself counts as a legal delivery.
            (99, 1, 'A', 'B', 0, 1, 'bat1', 'bowl1', 'bat2',
             0, 11, 11, 0, 0, 4, 2, 5, TRUE,  'powerplay', NULL, NULL, FALSE),
            (99, 1, 'A', 'B', 0, 2, 'bat1', 'bowl1', 'bat2',
             2, 1,  3,  1, 0, 0, 0, 0, FALSE, 'powerplay', NULL, NULL, FALSE)
            """
        )
        rows = con.execute(
            """
            SELECT ball, bowler_conceded
            FROM v_deliveries
            WHERE match_id = 99
            ORDER BY ball
            """
        ).fetchall()
        conceded = dict(rows)
        # Ball A: byes(4) + legbyes(2) + penalty(5) are NOT the bowler's;
        # runs_batter(0) + wides(0) + noballs(0) = 0.
        assert conceded[1] == 0
        # Ball B: runs_batter(2) + wides(1) + noballs(0) = 3 — wides ARE charged.
        assert conceded[2] == 3
    finally:
        con.close()


# ---------------------------------------------------------------------------
# Task 3.4 — phase assignment matches the explicit powerplays for 1529311
# ---------------------------------------------------------------------------

def _expected_phase(over: int) -> str:
    if over <= 5:          # floor(0.1)=0 .. floor(5.7)=5  (or default T20 PP)
        return "powerplay"
    if over >= 15:         # DEATH_OVER_START
        return "death"
    return "middle"


def test_phase_assignment_matches_explicit_powerplays_for_1529311(ro):
    # Match 1529311: overs 0-5 are powerplay (either via explicit powerplays[]
    # or the default T20 rule applied by assign_phase when no explicit PPs are
    # present). DEATH_OVER_START = 15 => overs >= 15 are death; 6-14 are middle.
    over_phase = {
        (over, phase)
        for over, phase in ro.execute(
            "SELECT DISTINCT over, phase FROM v_deliveries WHERE match_id = 1529311"
        ).fetchall()
    }
    by_over = {}
    for over, phase in over_phase:
        by_over.setdefault(over, set()).add(phase)

    # Each over maps to exactly one phase (no leakage across boundaries).
    for over, phases in by_over.items():
        assert phases == {_expected_phase(over)}, (over, phases)

    # And every phase bucket is actually populated for this match.
    phases_present = {phase for _, phase in over_phase}
    assert phases_present == {"powerplay", "middle", "death"}


# ---------------------------------------------------------------------------
# Task 3.5 — v_deliveries excludes super-over rows
# ---------------------------------------------------------------------------

def test_v_deliveries_excludes_super_over_rows():
    con = _build_inmemory_with_views()
    try:
        _insert_match(con, 77, winner="A", eliminator=None)  # v_deliveries inner-joins matches
        con.execute(
            """
            INSERT INTO deliveries (
                match_id, innings, batting_team, bowling_team, over, ball,
                batter_id, bowler_id, non_striker_id,
                runs_batter, runs_extras, runs_total,
                wides, noballs, byes, legbyes, penalty,
                is_legal_ball, phase, wicket_kind, player_out, is_super_over
            ) VALUES
            (77, 1, 'A', 'B', 0, 1, 'bat1', 'bowl1', 'bat2',
             4, 0, 4, 0, 0, 0, 0, 0, TRUE, 'powerplay', NULL, NULL, FALSE),
            (77, 3, 'A', 'B', 0, 1, 'bat1', 'bowl1', 'bat2',
             6, 0, 6, 0, 0, 0, 0, 0, TRUE, 'powerplay', NULL, NULL, TRUE)
            """
        )
        base_count = con.execute(
            "SELECT COUNT(*) FROM deliveries WHERE match_id = 77"
        ).fetchone()[0]
        view_rows = con.execute(
            "SELECT innings, is_super_over FROM v_deliveries WHERE match_id = 77"
        ).fetchall()

        assert base_count == 2  # base table keeps both rows
        assert view_rows == [(1, False)]  # view drops the super-over ball
    finally:
        con.close()


# ---------------------------------------------------------------------------
# Task 3.6 — v_matches.effective_winner uses eliminator when winner is NULL
# ---------------------------------------------------------------------------

def _insert_match(con, match_id, winner, eliminator):
    con.execute(
        """
        INSERT INTO matches (
            match_id, match_date, season, event_name, match_number,
            venue, city, team_a, team_b, toss_winner, toss_decision,
            winner, outcome_by_runs, outcome_by_wickets, eliminator,
            result, method, player_of_match, is_super_over_match
        ) VALUES (
            ?, DATE '2026-04-01', '2026', 'IPL', 1,
            'V', 'C', 'A', 'B', 'A', 'bat',
            ?, NULL, NULL, ?,
            NULL, NULL, NULL, ?
        )
        """,
        [match_id, winner, eliminator, eliminator is not None],
    )


def test_effective_winner_uses_eliminator_when_winner_null():
    con = _build_inmemory_with_views()
    try:
        _insert_match(con, 1, winner="A", eliminator=None)        # normal win
        _insert_match(con, 2, winner=None, eliminator="B")        # tie -> super over
        _insert_match(con, 3, winner=None, eliminator=None)       # abandoned
        result = dict(
            con.execute(
                "SELECT match_id, effective_winner FROM v_matches ORDER BY match_id"
            ).fetchall()
        )
        assert result[1] == "A"      # winner present -> used directly
        assert result[2] == "B"      # winner NULL -> eliminator path
        assert result[3] is None     # both NULL -> still NULL
    finally:
        con.close()


def test_effective_winner_on_loaded_reconciliation_match(ro):
    # 1529311: PBKS won by 7 wickets, no super over -> winner is used directly.
    eff = ro.execute(
        "SELECT effective_winner FROM v_matches WHERE match_id = 1529311"
    ).fetchone()[0]
    assert eff == "Punjab Kings"
