"""Technical checks for shared early-voting feeds; no election reconciliation."""

import copy
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select

from test_pipeline_api import ROOT
from backend.app.database import SessionLocal
from backend.app.lifecycle import activity, apply_snapshot
from backend.app.models import BoundaryVersion, Contest, GeographicUnit, Geometry, MetricObservation, Office, Participation, PublicationSnapshot, Source, VoteResult
from backend.app.publication_input import SnapshotInput
from scripts.provider_2026 import early_vote_input


def retained(category):
    files = [(p, json.loads(p.read_text())) for p in (ROOT / "data/raw/2026/manifests").glob(f"early-vote-{category}-*.json")]
    # Pin the first retained release so automatic live refreshes do not change fixtures.
    path, payload = min(files, key=lambda row: row[1]["retrieved_at"])
    return path, payload, json.loads((ROOT / payload["source"]["raw_path"]).read_text())


@pytest.fixture(scope="module")
def client():
    # Isolate these tests from unrelated House historical raw-file imports.
    subprocess.run([sys.executable, "-m", "alembic", "-c", "backend/alembic.ini", "upgrade", "head"], cwd=ROOT, check=True)
    features = json.loads((ROOT / "data/geography/az-counties-2022.geojson").read_text())["features"]
    with SessionLocal.begin() as s:
        s.merge(Office(id="governor", name="Governor"))
        s.merge(Office(id="attorney-general", name="Attorney General"))
        s.flush()
        if not s.get(BoundaryVersion, "county-2022"):
            s.add(Source(id="provider-test-geography", title="Retained geography fixture", url="https://www.census.gov/", sha256="", notes="Local technical fixture; no network retrieval"))
            s.flush()
            s.add(BoundaryVersion(id="county-2022", vintage=2022, source_id="provider-test-geography"))
            s.add(GeographicUnit(id="04", name="Arizona", kind="state"))
            for feature in features:
                props = feature["properties"]
                s.add(GeographicUnit(id=props["geoid"], name=props["name"], kind="county"))
            s.flush()
            for feature in features:
                s.add(Geometry(unit_id=feature["properties"]["geoid"], boundary_id="county-2022", feature=feature))
    for category in ("requested", "returned"):
        path, _, _ = retained(category)
        subprocess.run([sys.executable, "scripts/refresh_2026.py", "--manifest", str(path)], cwd=ROOT, check=True, capture_output=True)
    from fastapi.testclient import TestClient
    from backend.app.main import app
    with TestClient(app) as client:
        yield client


def fixture_input(tmp_path, feed):
    raw = tmp_path / "data/raw/synthetic-early-vote.json"
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_text(json.dumps({**feed, "synthetic_fixture": True}))
    meta = dict(url=f"https://civicapi.org/api/v2/early-vote/AZ/{feed['category']}", raw_path="data/raw/synthetic-early-vote.json", sha256=hashlib.sha256(raw.read_bytes()).hexdigest(), retrieved_at=datetime.now(timezone.utc).isoformat())
    return SnapshotInput.model_validate(early_vote_input(feed, meta, feed["category"]))


def test_shared_reports_populate_both_pages_without_candidates(client):
    activities = [client.get(f"/api/elections/az-2026-{office}/activity").json() for office in ("governor", "attorney-general")]
    for a in activities:
        assert a["stage"] == "pre_results"
        assert a["provider_report"] is None
        assert a["provider_participation"]["provider"] == "civicAPI"
        assert a["coverage"]["ballots_requested"] == a["coverage"]["ballots_received"] == 15
        assert a["coverage"]["in_person_early"] == a["coverage"]["registered_voters"] == 0
        state = {m["key"]: m["value"] for m in a["statewide"]["metrics"]}
        assert state["ballots_requested"] == 3289914
        assert state["ballots_received"] == 1143275
        assert state["ballots_received__democratic"] == 430622
        assert state["registered_voters"] is None
        assert len(a["releases"]) == len(a["sources"]) == 2
        assert all(r["reported_at"] == "2026-10-27" and r["report_precision"] == "date" for r in a["releases"])
    assert activities[0]["releases"] == activities[1]["releases"]
    assert activities[0]["counties"] == activities[1]["counties"]
    for office in ("governor", "attorney-general"):
        detail = client.get(f"/api/elections/az-2026-{office}").json()
        assert detail["statewide"]["candidates"] == []
        assert detail["statewide"]["total_votes"] is None
        assert all(row["winner"] is None and not row["candidates"] for row in client.get(f"/api/elections/az-2026-{office}/counties").json())
        shared_ids = {r["id"] for r in activities[0]["releases"]}
        assert shared_ids <= {r["id"] for r in client.get(f"/api/elections/az-2026-{office}/snapshots").json()}


def test_single_catalog_view_reuses_existing_event_records(client):
    models = (Contest, PublicationSnapshot, MetricObservation, Participation, VoteResult)
    with SessionLocal() as s:
        before = [s.scalar(select(func.count()).select_from(m)) for m in models]
    entries = [e for e in client.get("/api/elections").json() if e["year"] == 2026]
    assert len(entries) == 1
    assert entries[0]["id"] == "az-2026-early-voting"
    assert entries[0]["office_id"] == "early-voting" and entries[0]["office"] == "Early Voting"
    detail = client.get("/api/elections/az-2026-early-voting").json()
    assert detail["election"]["id"] == entries[0]["id"]
    assert detail["statewide"]["candidates"] == []
    canonical = client.get("/api/elections/az-2026-early-voting/activity").json()
    assert canonical.pop("revision")
    assert canonical == client.get("/api/elections/az-2026-governor/activity").json()
    assert len(client.get("/api/elections/az-2026-early-voting/counties").json()) == 15
    assert len(client.get("/api/elections/az-2026-early-voting/snapshots").json()) == 2
    with SessionLocal() as s:
        assert [s.scalar(select(func.count()).select_from(m)) for m in models] == before


def test_replay_does_not_duplicate_shared_observations(client):
    _, payload, _ = retained("requested")
    data = SnapshotInput.model_validate(payload)
    with SessionLocal() as s:
        models = (PublicationSnapshot, MetricObservation, Participation, VoteResult)
        before = [s.scalar(select(func.count()).select_from(m)) for m in models]
        first = apply_snapshot(s, data)
        second = apply_snapshot(s, data.model_copy(update={"retrieved_at": datetime.now(timezone.utc).isoformat()}))
        assert first["snapshot_id"] == second["snapshot_id"]
        assert not first["created"] and not second["created"]
        assert [s.scalar(select(func.count()).select_from(m)) for m in models] == before


def test_partial_source_zero_and_missing_are_displayed_without_reconciliation(client, tmp_path):
    feed = {"state": "AZ", "category": "requested", "snapshot_date": "2026-10-27", "statewide_total": {"Democratic": {"votes": 7}, "Other": {"votes": 8}}, "regions": {"Apache": {"Democratic": {"votes": 0}, "Other": {"votes": None}}}}
    data = fixture_input(tmp_path, feed)
    with SessionLocal() as s:
        outcome = apply_snapshot(s, data, root=tmp_path)
        assert outcome["advanced"] and not outcome["warnings"]
        a = activity(s, "az-2026-governor")
        state = {m["key"]: m["value"] for m in a["statewide"]["metrics"]}
        assert state["ballots_requested"] == 15  # Uses the state block, never county sums.
        apache = next(c for c in a["counties"] if c["geoid"] == "04001")
        values = {m["key"]: m["value"] for m in apache["metrics"]}
        assert values["ballots_requested__democratic"] == 0
        assert values["ballots_requested__other"] is None
        assert values["ballots_requested"] is None
        assert a["coverage"]["ballots_requested"] == 0


def test_older_category_snapshot_keeps_newer_values(client, tmp_path):
    _, _, feed = retained("requested")
    feed["snapshot_date"] = "2026-10-26"
    data = fixture_input(tmp_path, feed)
    with SessionLocal() as s:
        before = activity(s, "az-2026-governor")["statewide"]
        outcome = apply_snapshot(s, data, root=tmp_path)
        assert not outcome["advanced"]
        assert activity(s, "az-2026-governor")["statewide"] == before


def test_category_and_snapshot_binding(client, tmp_path):
    _, payload, feed = retained("returned")
    wrong = copy.deepcopy(feed)
    wrong["state"] = "CA"
    with pytest.raises(ValueError, match="Arizona"):
        early_vote_input(wrong, payload["source"], "returned")
    data = fixture_input(tmp_path, feed)
    (tmp_path / data.source.raw_path).write_text("altered response bytes")
    with SessionLocal() as s, pytest.raises(ValueError, match="checksum"):
        apply_snapshot(s, data, root=tmp_path)
