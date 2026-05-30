"""DuckDB connection factory. The single place that opens the database file."""

import os

import duckdb

from core.config import DB_PATH


def connect(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    """Open a connection to the DuckDB database at ``DB_PATH``.

    ``DB_PATH`` is a relative path (``"data/cricket.duckdb"``), so it is
    resolved relative to the **current working directory**.  Callers must
    therefore run with cwd set to the repository root (e.g. ``uv run`` from
    the repo root) to get the expected file location.

    For writable connections the parent directory is created if missing.
    With ``read_only=True`` the file must already exist (DuckDB raises otherwise),
    which is the desired fail-closed behavior for query-time access.
    """
    if not read_only:
        parent = os.path.dirname(DB_PATH)
        if parent:
            os.makedirs(parent, exist_ok=True)
    return duckdb.connect(DB_PATH, read_only=read_only)
