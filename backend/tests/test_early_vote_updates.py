"""Committed-job SSE notifications; retained fixtures, no network acquisitions."""

import asyncio
import copy
import json
from datetime import datetime, timezone

from test_2026_providers import client
from backend.app import early_vote_updates as updates
from backend.app.database import SessionLocal
from backend.app.lifecycle import EVENT
from backend.app.models import CurrentSnapshot
from scripts.early_vote_runtime import run_refresh


def test_revision_is_canonical_only_and_tracks_retrieval_and_failures(client):
    canonical = client.get("/api/elections/az-2026-early-voting/activity").json()
    legacy = client.get("/api/elections/az-2026-governor/activity").json()
    assert "revision" not in legacy
    assert canonical.pop("revision") == updates.revision(legacy)
    assert updates.current_revision() == updates.revision(legacy)
    changed = copy.deepcopy(legacy)
    changed["releases"][0]["retrieved_at"] = "2026-10-28T10:00:00+00:00"
    assert updates.revision(changed) != updates.revision(legacy)
    changed = copy.deepcopy(legacy)
    changed["releases"][0]["stale"] = not changed["releases"][0]["stale"]
    assert updates.revision(changed) == updates.revision(legacy)
    changed["failures"].append({"stream": "early-vote-returned", "error": "Synthetic failure"})
    assert updates.revision(changed) != updates.revision(legacy)


def test_finished_marker_is_published_after_import_callback_commits(client, tmp_path, monkeypatch):
    status = tmp_path / "early-voting-refresh-status.json"
    monkeypatch.setattr(updates, "STATUS", status)
    assert updates.finished_job() is None
    key = (EVENT, "early-vote-returned")
    before = updates.current_revision()
    with SessionLocal() as s:
        original = s.get(CurrentSnapshot, key).checked_at

    def importer():
        assert updates.finished_job() is None  # Still running: cannot notify yet.
        with SessionLocal.begin() as s:
            s.get(CurrentSnapshot, key).checked_at = datetime.now(timezone.utc).isoformat()
            s.flush()
            # The separate API connection sees no uncommitted data.
            assert updates.current_revision() == before
        assert updates.current_revision() != before
        assert updates.finished_job() is None
        return 0

    assert run_refresh(importer, local=tmp_path) == 0
    assert updates.finished_job() == json.loads(status.read_text())["finished_at"]
    assert run_refresh(lambda: 1, local=tmp_path) == 1
    assert updates.finished_job() == json.loads(status.read_text())["finished_at"]
    with SessionLocal.begin() as s:
        s.get(CurrentSnapshot, key).checked_at = original


def test_stream_initial_catchup_completed_jobs_deduplication_and_disconnect(monkeypatch):
    state = {"job": None, "revision": "initial", "checks": 0, "disconnect": False}

    def current():
        state["checks"] += 1
        return state["revision"]

    monkeypatch.setattr(updates, "current_revision", current)
    monkeypatch.setattr(updates, "finished_job", lambda: state["job"])

    class Request:
        async def is_disconnected(self):
            return state["disconnect"]

    async def exercise():
        stream = updates.events(Request())
        assert '"revision": "initial"' in await anext(stream)
        state.update(job="finished-1", revision="committed")
        assert '"revision": "committed"' in await anext(stream)
        # Unchanged audit marker does not query the DB, even over several ticks.
        checks = state["checks"]
        task = asyncio.create_task(anext(stream))
        await asyncio.sleep(2.1)
        assert state["checks"] == checks
        state.update(job="finished-2", revision="committed")
        await asyncio.sleep(1.1)
        assert state["checks"] == checks + 1  # Same revision: no duplicate event.
        state.update(job="finished-3", revision="newest")
        assert '"revision": "newest"' in await asyncio.wait_for(task, 2)
        state["disconnect"] = True
        try:
            await anext(stream)
            assert False, "Disconnected client still streaming"
        except StopAsyncIteration:
            pass
        state["disconnect"] = False
        reconnected = updates.events(Request())
        assert '"revision": "newest"' in await anext(reconnected)
        await reconnected.aclose()

    asyncio.run(exercise())
