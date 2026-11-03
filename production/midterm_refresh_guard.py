"""Read-only Relay preflight: require the SQLite-serving release and additive schema.

Does not migrate, initialize, seed, fetch results, or open SQLite in writable mode. An empty
new table is ready for its first scheduled ingestion. Missing prerequisites fail closed.
"""
import ast
import os
import sqlite3
from contextlib import closing
from pathlib import Path

from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_COLUMNS = {
    "id", "election_date", "race_id", "office", "payload", "revision", "retrieved_at",
    "source_url", "raw_sha256", "completed", "certified", "attempted_at", "refresh_error",
}


def check_readiness(root=ROOT, database_url=None):
    root = Path(root)
    try:
        if not (root / "backend/app/live_results.py").is_file():
            return False, "persistent_results_release_missing"
        tree = ast.parse((root / "backend/app/midterm.py").read_text(encoding="utf-8"))
        functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
        for name, operation in (("load", "read"), ("refresh", "publish")):
            if name not in functions or not any(
                isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name) and node.func.value.id == "live_results"
                and node.func.attr == operation for node in ast.walk(functions[name])
            ):
                return False, "persistent_results_code_not_ready"
        # Match backend/app/database.py exactly, using the same container environment/path.
        url = make_url(database_url or os.getenv("DATABASE_URL", f"sqlite:///{root / 'backend/local/elections.db'}"))
        if url.get_backend_name() != "sqlite" or not url.database or url.database == ":memory:":
            return False, "persistent_sqlite_required"
        path = Path(url.database).resolve()
        with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=5)) as connection:
            versions = {row[0] for row in connection.execute("SELECT version_num FROM alembic_version")}
            if not versions or versions & {"0001", "0002"}:
                return False, "migration_0003_required"
            columns = {row[1] for row in connection.execute("PRAGMA table_info(live_race_snapshots)")}
            if not REQUIRED_COLUMNS.issubset(columns):
                return False, "live_results_schema_missing"
        return True, "ready"
    except (OSError, ValueError, SyntaxError, sqlite3.Error):
        return False, "readiness_check_failed"


if __name__ == "__main__":
    ready, reason = check_readiness()
    print(reason)
    raise SystemExit(0 if ready else 1)
