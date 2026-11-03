"""Server-sent notifications when the scheduled midterm refresh publishes new results.

Same mechanism as the early-voting stream: the job writes its finished status only after the
snapshot is published, and each API worker observes that one local file. No civicAPI requests are
made here, and idle connections do not read the snapshot.
"""

import asyncio
import json
import time
from pathlib import Path

from . import midterm

STATUS = Path(__file__).resolve().parents[2] / "backend/local/midterm-refresh-status.json"


def finished_job():
    try:
        value = json.loads(STATUS.read_text())
        return value.get("finished_at") if value.get("status") in {"success", "failed"} else None
    except (OSError, ValueError):
        return None


async def events(request):
    # Read the marker before the revision to catch publications racing connection setup.
    marker = await asyncio.to_thread(finished_job)
    previous = None
    heartbeat = time.monotonic()
    check_revision = True
    while not await request.is_disconnected():
        if check_revision:
            value = await asyncio.to_thread(midterm.snapshot_revision)
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
