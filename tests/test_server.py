"""Endpoint tests for the bespoke web backend (server.py).

Deterministic API only — the SSE /api/ask path (LLM) is excluded. Asserts the
multi-season foundation holds and that 2026 stays pinned to known-good numbers.
"""
from fastapi.testclient import TestClient

from server import app

client = TestClient(app)


def test_filters_has_all_seasons():
    d = client.get("/api/filters").json()
    assert len(d["seasons"]) == 19
    assert d["seasons"][0] == "2026"           # newest first
    assert "Mumbai Indians" in d["teams"]
    assert "Mumbai" in d["venues"]


def test_dashboard_2026_is_pinned():
    d = client.get("/api/dashboard?season=2026").json()
    assert d["kpis"] == {"matches": 70, "runs": 25846, "wickets": 782,
                         "sixes": 1349, "run_rate": 9.86}
    assert d["run_scorers"][0]["player"] == "B Sai Sudharsan"


def test_dashboard_all_time_career_leader():
    d = client.get("/api/dashboard?season=All").json()
    assert d["kpis"]["matches"] == 1239
    assert d["run_scorers"][0]["player"] == "Virat Kohli"
    assert d["run_scorers"][0]["value"] > 9000


def test_dashboard_filters_compose():
    # Mumbai Indians batting vs spin, 2026 — should be a strict subset.
    full = client.get("/api/dashboard?season=2026&team=Mumbai%20Indians").json()
    spin = client.get("/api/dashboard?season=2026&team=Mumbai%20Indians&bowltype=spin").json()
    assert spin["kpis"]["runs"] < full["kpis"]["runs"]


def test_player_resolves_and_profiles():
    d = client.get("/api/player?name=Kohli&season=All").json()
    assert "Kohli" in d["name"]
    assert d["batting"]["runs"] > 9000
    assert len(d["runs_by_season"]) > 5            # multi-season form curve


def test_matchup_resolves_both_names():
    d = client.get("/api/matchup?batter=Kohli&bowler=Bumrah&season=All").json()
    assert d["found"] is True
    assert d["batter"] == "Virat Kohli" and d["bowler"] == "Jasprit Bumrah"
    assert d["stats"]["balls"] > 0


def test_insights_quadrants_have_xy():
    d = client.get("/api/insights?season=2026").json()
    assert d["bowlers"] and all("x" in b and "y" in b for b in d["bowlers"])
    assert d["batters"] and all("x" in b and "y" in b for b in d["batters"])
    assert d["venues"][0]["value"] > 150           # avg 1st-innings score


def test_health_ok():
    d = client.get("/api/health").json()
    assert d["status"] == "ok" and d["db"] is True
    assert d["seasons"] == 19
    assert d["latest_season"] == "2026"
    assert isinstance(d["has_key"], bool)
    assert d["model"]                              # configured model name surfaced


def test_health_reports_missing_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    assert client.get("/api/health").json()["has_key"] is False


def test_health_reports_present_key(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "x")
    assert client.get("/api/health").json()["has_key"] is True
