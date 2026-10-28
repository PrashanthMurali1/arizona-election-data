"""Back up existing local data and prepare a separate, private production seed."""

import fcntl
import hashlib
import json
import shutil
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / ".production"


def backup(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    with (
        closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as src,
        closing(sqlite3.connect(destination)) as dst,
    ):
        src.backup(dst)
        dst.execute("PRAGMA journal_mode=DELETE")
        if dst.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise RuntimeError("Database backup failed SQLite quick_check")
    destination.chmod(0o600)


def main():
    seed = TARGET / "seed/elections.db"
    if seed.exists():
        raise SystemExit(
            "Production seed already exists; refusing to replace it. See production hosting guide."
        )
    source = ROOT / "backend/local/elections.db"
    if not source.is_file():
        raise SystemExit(
            "Existing populated database is required; no bootstrap is performed"
        )
    TARGET.mkdir(mode=0o700, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    retained = TARGET / "backups" / f"before-production-{stamp}"
    # Cooperate with the existing importer while retaining DB + raw responses.
    with (ROOT / "backend/local/early-voting-refresh.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        backup(source, retained / "elections.db")
        shutil.copytree(ROOT / "data/raw", retained / "raw")
        shutil.copytree(retained / "raw", TARGET / "raw")
        seed.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(retained / "elections.db", seed)
    (TARGET / "secrets").mkdir(mode=0o700, exist_ok=True)
    record = {
        "created_at": stamp,
        "source": str(source),
        "backup": str(retained),
        "database_sha256": hashlib.sha256(seed.read_bytes()).hexdigest(),
    }
    (TARGET / "preparation.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
