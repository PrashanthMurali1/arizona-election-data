"""Scheduled 2026 midterm results refresh (Relay entry point, every 30 minutes).

Fetches every Arizona race from civicAPI's race search, retains the raw response and publishes the
normalized snapshot and legislative district boundaries that the API serves. The database is not
touched. A failed run leaves the previous snapshot in place and exits non-zero.
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
