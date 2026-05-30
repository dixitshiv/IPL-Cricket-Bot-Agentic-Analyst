-- Analytical views over the base tables.
-- Loaded by ingest.load.create_views(). All views exclude super-over deliveries.

-- Names: prefer the enriched canonical_name (2026), else fall back to the
-- match_players roster name so EVERY season has readable names. The fallback
-- is grouped to one row per registry_id to avoid join fan-out.
CREATE OR REPLACE VIEW v_deliveries AS
SELECT d.*,
       m.season,
       (d.runs_batter + d.wides + d.noballs) AS bowler_conceded,
       COALESCE(pb.canonical_name, nb.player_name) AS batter_name,
       pb.batting_hand   AS batter_hand,
       COALESCE(pw.canonical_name, nw.player_name) AS bowler_name,
       pw.bowling_type   AS bowler_type,
       pw.bowling_style  AS bowler_style
FROM deliveries d
JOIN matches m ON m.match_id = d.match_id
LEFT JOIN player_attributes pb ON pb.registry_id = d.batter_id
LEFT JOIN player_attributes pw ON pw.registry_id = d.bowler_id
LEFT JOIN (SELECT registry_id, MAX(player_name) AS player_name FROM match_players
           WHERE registry_id IS NOT NULL GROUP BY registry_id) nb ON nb.registry_id = d.batter_id
LEFT JOIN (SELECT registry_id, MAX(player_name) AS player_name FROM match_players
           WHERE registry_id IS NOT NULL GROUP BY registry_id) nw ON nw.registry_id = d.bowler_id
WHERE d.is_super_over = FALSE;

CREATE OR REPLACE VIEW v_innings AS
SELECT match_id, innings, batting_team, bowling_team,
       SUM(runs_total) AS runs,
       COUNT(*) FILTER (WHERE is_legal_ball) AS legal_balls,
       COUNT(*) FILTER (WHERE player_out IS NOT NULL) AS wickets
FROM deliveries
WHERE is_super_over = FALSE
GROUP BY 1, 2, 3, 4;

CREATE OR REPLACE VIEW v_matches AS
SELECT m.*, COALESCE(m.winner, m.eliminator) AS effective_winner
FROM matches m;
