"""Back up existing local data and prepare a separate, private production seed."""

import argparse
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


def prepare_export(source):
    """Import a completed, checksummed export without requiring Unix host APIs."""
    source = source.resolve()
    from production.manage_db import check

    manifest = json.loads((source / 'manifest.json').read_text())
    actual = {p.relative_to(source).as_posix() for p in source.rglob('*') if p.is_file() and p != source / 'manifest.json'}
    if set(manifest) != actual or not {'elections.db'}.issubset(actual) or not (source / 'raw').is_dir():
        raise RuntimeError('Incomplete migration export')
    for name, digest in manifest.items():
        path = (source / name).resolve()
        if not path.is_relative_to(source) or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise RuntimeError('Migration export checksum mismatch')
    check(source / 'elections.db')
    if TARGET.exists():
        raise SystemExit('Production directory already exists; retain it and use a fresh checkout for import')
    TARGET.mkdir(mode=0o700)
    seed = TARGET / 'seed'
    seed.mkdir()
    backup(source / 'elections.db', seed / 'elections.db')
    shutil.copytree(source / 'raw', TARGET / 'raw')
    if (source / 'audit').is_dir():
        shutil.copytree(source / 'audit', seed / 'audit')
    (TARGET / 'backups').mkdir()
    (TARGET / 'secrets').mkdir(mode=0o700)
    (TARGET / 'preparation.json').write_text(json.dumps({'source': str(source), 'manifest': manifest}, indent=2) + '\n')
    print('Verified export imported. No containers or tunnel started.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--from-export', type=Path, help='Completed manage_db.py export directory')
    args = parser.parse_args()
    if args.from_export:
        # Direct script invocation otherwise puts only scripts/ on sys.path.
        import sys
        sys.path.insert(0, str(ROOT))
        prepare_export(args.from_export)
        return
    if __import__('os').name == 'nt':
        raise SystemExit('On Windows use --from-export with a completed Mac production export; do not seed from stale host data')
    import fcntl

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
