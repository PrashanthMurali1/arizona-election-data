"""SQLite online backup/offline restore use disposable technical databases."""

import sqlite3
from contextlib import closing

import pytest
from test_pipeline_api import ROOT  # noqa: F401 -- establishes the isolated test environment

from production import manage_db


def test_backup_and_restore_preserve_committed_wal_and_rollback_copy(
    tmp_path, monkeypatch
):
    state = tmp_path / "state"
    state.mkdir()
    db = state / "elections.db"
    monkeypatch.setattr(manage_db, "STATE", state)
    monkeypatch.setattr(manage_db, "DB", db)
    monkeypatch.setattr(manage_db, "BACKUPS", tmp_path / "backups")
    with closing(sqlite3.connect(db)) as c:
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("CREATE TABLE contests (id TEXT)")
        c.execute("INSERT INTO contests VALUES ('technical-fixture')")
        c.commit()
        saved = manage_db.backup()
        assert not saved.with_name(saved.name + "-wal").exists()
        with closing(
            sqlite3.connect(saved.as_uri() + "?immutable=1", uri=True)
        ) as independent:
            assert (
                independent.execute("SELECT count(*) FROM contests").fetchone()[0] == 1
            )
        c.execute("INSERT INTO contests VALUES ('later-fixture')")
        c.commit()
        with pytest.raises(SystemExit):
            manage_db.restore(saved, False)
    manage_db.restore(saved, True)
    with closing(sqlite3.connect(db)) as c:
        assert c.execute("SELECT id FROM contests").fetchall() == [
            ("technical-fixture",)
        ]
    rollback = next((tmp_path / "backups").glob("before-restore-*.db"))
    with closing(sqlite3.connect(rollback)) as c:
        assert c.execute("SELECT count(*) FROM contests").fetchone()[0] == 2


def test_migration_refuses_missing_database(tmp_path, monkeypatch):
    monkeypatch.setattr(manage_db, "DB", tmp_path / "missing.db")
    with pytest.raises(sqlite3.OperationalError):
        manage_db.backup()
    assert not (tmp_path / "missing.db").exists()
