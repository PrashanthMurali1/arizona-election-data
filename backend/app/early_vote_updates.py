"""Local, cross-process notifications using the importer's committed job audit.

No civicAPI requests are made here. The job writes its finished status only after
all import transactions have exited; each API worker can observe that same file.
"""

import asyncio
import hashlib
import json
import time
from pathlib import Path

from .database import SessionLocal
from .lifecycle import activity, CONTEST

STATUS = Path(__file__).resolve().parents[2] / "backend/local/early-voting-refresh-status.json"


def revision(value):
    # Include successful retrievals and failure attempts, so source dates/status
    # update even when the provider's counts and report date have not changed.
    content = {"releases": value["releases"], "failures": value["failures"]}
    # Staleness depends on wall time, not on an import or stored data revision.
    content["releases"] = [{k: v for k, v in row.items() if k != "stale"} for row in content["releases"]]
    return hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()


def current_revision():
    with SessionLocal() as s:
        value = activity(s, CONTEST)
        return revision(value) if value else "unavailable"


def finished_job():
    try:
        value = json.loads(STATUS.read_text())
        return value.get("finished_at") if value.get("status") in {"success", "failed"} else None
    except (OSError, ValueError):
        return None


async def events(request):
    # Read the marker before the revision to catch commits racing connection setup.
    marker = await asyncio.to_thread(finished_job)
    previous = None
    heartbeat = time.monotonic()
    check_revision = True
    while not await request.is_disconnected():
        if check_revision:
            value = await asyncio.to_thread(current_revision)
            if value != previous:
                yield f"retry: 5000\nid: {value}\nevent: revision\ndata: {json.dumps({'revision': value})}\n\n"
                previous = value
            check_revision = False
        if time.monotonic() - heartbeat >= 15:
            yield ": keep-alive\n\n"
            heartbeat = time.monotonic()
        await asyncio.sleep(1)
        latest = await asyncio.to_thread(finished_job)
        if latest is not None and latest != marker:
            marker = latest
            check_revision = True
