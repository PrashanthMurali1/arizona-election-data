"""Historical Senate source, identity, reconciliation and isolation checks."""

import copy
import hashlib
import json
import subprocess
import sys

import pytest
from sqlalchemy import func, select

# Reuse the same clean migrated database and offline bootstrap fixture.
from test_pipeline_api import ROOT, client
from backend.app.database import SessionLocal
from backend.app.models import Contest, ElectionEvent, Participation, Turnout, VoteResult
from scripts.import_data import reconcile
from scripts.normalize_us_senate import normalize
from scripts.senate_sources import verify_provenance

EXPECTED = {
    2016: (11, 8, 2530730, "John McCain", 1359267),
    2018: (10, 7, 2384308, "Kyrsten Sinema", 1191100),
    2020: (19, 17, 3355317, "Mark Kelly", 1716467),
    2022: (11, 8, 2572294, "Mark Kelly", 1322027),
    2024: (10, 7, 3348814, "Ruben Gallego", 1676335),
}


def contest_id(year):
    return f"az-{year}-us-senate" + ("-special" if year == 2020 else "")


@pytest.mark.parametrize("year", EXPECTED)
def test_senate_complete_official_results(client, year):
    count, write_ins, total, winner, winner_votes = EXPECTED[year]
    id = contest_id(year)
    detail = client.get(f"/api/elections/{id}").json()
    election, state = detail["election"], detail["statewide"]
    assert election["status"] == "verified"
    assert election["candidate_count"] == count and election["county_count"] == 15
    assert election["kind"] == ("special" if year == 2020 else "general")
    assert state["total_votes"] == total
    assert (state["winner"]["name"], state["winner"]["votes"]) == (winner, winner_votes)
    assert sum(c["write_in"] for c in state["candidates"]) == write_ins
    assert len(state["candidates"]) == count
    report = detail["reconciliation"]
    assert report["status"] == "verified"
    assert not report["missing_candidates"] and not report["unexpected_candidates"]
    assert len(report["candidates"]) == count
    assert all(c["difference"] == 0 and not c["missing_counties"] and not c["county_reference_mismatches"] and c["candidate_metadata_matches_reference"] for c in report["candidates"])
    rows = client.get(f"/api/elections/{id}/counties").json()
    assert {c["geoid"] for c in rows} == {f"04{i:03}" for i in [1,3,5,7,9,11,12,13,15,17,19,21,23,25,27]}
    assert sum(c["total_votes"] for c in rows) == total
    for c in rows:
        assert len(c["candidates"]) == count
        assert all(type(v["votes"]) is int for v in c["candidates"])
        assert sum(v["percent"] for v in c["candidates"]) == pytest.approx(100)
        assert c["turnout"]["ballots_cast"] is not None
        assert client.get(f"/api/elections/{id}/counties/{c['geoid']}").json() == c
    for candidate in state["candidates"]:
        assert sum(next(v["votes"] for v in c["candidates"] if v["id"] == candidate["id"]) for c in rows) == candidate["votes"]
    assert sum(c["turnout"]["ballots_cast"] for c in rows) == state["turnout"]["ballots_cast"]
    assert sum(c["turnout"]["registered_voters"] for c in rows) == state["turnout"]["registered_voters"]


def test_senate_calendar_shared_events_and_absent_2026(client):
    catalog = client.get("/api/elections").json()
    assert {e["id"] for e in catalog if e["office_id"] == "us-senate"} == {contest_id(y) for y in EXPECTED}
    for id in ["az-2014-us-senate", "az-2026-us-senate"]:
        assert client.get(f"/api/elections/{id}").status_code == 404
    with SessionLocal() as s:
        special = s.get(Contest, contest_id(2020))
        assert special.event_id == "az-2020-general"
        assert s.get(ElectionEvent, special.event_id).kind == "general"
        for year in [2018, 2022]:
            assert s.get(Contest, contest_id(year)).event_id == s.get(Contest, f"az-{year}-governor").event_id
            assert s.scalar(select(func.count()).select_from(Turnout).where(Turnout.event_id == f"az-{year}-general")) == 16
    # A missing third-party Mohave row is resolved by an explicit official cell.
    mohave = client.get("/api/elections/az-2018-us-senate/counties/04015").json()
    assert next(c["votes"] for c in mohave["candidates"] if c["name"] == "Jeff Pearce") == 1


def test_senate_sources_normalization_and_missing_zero(client):
    for year in EXPECTED:
        provenance = verify_provenance(ROOT / f"data/raw/us-senate/{year}-provenance.json")
        path = ROOT / f"data/processed/us-senate/{contest_id(year)}.json"
        before = path.read_bytes()
        assert normalize(ROOT / f"data/raw/us-senate/{year}-transcription.csv").read_bytes() == before
        data = json.loads(before)
        assert reconcile(data, ROOT / data["reference_path"])["status"] == "verified"
        assert len(data["candidates"]) == provenance["candidate_count"]
    data = json.loads((ROOT / "data/processed/us-senate/az-2024-us-senate.json").read_text())
    missing = copy.deepcopy(data)
    missing["candidates"][-1]["county_votes"]["04001"] = None
    report = reconcile(missing, ROOT / data["reference_path"])
    assert report["status"] == "incomplete"
    assert report["candidates"][-1]["missing_counties"] == ["04001"]
    assert data["candidates"][-1]["county_votes"]["04001"] == 0


def test_senate_scoped_import_idempotence_and_existing_offices(client):
    baseline = json.loads((ROOT / "data/processed/us-senate/validation/existing-office-baseline.json").read_text())
    def existing_hashes():
        return {id: hashlib.sha256(json.dumps([client.get(f"/api/elections/{id}{suffix}").json() for suffix in ["", "/counties"]], sort_keys=True).encode()).hexdigest() for id in baseline}
    def counts():
        with SessionLocal() as s:
            return [s.scalar(select(func.count()).select_from(m)) for m in [Contest, Participation, VoteResult, Turnout]]
    assert existing_hashes() == baseline
    before = counts()
    subprocess.run([sys.executable, "scripts/import_data.py", "--office", "us-senate"], cwd=ROOT, check=True, capture_output=True)
    assert counts() == before
    assert existing_hashes() == baseline


def test_senate_checksum_failure_is_rejected(tmp_path, monkeypatch):
    import scripts.senate_sources as sources
    monkeypatch.setattr(sources, "ROOT", tmp_path)
    raw = tmp_path / "data/raw/source.txt"
    raw.parent.mkdir(parents=True)
    raw.write_text("official snapshot")
    provenance = tmp_path / "provenance.json"
    provenance.write_text(json.dumps({"snapshots": [{"path": "data/raw/source.txt", "sha256": hashlib.sha256(raw.read_bytes()).hexdigest()}]}))
    sources.verify_provenance(provenance)
    raw.write_text("changed bytes")
    with pytest.raises(ValueError, match="checksum mismatch"):
        sources.verify_provenance(provenance)
