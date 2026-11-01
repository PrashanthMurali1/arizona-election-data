"""Real migrations and importer on an isolated clean database; no production fixtures."""

import atexit, copy, json, os, subprocess, sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
# Set database URL before importing application modules.
import tempfile

TEST_DIR = tempfile.TemporaryDirectory(prefix="az-election-tests-")
os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(TEST_DIR.name) / "test.db")
from backend.app.database import engine, SessionLocal
# Release pooled handles before TemporaryDirectory's exit cleanup on Windows.
atexit.register(engine.dispose)
from backend.app.models import Contest, Participation, VoteResult, Turnout, ImportRun
from sqlalchemy import select, func
from scripts.import_data import reconcile


@pytest.fixture(scope="module")
def client():
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
    subprocess.run(
        [sys.executable, "scripts/import_data.py"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [sys.executable, "scripts/refresh_2026.py"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    from fastapi.testclient import TestClient
    from backend.app.main import app

    with TestClient(app) as client:
        yield client
    engine.dispose()


def test_clean_migration_and_import(client):
    assert client.get("/api/health").json() == {"status": "ok"}
    catalog = client.get("/api/elections").json()
    assert len(catalog) == 47
    assert len([x for x in catalog if x["office_id"] == "governor"]) == 15
    assert len([x for x in catalog if x["office_id"] == "attorney-general"]) == 8
    assert len([x for x in catalog if x["office_id"] == "early-voting"]) == 1
    assert all(x["id"] != "az-2026-us-senate" for x in catalog)
    assert client.get("/api/elections/az-2026-us-senate").status_code == 404
    result = client.get("/api/elections/az-2022-governor").json()
    assert result["statewide"]["total_votes"] == 2559485
    candidates = result["statewide"]["candidates"]
    assert len(candidates) == 9 and sum(c["write_in"] for c in candidates) == 7
    assert candidates[0]["name"] == "Katie Hobbs"
    assert candidates[0]["votes"] == 1287891
    assert result["reconciliation"]["status"] == "verified"
    assert all(r["difference"] == 0 for r in result["reconciliation"]["candidates"])


def test_15_counties_sources_and_details(client):
    counties = client.get("/api/elections/az-2022-governor/counties").json()
    features = client.get("/api/geography/county-2022").json()["features"]
    assert len(counties) == len(features) == 15
    assert {c["geoid"] for c in counties} == {
        f["properties"]["geoid"] for f in features
    }
    assert counties[0]["name"] == "Maricopa"
    assert sum(r["total_votes"] for r in counties) == 2559485
    for county in counties:
        assert (
            client.get(
                "/api/elections/az-2022-governor/counties/" + county["geoid"]
            ).json()
            == county
        )
        assert len(county["candidates"]) == 9
        assert sum(c["percent"] for c in county["candidates"]) == pytest.approx(100)
    detail = client.get("/api/elections/az-2022-governor/counties/04013").json()
    assert detail["turnout"]["percent"] == 64.17
    assert detail["turnout"]["ballots_cast"] == 1562758
    assert detail["turnout"]["registered_voters"] == 2435397
    assert detail["turnout"]["ballots_cast"] > detail["total_votes"]
    assert len(client.get("/api/elections/az-2022-governor/sources").json()) == 2
    assert client.get("/api/elections/missing").status_code == 404
    assert (
        client.get("/api/elections/az-2022-governor/counties/99999").status_code == 404
    )
    assert client.get("/api/geography/missing").status_code == 404


def test_repeat_import_does_not_duplicate(client):
    def counts():
        with SessionLocal() as s:
            return [
                s.scalar(select(func.count()).select_from(model))
                for model in [Contest, Participation, VoteResult, Turnout]
            ]

    before = counts()
    subprocess.run(
        [sys.executable, "scripts/import_data.py"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    assert counts() == before


def test_missing_and_zero_values(client):
    data = json.loads((ROOT / "data/processed/2022.json").read_text())
    assert reconcile(data)["status"] == "verified"
    omitted = copy.deepcopy(data)
    omitted["candidates"].pop()
    assert reconcile(omitted)["missing_candidates"] == ["Liana West (Write-In)"]
    changed = copy.deepcopy(data)
    changed["candidates"][0]["statewide"] += 1
    assert reconcile(changed)["status"] == "incomplete"
    assert not reconcile(changed)["candidates"][0]["statewide_matches_reference"]
    shifted = copy.deepcopy(data)
    shifted["candidates"][0]["county_votes"]["04001"] += 1
    shifted["candidates"][0]["county_votes"]["04003"] -= 1
    assert reconcile(shifted)["status"] == "incomplete"
    assert reconcile(shifted)["candidates"][0]["county_reference_mismatches"] == [
        "04001",
        "04003",
    ]
    invalid = copy.deepcopy(data)
    invalid["turnout"]["04"]["percent"] = 101
    with pytest.raises(ValueError, match="turnout percent"):
        reconcile(invalid)
    data["candidates"][0]["county_votes"]["04001"] = None
    report = reconcile(data)
    assert report["status"] == "incomplete"
    assert report["candidates"][0]["difference"] == -8870
    assert report["candidates"][0]["missing_counties"] == ["04001"]
    # Genuine published zeros are preserved.
    rows = client.get("/api/elections/az-2022-governor/counties/04001").json()[
        "candidates"
    ]
    assert any(r["votes"] == 0 and r["percent"] == 0 for r in rows)


def test_partial_contest_withholds_conclusions(client):
    with SessionLocal.begin() as s:
        row = s.scalar(
            select(VoteResult)
            .join(Participation)
            .where(
                Participation.contest_id == "az-2022-governor",
                VoteResult.unit_id == "04013",
                VoteResult.votes > 100000,
            )
        )
        original = row.votes
        rid = row.id
        row.votes = None
        row.status = "unavailable"
    try:
        r = client.get("/api/elections/az-2022-governor/counties/04013").json()
        assert r["winner"] is None and r["total_votes"] is None
        assert all(c["percent"] is None for c in r["candidates"])
        assert any(c["votes"] is None for c in r["candidates"])
    finally:
        with SessionLocal.begin() as s:
            row = s.get(VoteResult, rid)
            row.votes = original
            row.status = "verified"


def test_historical_totals_and_geoid_joins(client):
    result = client.get("/api/elections/az-2014-governor").json()
    assert len(result["statewide"]["candidates"]) == 10
    assert result["statewide"]["winner"]["name"] == "Doug Ducey"
    assert all(c["difference"] == 0 for c in result["reconciliation"]["candidates"])
    # County names are display labels, not join keys.
    assert (
        client.get("/api/elections/az-2022-governor/counties/04011").json()["name"]
        == "Greenlee"
    )
    assert (
        client.get("/api/elections/az-2022-governor/counties/04012").json()["name"]
        == "La Paz"
    )


def test_2018_certified_results_turnout_and_provenance(client):
    detail = client.get("/api/elections/az-2018-governor").json()
    assert detail["election"]["status"] == "verified"
    assert detail["election"]["county_count"] == 15
    statewide = detail["statewide"]
    assert statewide["total_votes"] == 2376441
    expected = {
        "Doug Ducey": 1330863,
        "David Garcia": 994341,
        "Angel Torres": 50962,
        "Cary D. Dolego (Write-In)": 13,
        'Arthur Ray "RT" Arvizu (Write-In)': 12,
        'James "MarvelMan" Gibson II (Write-In)': 7,
        "Christian Komor (Write-In)": 66,
        "Patrick Masoya (Write-In)": 177,
    }
    assert {c["name"]: c["votes"] for c in statewide["candidates"]} == expected
    assert sum(c["votes"] for c in statewide["candidates"] if c["write_in"]) == 275
    assert len(detail["sources"]) == 4
    assert {"canvass-2018", "census-2022", "vest-2018", "openelections-2018"} == {
        s["id"] for s in detail["sources"]
    }
    counties = client.get("/api/elections/az-2018-governor/counties").json()
    assert len(counties) == 15 and counties[0]["name"] == "Maricopa"
    for name, total in expected.items():
        assert (
            sum(
                next(c["votes"] for c in r["candidates"] if c["name"] == name)
                for r in counties
            )
            == total
        )
    for county in counties:
        assert (
            client.get(
                "/api/elections/az-2018-governor/counties/" + county["geoid"]
            ).json()
            == county
        )
        assert len(county["candidates"]) == 8
        assert all(c["status"] == "verified" for c in county["candidates"])
        assert sum(c["percent"] for c in county["candidates"]) == pytest.approx(100)
        assert county["turnout"]["percent"] is not None
    assert sum(c["turnout"]["ballots_cast"] for c in counties) == 2409910
    assert sum(c["turnout"]["registered_voters"] for c in counties) == 3716263
    assert statewide["turnout"]["percent"] == 64.85
    assert sum(c["total_votes"] for c in counties) == 2376441
    for geoid, votes in [("04017", 0), ("04021", 1), ("04025", 0)]:
        county = next(c for c in counties if c["geoid"] == geoid)
        assert (
            next(
                c["votes"]
                for c in county["candidates"]
                if c["name"] == "Cary D. Dolego (Write-In)"
            )
            == votes
        )
    comparison = detail["reconciliation"]["input_validation"]
    assert comparison["precinct_count"] == 1489
    assert all(c["difference"] == 0 for c in comparison["ballot_candidates"])
    assert comparison["vest_write_in_comparison"]["vest_total"] == 3203
    assert comparison["vest_write_in_comparison"]["official_named_total"] == 275
    assert comparison["vest_write_in_comparison"]["difference"] == 2928
    with SessionLocal() as s:
        sources = dict(
            s.execute(
                select(VoteResult.source_id, func.count())
                .join(Participation)
                .where(Participation.contest_id == "az-2018-governor")
                .group_by(VoteResult.source_id)
            ).all()
        )
        assert sources == {"canvass-2018": 8, "vest-2018": 45, "openelections-2018": 75}


def test_2018_normalization_is_reproducible_and_detects_missing_votes():
    from scripts.normalize_2018 import normalize_2018, aggregate_vest
    from scripts.normalize import COUNTIES

    before = (ROOT / "data/processed/2018.json").read_bytes()
    normalize_2018()
    assert (ROOT / "data/processed/2018.json").read_bytes() == before
    data = json.loads(before)
    data["candidates"][0]["county_votes"]["04011"] = None
    assert reconcile(data)["status"] == "incomplete"
    assert reconcile(data)["candidates"][0]["missing_counties"] == ["04011"]
    totals, counts = aggregate_vest(ROOT / "data/raw/2018/az_2018.zip")
    assert set(totals) == {g for g, _ in COUNTIES}
    assert sum(counts.values()) == 1489
    assert sum(r["G18GOVOWRI"] for r in totals.values()) == 3203


def test_2026_provider_availability_and_pre_release_api(client):
    for office in ("governor", "attorney-general"):
        endpoint = f"/api/elections/az-2026-{office}"
        detail = client.get(endpoint).json()
        assert detail["election"]["status"] == "pre_results"
        assert detail["statewide"]["candidates"] == []
        assert detail["statewide"]["winner"] is None
        assert detail["statewide"]["total_votes"] is None
        rows = client.get(endpoint + "/counties").json()
        assert len(rows) == 15
        assert all(not r["candidates"] and r["winner"] is None and r["total_votes"] is None for r in rows)
        activity = client.get(endpoint + "/activity").json()
        assert activity["stage"] == "pre_results" and activity["reported_leaders"] == {}
        assert activity["candidate_availability"] == "not_released"
        assert activity["provider_report"] is None
        assert activity["provider_participation"]["provider"] == "civicAPI"
        assert activity["coverage"]["ballots_requested"] == 15
        assert activity["coverage"]["ballots_received"] == 15
        assert len(activity["sources"]) == len(activity["releases"]) == 2
        assert all(source["url"].startswith("https://civicapi.org/api/v2/early-vote/") for source in activity["sources"])
        assert not activity["warnings"]
    assert client.get("/api/elections/az-2022-governor/activity").json() is None


def test_attorney_general_history_and_2026_event_activity(client):
    totals = {
        2014: [
            ("Mark Brnovich", 782361),
            ("Felecia Rotellini", 696054),
            ("Anthony Camboni (Write-In)", 265),
        ],
        2018: [
            ("Mark Brnovich", 1201398),
            ("January Contreras", 1120726),
            ("Anthony Camboni (Write-In)", 346),
        ],
        2022: [
            ('Abraham "Abe" Hamadeh', 1254102),
            ("Kris Mayes", 1254613),
            ("Samantha Severson (Write-In)", 418),
        ],
    }
    for year, expected in totals.items():
        detail = client.get(f"/api/elections/az-{year}-attorney-general").json()
        assert detail["election"]["status"] == "verified"
        assert detail["election"]["county_count"] == 15
        assert detail["statewide"]["total_votes"] == sum(v for _, v in expected)
        assert [
            (c["name"], c["votes"]) for c in detail["statewide"]["candidates"]
        ] == sorted(expected, key=lambda x: -x[1])
        assert detail["reconciliation"]["status"] == "verified"
        assert len(detail["reconciliation"]["candidates"]) == 3
        assert all(
            c["difference"] == 0 and not c["missing_counties"]
            for c in detail["reconciliation"]["candidates"]
        )
        county_rows = client.get(
            f"/api/elections/az-{year}-attorney-general/counties"
        ).json()
        assert len(county_rows) == 15
        assert all(len(row["candidates"]) == 3 for row in county_rows)
    rows = client.get("/api/elections/az-2026-attorney-general/counties").json()
    activity = client.get("/api/elections/az-2026-attorney-general/activity").json()
    assert len(rows) == 15
    assert all(not row["candidates"] and row["winner"] is None for row in rows)
    assert activity["stage"] == "pre_results"
    assert activity["coverage"]["registered_voters"] == 0
    assert activity["coverage"]["ballots_received"] == 15


def test_2026_snapshot_idempotence_and_historical_values(client):
    from backend.app.models import PublicationSnapshot, MetricObservation
    from backend.app.main import election, counties
    import hashlib

    def digest(s, year):
        data = {
            "detail": election(f"az-{year}-governor", s).model_dump(),
            "counties": [r.model_dump() for r in counties(f"az-{year}-governor", s)],
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    with SessionLocal() as s:
        baseline = {year: digest(s, year) for year in [2014, 2018, 2022]}
        before = [
            s.scalar(select(func.count()).select_from(m))
            for m in [
                PublicationSnapshot,
                MetricObservation,
                Participation,
                VoteResult,
                Turnout,
            ]
        ]
    subprocess.run(
        [sys.executable, "scripts/refresh_2026.py"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    with SessionLocal() as s:
        assert [
            s.scalar(select(func.count()).select_from(m))
            for m in [
                PublicationSnapshot,
                MetricObservation,
                Participation,
                VoteResult,
                Turnout,
            ]
        ] == before
        assert {year: digest(s, year) for year in baseline} == baseline


def test_2026_staleness_corrections_and_older_snapshots(client, tmp_path):
    from datetime import datetime, timezone
    from backend.app.lifecycle import apply_snapshot, activity, record_failure, CONTEST
    from backend.app.publication_input import SnapshotInput
    import hashlib

    raw = tmp_path / "data/raw/aggregate.json"
    raw.parent.mkdir(parents=True)
    raw.write_text('{"test_only":true}')
    values = dict(
        election_date="2026-11-03",
        election_kind="general",
        stream="test-corrections",
        kind="participation",
        stage="pre_results",
        completeness="partial",
        verification="source_checked",
        source=dict(
            title="Synthetic aggregate fixture",
            url="https://recorder.pima.gov/test-fixture",
            raw_path="data/raw/aggregate.json",
            sha256=hashlib.sha256(raw.read_bytes()).hexdigest(),
            notes="Test fixture, not production election data",
        ),
        reported_at="2026-10-25",
        report_precision="date",
        retrieved_at="2026-10-27T10:00:00+00:00",
        release_id="fixture-v1",
        vote_scope="participation",
        metrics=[
            dict(
                geoid="04001",
                key="ballots_accepted",
                label="Test only",
                definition="Test acceptance count",
                value=10,
                completeness="complete",
                coverage_note="",
            )
        ],
        notes="Test only",
    )
    now = datetime(2026, 10, 27, 11, tzinfo=timezone.utc)
    with SessionLocal() as s:
        # Exercise the archived official-stream behavior without the current provider selection.
        s.get(Contest, CONTEST).source_id = "2026-availability"
        from backend.app.models import CurrentSnapshot
        from sqlalchemy import delete
        s.execute(delete(CurrentSnapshot).where(CurrentSnapshot.stream.like("early-vote-%")))
        apply_snapshot(s, SnapshotInput.model_validate(values), root=tmp_path, now=now)
        reduced = copy.deepcopy(values)
        reduced["metrics"][0]["value"] = 0
        reduced["reported_at"] = "2026-10-26"
        reduced["retrieved_at"] = "2026-10-27T10:30:00+00:00"
        reduced["release_id"] = "fixture-v2"
        outcome = apply_snapshot(
            s, SnapshotInput.model_validate(reduced), root=tmp_path, now=now
        )
        assert any("decreased from 10 to 0" in w for w in outcome["warnings"])
        older = apply_snapshot(
            s, SnapshotInput.model_validate(values), root=tmp_path, now=now
        )
        assert not older["advanced"]
        record_failure(s, "test-corrections", "Fixture network failure", now=now)
        s.flush()
        # Replaying an old retained file does not clear a failed fresh retrieval.
        apply_snapshot(s, SnapshotInput.model_validate(reduced), root=tmp_path, now=now)
        a = activity(s, CONTEST, now=now)
        m = next(
            m
            for c in a["counties"]
            if c["geoid"] == "04001"
            for m in c["metrics"]
            if m["key"] == "ballots_accepted"
        )
        assert m["value"] == 0 and m["stale"]
        assert a["failures"] and a["stale"]
        assert a["candidate_availability"] == "not_released"
        assert (
            activity(s, CONTEST, now=datetime(2026, 11, 4, 4, tzinfo=timezone.utc))[
                "candidate_availability"
            ]
            == "not_imported"
        )
        timed = copy.deepcopy(values)
        timed.update(
            report_precision="datetime", reported_at="2026-10-25T03:00:00-07:00"
        )
        assert (
            SnapshotInput.model_validate(timed).reported_at
            == "2026-10-25T10:00:00+00:00"
        )
        raw.write_text("tampered source")
        with pytest.raises(ValueError, match="checksum"):
            apply_snapshot(
                s, SnapshotInput.model_validate(values), root=tmp_path, now=now
            )
        s.rollback()

def test_2026_source_adapter_guards(monkeypatch):
    from scripts import refresh_2026 as refresh

    manifest = json.loads(
        next((ROOT / "data/raw/2026/manifests").glob("maricopa-*.json")).read_text()
    )
    bundle = json.loads((ROOT / manifest["source"]["raw_path"]).read_text())
    monkeypatch.setattr(
        refresh, "raw_file", lambda *_: ("data/raw/test-only.json", "0" * 64)
    )
    valid = next(
        a["attributes"]
        for a in bundle["aggregate"]["features"]
        if a["attributes"].get("ElectionDescription")
    )
    valid["returns"] = 0
    assert refresh.maricopa_from_bundle(bundle)["metrics"][1]["value"] == 0
    valid["return_records"] -= 1
    with pytest.raises(ValueError, match="missing or invalid"):
        refresh.maricopa_from_bundle(bundle)
    valid["ElectionDescription"] = "JUL 21 2026 PRIMARY ELECTION"
    with pytest.raises(ValueError, match="primary results are forbidden"):
        refresh.maricopa_from_bundle(bundle)

    class PrimaryPage:
        def extract_text(self):
            return "Early Ballot Status Report 2026 PRIMARY ELECTION Status as of end of day:"

    class PrimaryPDF:
        pages = [PrimaryPage()]

    monkeypatch.setattr(refresh, "PdfReader", lambda _: PrimaryPDF())
    with pytest.raises(ValueError, match="exactly one 2026 general-election"):
        refresh.pima_from_pdf(b"test-only")


def test_2026_result_stages_and_certification_guard(client, tmp_path, monkeypatch):
    from datetime import datetime, timezone
    from backend.app import lifecycle
    from backend.app.lifecycle import apply_snapshot, activity, CONTEST
    from backend.app.publication_input import SnapshotInput
    from backend.app.services import results
    from backend.app.models import GeographicUnit
    from scripts.normalize import COUNTIES
    import hashlib, csv

    raw = tmp_path / "data/raw/result.json"
    raw.parent.mkdir(parents=True)
    raw.write_text('{"synthetic_test_release":true}')
    source = dict(
        title="Synthetic official-source fixture",
        url="https://results.arizona.vote/test-fixture",
        raw_path="data/raw/result.json",
        sha256=hashlib.sha256(raw.read_bytes()).hexdigest(),
        notes="Synthetic unit-test records; never loaded into production",
    )
    units = ["04", *[g for g, _ in COUNTIES]]
    payload = dict(
        election_date="2026-11-03",
        election_kind="general",
        stream="results",
        kind="results",
        stage="unofficial",
        completeness="complete",
        verification="source_checked",
        source=source,
        reported_at="2026-11-04T03:05:00+00:00",
        report_precision="datetime",
        retrieved_at="2026-11-04T03:06:00+00:00",
        release_id="synthetic-source-release-1",
        vote_scope="total",
        metrics=[],
        candidates=[
            dict(
                key="fixture-a",
                name="Fixture A",
                party="REP",
                party_name="Republican",
                write_in=False,
            ),
            dict(
                key="fixture-b",
                name="Fixture B",
                party="DEM",
                party_name="Democratic",
                write_in=False,
            ),
        ],
        votes=[
            dict(geoid=u, candidate=k, votes=n * (15 if u == "04" else 1))
            for u in units
            for k, n in [("fixture-a", 1), ("fixture-b", 2)]
        ],
        roster_complete=True,
        complete_units=units,
        notes="Synthetic test release",
    )
    before = datetime(2026, 10, 27, 15, tzinfo=timezone.utc)
    with SessionLocal() as s:
        with pytest.raises(ValueError):
            apply_snapshot(
                s, SnapshotInput.model_validate(payload), root=tmp_path, now=before
            )
        s.rollback()
    after = datetime(2026, 11, 4, 3, 10, tzinfo=timezone.utc)
    monkeypatch.setattr(lifecycle, "utcnow", lambda: after)
    with SessionLocal() as s:
        apply_snapshot(
            s, SnapshotInput.model_validate(payload), root=tmp_path, now=after
        )
        c = s.get(Contest, CONTEST)
        state = results(s, c, s.get(GeographicUnit, "04"))
        assert (
            state.status == "unofficial"
            and state.total_votes == 45
            and state.winner is None
        )
        assert state.candidates[0].percent == pytest.approx(2 / 3 * 100)
        assert (
            activity(s, CONTEST, now=after)["reported_leaders"]["04"]["name"]
            == "Fixture B"
        )
        # A partial source roster must not produce percentages or a leader.
        partial = copy.deepcopy(payload)
        partial["roster_complete"] = False
        partial["completeness"] = "partial"
        partial["release_id"] = "synthetic-incomplete-roster"
        apply_snapshot(
            s, SnapshotInput.model_validate(partial), root=tmp_path, now=after
        )
        assert results(s, c, s.get(GeographicUnit, "04")).total_votes is None
        assert activity(s, CONTEST, now=after)["reported_leaders"] == {}
        s.rollback()
    reference = tmp_path / "data/raw/canvass.csv"
    fields = [
        "party",
        "name",
        "write_in",
        *[g for g, _ in COUNTIES],
        "official_statewide",
    ]
    with reference.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for name, party, n in [("Fixture A", "REP", 1), ("Fixture B", "DEM", 2)]:
            writer.writerow(
                dict(
                    party=party,
                    name=name,
                    write_in="false",
                    **{g: n for g, _ in COUNTIES},
                    official_statewide=n * 15,
                )
            )
    certified = copy.deepcopy(payload)
    certified.update(
        stage="certified",
        verification="reconciled",
        reference_path="data/raw/canvass.csv",
        certification=source,
        release_id="synthetic-certified-canvass",
    )
    with SessionLocal() as s:
        wrong = copy.deepcopy(certified)
        wrong["votes"][0]["votes"] += 1
        with pytest.raises(ValueError, match="does not reconcile"):
            apply_snapshot(
                s, SnapshotInput.model_validate(wrong), root=tmp_path, now=after
            )
        apply_snapshot(
            s, SnapshotInput.model_validate(certified), root=tmp_path, now=after
        )
        c = s.get(Contest, CONTEST)
        state = results(s, c, s.get(GeographicUnit, "04"))
        assert state.status == "verified" and state.winner.name == "Fixture B"
        with pytest.raises(ValueError, match="cannot replace"):
            apply_snapshot(
                s, SnapshotInput.model_validate(payload), root=tmp_path, now=after
            )
        s.rollback()
    ag_payload = copy.deepcopy(payload)
    ag_payload.update(
        office_id="attorney-general",
        stream="results-attorney-general",
        release_id="synthetic-ag-unofficial",
    )
    with SessionLocal() as s:
        apply_snapshot(
            s, SnapshotInput.model_validate(ag_payload), root=tmp_path, now=after
        )
        ag = s.get(Contest, "az-2026-attorney-general")
        governor = s.get(Contest, CONTEST)
        ag_results = results(s, ag, s.get(GeographicUnit, "04"))
        gov_results = results(s, governor, s.get(GeographicUnit, "04"))
        assert ag_results.status == "unofficial" and len(ag_results.candidates) == 2
        assert gov_results.candidates == []
        assert activity(s, "az-2026-attorney-general", now=after)["reported_leaders"]
        assert activity(s, CONTEST, now=after)["reported_leaders"] == {}
        s.rollback()
