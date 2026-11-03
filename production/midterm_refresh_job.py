"""Scheduled 2026 midterm results refresh (Relay entry point, every five minutes).

Fetches every Arizona race from civicAPI's race search, retains the raw response and publishes the
transactional SQLite snapshots and legislative district boundaries. A failed run leaves prior
valid results in place. Relay's existing election-production resource also excludes deployments.
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.observability import configure_logging, emit

STATUS = ROOT / "backend/local/midterm-refresh-status.json"


def write_status(**fields):
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    temporary = STATUS.with_name(STATUS.name + ".tmp")
    temporary.write_text(json.dumps(fields, indent=2) + "\n")
    os.replace(temporary, STATUS)


def main():
    # OS advisory locks release automatically on process death (unlike a running status marker).
    # Production runs on Linux; Windows uses its equivalent for local validation.
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    with STATUS.with_suffix(".lock").open("a+") as lock:
        try:
            if os.name == "nt":
                import msvcrt
                lock.seek(0)
                lock.write(" ")
                lock.flush()
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            emit(logging.WARNING, "midterm_refresh_skipped", outcome="lock_held")
            return 0  # another authorized refresh already owns publication
        return run()


def run():
    configure_logging('refresh')
    started = datetime.now(timezone.utc).isoformat()
    clock = time.monotonic()
    write_status(status="running", started_at=started)
    try:
        from backend.app import midterm
        value = midterm.refresh()
    except Exception as exc:
        write_status(status="failed", started_at=started, finished_at=datetime.now(timezone.utc).isoformat(), error=f"{type(exc).__name__}: {exc}")
        emit(logging.CRITICAL, 'midterm_refresh_failed', exc=exc, outcome='failed')
        return 1
    races = sum(len(items) for items in value["offices"].values())
    write_status(status="success", started_at=started, finished_at=datetime.now(timezone.utc).isoformat(), races=races, raw_sha256=value["raw_sha256"])
    emit(logging.INFO, 'midterm_refresh_succeeded', outcome='success', races=races, duration_ms=round((time.monotonic() - clock) * 1000))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
