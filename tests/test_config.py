import importlib
import os

import pytest

from core import config


@pytest.fixture(autouse=True)
def _restore_config():
    yield
    importlib.reload(config)


def test_path_and_corpus_constants():
    assert config.DB_PATH == "data/cricket.duckdb"
    assert config.JSON_DIR == "ipl_json"
    assert config.SEASON == "2026"


def test_model_constants_default(monkeypatch):
    # With no env overrides, MODEL falls back to the DeepSeek slug,
    # and ROUTE_MODEL / EXPLAIN_MODEL mirror it.
    monkeypatch.delenv("CRICKET_MODEL", raising=False)
    monkeypatch.delenv("CRICKET_EXPLAIN_MODEL", raising=False)
    import importlib

    reloaded = importlib.reload(config)
    assert reloaded.MODEL == "deepseek/deepseek-v4-pro"
    assert reloaded.ROUTE_MODEL == reloaded.MODEL
    assert reloaded.EXPLAIN_MODEL == reloaded.MODEL


def test_model_env_overrides(monkeypatch):
    monkeypatch.setenv("CRICKET_MODEL", "some/other-model")
    monkeypatch.setenv("CRICKET_EXPLAIN_MODEL", "cheap/flash")
    import importlib

    reloaded = importlib.reload(config)
    assert reloaded.MODEL == "some/other-model"
    assert reloaded.ROUTE_MODEL == "some/other-model"
    assert reloaded.EXPLAIN_MODEL == "cheap/flash"


def test_route_model_env_override(monkeypatch):
    monkeypatch.setenv("CRICKET_ROUTE_MODEL", "fast/route-model")
    monkeypatch.delenv("CRICKET_MODEL", raising=False)
    import importlib

    reloaded = importlib.reload(config)
    assert reloaded.ROUTE_MODEL == "fast/route-model"


def test_render_and_threshold_constants():
    assert config.VL_SCHEMA == "https://vega.github.io/schema/vega-lite/v5.json"
    assert config.MIN_LEGAL_BALLS == 10
    assert config.DEATH_OVER_START == 15
    assert config.APP_URL == "https://github.com/local/cricket-nl"
    assert config.APP_TITLE == "Cricket NL"
