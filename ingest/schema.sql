-- Base schema for the cricket NL analytics DuckDB database.
-- One file = one source of truth for the four base tables.
-- Loaded by ingest.load.create_schema(). NO views here (see ingest/views.sql).

CREATE TABLE IF NOT EXISTS matches (
    match_id            INTEGER PRIMARY KEY,
    match_date          DATE,
    season              VARCHAR,
    event_name          VARCHAR,
    match_number        INTEGER,
    venue               VARCHAR,
    city                VARCHAR,
    team_a              VARCHAR,
    team_b              VARCHAR,
    toss_winner         VARCHAR,
    toss_decision       VARCHAR,
    winner              VARCHAR,          -- NULL for tie/no-result
    outcome_by_runs     INTEGER,
    outcome_by_wickets  INTEGER,
    eliminator          VARCHAR,          -- super-over winner else NULL
    result              VARCHAR,
    method              VARCHAR,
    player_of_match     VARCHAR,
    is_super_over_match BOOLEAN
);

CREATE TABLE IF NOT EXISTS deliveries (
    match_id      INTEGER,
    innings       INTEGER,                -- 1-based enumeration order
    batting_team  VARCHAR,
    bowling_team  VARCHAR,
    over          INTEGER,                -- 0-indexed
    ball          INTEGER,                -- 1-based position in over
    batter_id     VARCHAR,
    bowler_id     VARCHAR,
    non_striker_id VARCHAR,
    runs_batter   INTEGER,
    runs_extras   INTEGER,
    runs_total    INTEGER,
    wides         INTEGER DEFAULT 0,
    noballs       INTEGER DEFAULT 0,
    byes          INTEGER DEFAULT 0,
    legbyes       INTEGER DEFAULT 0,
    penalty       INTEGER DEFAULT 0,
    is_legal_ball BOOLEAN,                -- wides=0 AND noballs=0
    phase         VARCHAR,
    wicket_kind   VARCHAR,
    player_out    VARCHAR,                -- registry_id dismissed, else NULL
    is_super_over BOOLEAN
);

CREATE TABLE IF NOT EXISTS match_players (
    match_id    INTEGER,
    team        VARCHAR,
    player_name VARCHAR,
    registry_id VARCHAR
);

CREATE TABLE IF NOT EXISTS player_attributes (
    registry_id    VARCHAR PRIMARY KEY,
    canonical_name VARCHAR,
    batting_hand   VARCHAR,               -- RHB|LHB
    bowling_type   VARCHAR,               -- pace|spin|NULL
    bowling_style  VARCHAR,
    source         VARCHAR,
    confidence     DOUBLE
);
