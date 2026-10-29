"""Production SQLite initialization, online backup, migrations and offline restore."""

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "backend/local"
DB = STATE / "elections.db"
BACKUPS = Path("/backups")


def check(path):
    with closing(
        sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=30)
    ) as connection:
        if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise RuntimeError("SQLite quick_check failed")
        if connection.execute("SELECT count(*) FROM contests").fetchone()[0] == 0:
            raise RuntimeError("Refusing an empty election database")


def backup(label="backup"):
    check(DB)
    BACKUPS.mkdir(parents=True, exist_ok=True)
    path = BACKUPS / f"{label}-{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ')}.db"
    with (
        closing(sqlite3.connect(DB, timeout=30)) as source,
        closing(sqlite3.connect(path)) as target,
    ):
        source.backup(target)
        # A backup must be self-contained, regardless of the live DB's WAL mode.
        target.execute("PRAGMA journal_mode=DELETE")
    check(path)
    path.chmod(0o600)
    print(f"SQLite backup: {path}", flush=True)
    return path


def initialize():
    STATE.mkdir(parents=True, exist_ok=True)
    if not DB.exists():
        seed = Path("/seed/elections.db")
        check(seed)
        shutil.copy2(seed, DB)
        # Retain the last job status and logs from a migration export, if supplied.
        audit = Path('/seed/audit')
        if audit.is_dir():
            shutil.copytree(audit, STATE, dirs_exist_ok=True)
        for path in STATE.rglob('*'):
            os.chown(path, int(os.environ['APP_UID']), int(os.environ['APP_GID']))
        os.chown(DB, int(os.environ["APP_UID"]), int(os.environ["APP_GID"]))
        print("Initialized production volume from retained seed", flush=True)
    check(DB)
    os.chown(STATE, int(os.environ["APP_UID"]), int(os.environ["APP_GID"]))
    STATE.chmod(0o700)


def migrate():
    backup("before-migration")
    with closing(sqlite3.connect(DB, timeout=30)) as connection:
        mode = connection.execute("PRAGMA journal_mode=WAL").fetchone()[0]
        if mode != "wal":
            raise RuntimeError("Production SQLite requires WAL on its Docker volume")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            "backend/alembic.ini",
            "upgrade",
            "head",
        ],
        cwd=ROOT,
        check=True,
    )


def export_migration():
    """Run in the Linux backend container; cooperate with its refresh lock."""
    import fcntl

    destination = BACKUPS / ('windows-transfer-' + datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ'))
    with (STATE / 'early-voting-refresh.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        saved = backup('migration')
        destination.mkdir()
        shutil.copy2(saved, destination / 'elections.db')
        shutil.copytree(ROOT / 'data/raw', destination / 'raw')
        audit = destination / 'audit'
        audit.mkdir()
        status = STATE / 'early-voting-refresh-status.json'
        if status.is_file():
            shutil.copy2(status, audit / status.name)
        if (STATE / 'logs').is_dir():
            shutil.copytree(STATE / 'logs', audit / 'logs')
        manifest = {
            str(path.relative_to(destination)).replace('\\', '/'): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in destination.rglob('*') if path.is_file()
        }
        (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'Migration export: {destination}', flush=True)
    return destination


def restore(path, offline):
    if not offline:
        raise SystemExit("Pause and drain Relay production jobs and stop backend, then pass --offline to restore")
    path = path.resolve()
    check(path)
    backup("before-restore")
    temporary = STATE / "restored.db"
    with (
        closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as source,
        closing(sqlite3.connect(temporary)) as target,
    ):
        source.backup(target)
        target.execute("PRAGMA journal_mode=DELETE")
    check(temporary)
    for suffix in ("-wal", "-shm"):
        Path(str(DB) + suffix).unlink(missing_ok=True)
    temporary.chmod(0o600)
    temporary.replace(DB)
    print("Restored backup; run migrations before restarting services", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=["initialize", "migrate", "backup", "restore", "export"]
    )
    parser.add_argument("--backup", type=Path)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    if args.action == "restore":
        if not args.backup:
            parser.error("restore requires --backup")
        restore(args.backup, args.offline)
    else:
        {"initialize": initialize, "migrate": migrate, "backup": backup, "export": export_migration}[args.action]()
