# ingest/flatten.py
"""Flatten Cricsheet match JSON into table-shaped row dicts.

Pure functions only: no DuckDB, no I/O. `flatten_match` returns row dicts
whose keys match the columns declared in ingest/schema.sql exactly.
"""
from __future__ import annotations

import math

from core.config import DEATH_OVER_START


def is_legal(extras: dict) -> bool:
    """A delivery is legal unless it carried a wide or a no-ball.

    Byes, legbyes, and penalty runs do NOT make a ball illegal.
    """
    return not ("wides" in extras or "noballs" in extras)


def assign_phase(over: int, powerplays: list[dict]) -> str:
    """Classify a 0-indexed over into 'powerplay' | 'middle' | 'death'.

    Powerplay is taken from the file's explicit powerplays[] array, whose
    `from`/`to` are over.ball decimals; we floor them to over numbers.
    Otherwise: 'death' for over >= DEATH_OVER_START, else 'middle'.
    """
    for pp in powerplays:
        if math.floor(pp["from"]) <= over <= math.floor(pp["to"]):
            return "powerplay"
    if over >= DEATH_OVER_START:
        return "death"
    return "middle"


def _registry(raw: dict) -> dict[str, str]:
    """name -> registry_id map from info.registry.people (may be empty)."""
    return raw.get("info", {}).get("registry", {}).get("people", {})


def _to_id(name: str | None, registry: dict[str, str]) -> str | None:
    """Resolve a player name to its registry id; None if absent."""
    if name is None:
        return None
    return registry.get(name)


def _flatten_match_row(raw: dict, match_id: int) -> dict:
    info = raw["info"]
    teams = info["teams"]
    outcome = info.get("outcome", {})
    by = outcome.get("by", {})
    pom = info.get("player_of_match") or []
    # super-over match = more than the standard two innings.
    is_super_over_match = len(raw.get("innings", [])) > 2
    dates = info.get("dates") or [None]
    event = info.get("event") or {}
    toss = info.get("toss") or {}
    return {
        "match_id": match_id,
        "match_date": dates[0],
        "season": str(info["season"]),
        "event_name": event.get("name"),
        "match_number": event.get("match_number"),
        "venue": info.get("venue"),
        "city": info.get("city"),
        "team_a": teams[0],
        "team_b": teams[1],
        "toss_winner": toss.get("winner"),
        "toss_decision": toss.get("decision"),
        "winner": outcome.get("winner"),          # None for tie / no-result
        "outcome_by_runs": by.get("runs"),
        "outcome_by_wickets": by.get("wickets"),
        "eliminator": outcome.get("eliminator"),  # super-over winner else None
        "result": outcome.get("result"),
        "method": outcome.get("method"),
        "player_of_match": pom[0] if pom else None,
        "is_super_over_match": is_super_over_match,
    }


def _flatten_players(raw: dict, match_id: int) -> list[dict]:
    info = raw["info"]
    registry = _registry(raw)
    rows: list[dict] = []
    for team, names in info.get("players", {}).items():
        for name in names:
            rows.append(
                {
                    "match_id": match_id,
                    "team": team,
                    "player_name": name,
                    "registry_id": registry.get(name),
                }
            )
    return rows


def _flatten_deliveries(raw: dict, match_id: int) -> list[dict]:
    registry = _registry(raw)
    teams = raw["info"]["teams"]
    rows: list[dict] = []
    for idx, inn in enumerate(raw.get("innings", []), start=1):
        batting_team = inn["team"]
        bowling_team = teams[1] if batting_team == teams[0] else teams[0]
        powerplays = inn.get("powerplays", [])
        # innings beyond the standard two are super-over innings.
        is_super_over = idx > 2
        for over_obj in inn.get("overs", []):
            over = over_obj["over"]
            phase = assign_phase(over, powerplays)
            for pos, d in enumerate(over_obj["deliveries"], start=1):
                extras = d.get("extras", {})
                runs = d["runs"]
                wickets = d.get("wickets") or []
                # Only the first wicket on a delivery is recorded — a known,
                # accepted v1 limitation.  The IPL 2026 corpus has zero
                # multi-wicket deliveries, so this is safe; full fidelity
                # would require a separate wickets child table.
                first_wkt = wickets[0] if wickets else {}
                player_out_name = first_wkt.get("player_out")
                rows.append(
                    {
                        "match_id": match_id,
                        "innings": idx,
                        "batting_team": batting_team,
                        "bowling_team": bowling_team,
                        "over": over,
                        "ball": pos,
                        "batter_id": _to_id(d.get("batter"), registry),
                        "bowler_id": _to_id(d.get("bowler"), registry),
                        "non_striker_id": _to_id(d.get("non_striker"), registry),
                        "runs_batter": runs["batter"],
                        "runs_extras": runs["extras"],
                        "runs_total": runs["total"],
                        "wides": extras.get("wides", 0),
                        "noballs": extras.get("noballs", 0),
                        "byes": extras.get("byes", 0),
                        "legbyes": extras.get("legbyes", 0),
                        "penalty": extras.get("penalty", 0),
                        "is_legal_ball": is_legal(extras),
                        "phase": phase,
                        "wicket_kind": first_wkt.get("kind"),
                        "player_out": _to_id(player_out_name, registry),
                        "is_super_over": is_super_over,
                    }
                )
    return rows


def flatten_match(raw: dict, match_id: int) -> dict:
    """Flatten one Cricsheet match into table-shaped row dicts.

    Returns {"match": dict, "deliveries": list[dict], "players": list[dict]}
    whose keys match the columns in ingest/schema.sql exactly.
    """
    return {
        "match": _flatten_match_row(raw, match_id),
        "deliveries": _flatten_deliveries(raw, match_id),
        "players": _flatten_players(raw, match_id),
    }
