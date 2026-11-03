import sqlite3
from contextlib import closing

from production.midterm_refresh_guard import check_readiness, REQUIRED_COLUMNS


def release(tmp_path):
    app = tmp_path / "backend/app"
    app.mkdir(parents=True)
    (app / "live_results.py").write_text("")
    (app / "midterm.py").write_text("def load():\n return live_results.read()\ndef refresh():\n live_results.publish()\n")
    return tmp_path / "elections.db"


def database(path, revision="0003", complete=True):
    with closing(sqlite3.connect(path)) as connection:
        connection.execute("CREATE TABLE alembic_version(version_num TEXT)")
        connection.execute("INSERT INTO alembic_version VALUES (?)", (revision,))
        if complete:
            connection.execute("CREATE TABLE live_race_snapshots(" + ",".join(f'"{name}" TEXT' for name in REQUIRED_COLUMNS) + ")")
        connection.commit()


def test_old_release_and_missing_database_fail_without_creating_files(tmp_path):
    assert check_readiness(tmp_path)[0] is False
    path = release(tmp_path)
    assert check_readiness(tmp_path, f"sqlite:///{path}")[0] is False
    assert not path.exists()


def test_old_or_partial_schema_fails_closed(tmp_path):
    path = release(tmp_path)
    database(path, revision="0002")
    assert check_readiness(tmp_path, f"sqlite:///{path}") == (False, "migration_0003_required")
    path.unlink()
    database(path, complete=False)
    assert check_readiness(tmp_path, f"sqlite:///{path}") == (False, "live_results_schema_missing")


def test_empty_migrated_database_passes_without_writes(tmp_path):
    path = release(tmp_path)
    database(path)
    before = path.read_bytes()
    assert check_readiness(tmp_path, f"sqlite:///{path}") == (True, "ready")
    assert path.read_bytes() == before
    assert not list(tmp_path.glob("*.db-*"))


def test_live_fallback_or_nonpersistent_database_is_not_ready(tmp_path):
    path = release(tmp_path)
    database(path)
    assert check_readiness(tmp_path, "sqlite:///:memory:")[0] is False
    (tmp_path / "backend/app/midterm.py").write_text("def load():\n return fetch()\ndef refresh():\n pass\n")
    assert check_readiness(tmp_path, f"sqlite:///{path}") == (False, "persistent_results_code_not_ready")


def test_second_refresh_is_skipped_while_the_lock_is_held(monkeypatch, tmp_path):
    from production import midterm_refresh_job as job
    monkeypatch.setattr(job, "STATUS", tmp_path / "status.json")
    calls = []

    def run():
        calls.append("run")
        return job.main()  # a concurrent run while this one holds the lock

    monkeypatch.setattr(job, "run", run)
    assert job.main() == 0
    assert calls == ["run"]
