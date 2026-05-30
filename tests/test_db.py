import duckdb
import pytest

from core import config, db


def test_connect_returns_duckdb_connection(tmp_path, monkeypatch):
    target = tmp_path / "data" / "cricket.duckdb"
    monkeypatch.setattr(db, "DB_PATH", str(target))

    con = db.connect()
    try:
        assert isinstance(con, duckdb.DuckDBPyConnection)
        # The parent directory is created on demand.
        assert target.parent.exists()
        # The connection is usable.
        assert con.execute("SELECT 1").fetchone() == (1,)
    finally:
        con.close()
    # The DB file now exists on disk.
    assert target.exists()


def test_connect_read_only_on_existing_db(tmp_path, monkeypatch):
    target = tmp_path / "data" / "cricket.duckdb"
    monkeypatch.setattr(db, "DB_PATH", str(target))

    # First create the file with a writable connection and a table.
    w = db.connect()
    w.execute("CREATE TABLE t (a INTEGER)")
    w.execute("INSERT INTO t VALUES (42)")
    w.close()

    ro = db.connect(read_only=True)
    try:
        assert ro.execute("SELECT a FROM t").fetchone() == (42,)
        # Writes must be rejected on a read-only connection.
        with pytest.raises(duckdb.Error):
            ro.execute("INSERT INTO t VALUES (1)")
    finally:
        ro.close()


def test_db_path_sourced_from_config():
    assert db.DB_PATH == config.DB_PATH
