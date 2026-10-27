"""Independent district contests, original-source cells, historical maps and isolation."""

import copy
import hashlib
import json

import pytest
from sqlalchemy import func, select
from test_pipeline_api import ROOT, client
from backend.app.database import SessionLocal
from backend.app.models import (
    Contest,
    ElectionEvent,
    Participation,
    Turnout,
    VoteResult,
)
from scripts.house_records import regular_records
from scripts.house_sources import COUNTY_IDS, verify_snapshots
from scripts.normalize_house import read_reference, validate_event
from scripts.import_house import import_all

EXPECTED = {
    2014: (29, 1467617),
    2016: (26, 2412064),
    2018: (24, 2341270),
    2020: (29, 3268249),
    2022: (26, 2360078),
    2024: (26, 3253920),
}


@pytest.mark.parametrize("year", EXPECTED)
def test_regular_house_coverage_and_district_arithmetic(client, year):
    detail = client.get(f"/api/elections/az-{year}-us-house").json()
    assert "statewide" not in detail
    election = detail["election"]
    assert election["status"] == "verified" and election["kind"] == "general"
    assert election["district_count"] == 9
    assert election["candidate_count"] == EXPECTED[year][0]
    plan = 2012 if year <= 2020 else 2022
    assert election["boundary_id"] == f"congressional-{plan}"
    geography = client.get(f"/api/geography/congressional-{plan}").json()
    units = {f"az-cd-{plan}-{i:02}" for i in range(1, 10)}
    assert {d["geoid"] for d in detail["districts"]} == units
    assert {f["properties"]["geoid"] for f in geography["features"]} == units
    assert all(
        f["geometry"]["type"] in {"Polygon", "MultiPolygon"}
        for f in geography["features"]
    )
    assert detail["default_district"] == f"az-cd-{plan}-01"
    assert sum(d["total_votes"] for d in detail["districts"]) == EXPECTED[year][1]
    reporting_counties = set()
    with SessionLocal() as s:
        for district in detail["districts"]:
            assert district["contested"] and district["winner"]
            assert district["turnout"]["ballots_cast"] is None
            assert district["turnout"]["registered_voters"] is None
            assert (
                sum(c["votes"] for c in district["candidates"])
                == district["total_votes"]
            )
            assert sum(c["percent"] for c in district["candidates"]) == pytest.approx(
                100
            )
            assert district["winner"]["votes"] == max(
                c["votes"] for c in district["candidates"]
            )
            contest = s.get(Contest, district["contest_id"])
            assert contest.jurisdiction_id == district["geoid"]
            assert contest.event_id == f"az-{year}-general"
            report = detail["reconciliation"]["reports"][district["geoid"]]
            assert all(
                c["difference"] == 0 and not c["missing_counties"]
                for c in report["candidates"]
            )
            assert report["source_cells_validated"]
            for candidate in district["candidates"]:
                records = list(
                    s.scalars(
                        select(VoteResult).where(
                            VoteResult.participation_id == candidate["id"],
                            VoteResult.unit_id != district["geoid"],
                        )
                    )
                )
                assert sum(r.votes for r in records) == candidate["votes"]
                reporting_counties.update(r.unit_id for r in records)
            assert client.get(f"/api/elections/{contest.id}").json()["district"] == {
                k: v
                for k, v in district.items()
                if k not in {"contested", "contest_id"}
            }
            assert (
                client.get(f"/api/elections/{contest.id}/statewide").status_code == 404
            )
    assert reporting_counties == set(COUNTY_IDS)
    assert client.get(f"/api/elections/az-{year}-us-house/statewide").status_code == 404


def test_house_recount_and_actual_county_correction(client):
    with SessionLocal() as s:
        for name, expected in [
            ("Ron Barber", {"04003": 14677, "04019": 94870}),
            ("Martha McSally", {"04003": 21737, "04019": 87977}),
        ]:
            district = client.get("/api/elections/az-2014-us-house").json()[
                "districts"
            ][1]
            candidate = next(c for c in district["candidates"] if c["name"] == name)
            records = list(
                s.scalars(
                    select(VoteResult).where(
                        VoteResult.participation_id == candidate["id"],
                        VoteResult.unit_id.in_(expected),
                    )
                )
            )
            assert {r.unit_id: r.votes for r in records} == expected
            assert all(r.source_id == "house-2014-recount" for r in records)
        district = client.get("/api/elections/az-2024-us-house").json()["districts"][8]
        gosar = next(c for c in district["candidates"] if "Gosar" in c["name"])
        records = list(
            s.scalars(
                select(VoteResult).where(
                    VoteResult.participation_id == gosar["id"],
                    VoteResult.unit_id.in_(COUNTY_IDS),
                )
            )
        )
        assert {r.unit_id: r.votes for r in records} == {
            "04012": 5260,
            "04013": 137529,
            "04015": 82372,
            "04027": 24422,
        }


@pytest.mark.parametrize(
    "year,district,plan,date,expected",
    [
        (2018, 8, 2012, "2018-04-24", {"Debbie Lesko": 96012, "Hiral Vyas Tipirneni": 87331}),
        (2025, 7, 2022, "2025-09-23", {"Adelita Grijalva": 70043, "Daniel Butierez": 29893, "Eduardo Quintana": 1116, "Richard Grayson": 536}),
    ],
)
def test_specials_display_retained_civicapi_reports(
    client, year, district, plan, date, expected
):
    id = f"az-{year}-us-house-special-{district:02}"
    detail = client.get(f"/api/elections/{id}").json()
    assert detail["election"]["date"] == date
    assert detail["election"]["kind"] == "special"
    assert detail["election"]["status"] == "civicapi"
    race_id = 29426 if year == 2018 else 6240
    assert f"https://civicapi.org/api/v2/race/{race_id}" in {
        source["url"] for source in detail["sources"]
    }
    assert detail["election"]["district_count"] == 1
    assert detail["default_district"] == f"az-cd-{plan}-{district:02}"
    active = [r for r in detail["districts"] if r["contested"]]
    assert len(active) == 1 and len(active[0]["candidates"]) == len(expected)
    assert {c["name"]: c["votes"] for c in active[0]["candidates"]} == expected
    assert active[0]["winner"] is not None
    assert active[0]["total_votes"] == sum(expected.values())
    inactive = [r for r in detail["districts"] if not r["contested"]]
    assert len(inactive) == 8
    assert all(
        r["status"] == "not_contested"
        and r["winner"] is None
        and r["total_votes"] is None
        and not r["candidates"]
        for r in inactive
    )
    with SessionLocal() as s:
        contest = s.get(Contest, active[0]["contest_id"])
        event = s.get(ElectionEvent, contest.event_id)
        assert event.kind == "special" and event.date == date
        assert contest.event_id != f"az-{year}-general"
        report = detail["reconciliation"]["reports"][active[0]["geoid"]]
        assert report["status"] == "civicapi_report"
        assert report["kind"] == "provider_results"
        assert report["provider"]["provider"] == "civicAPI"
        assert report["provider"]["percent_reporting"] == 100
        assert {c["candidate"]: c["votes"] for c in report["candidates"]} == expected
        assert all("official_district" not in c for c in report["candidates"])
        assert active[0]["turnout"]["ballots_cast"] is None
        assert active[0]["turnout"]["registered_voters"] is None


def test_original_cells_reject_balanced_errors_missing_and_changed_snapshots(client):
    manifest = json.loads((ROOT / "data/raw/us-house/manifest.json").read_text())
    event = next(e for e in manifest["events"] if e["year"] == 2024)
    rows = read_reference(ROOT / event["reference_path"])
    originals = regular_records()[2024]
    validate_event(event, rows, originals)
    changed = copy.deepcopy(rows)
    candidate = next(r for r in changed if r["district"] == 9)
    candidate["county_votes"]["04012"] += 1
    candidate["county_votes"]["04013"] -= 1
    with pytest.raises(ValueError, match="original source cells"):
        validate_event(event, changed, originals)
    changed = copy.deepcopy(rows)
    next(r for r in changed if r["district"] == 9)["county_votes"]["04012"] = None
    with pytest.raises(ValueError):
        validate_event(event, changed, originals)
    damaged = copy.deepcopy(manifest)
    damaged["snapshots"][0]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="checksum mismatch"):
        verify_snapshots(damaged)


def test_house_repeat_import_preserves_other_offices_and_event_turnout(client):
    catalog = client.get("/api/elections").json()
    assert len([e for e in catalog if e["office_id"] == "us-house"]) == 8
    assert all(e["year"] != 2026 for e in catalog if e["office_id"] == "us-house")
    previous = {
        e["id"]: client.get(f"/api/elections/{e['id']}").json() for e in catalog
    }

    def counts():
        with SessionLocal() as s:
            return [
                s.scalar(select(func.count()).select_from(model))
                for model in [
                    Contest,
                    ElectionEvent,
                    Participation,
                    VoteResult,
                    Turnout,
                ]
            ]

    before = counts()
    import_all(2018)
    assert counts() == before
    import_all()
    assert counts() == before
    assert {
        e["id"]: client.get(f"/api/elections/{e['id']}").json() for e in catalog
    } == previous
