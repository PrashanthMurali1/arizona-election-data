"""Governor 1966-1990: secondary-source status, pre-1983 county boundary and shared turnout."""

import copy
import json
import subprocess
import sys

import pytest
from sqlalchemy import func, select

# Reuse the same clean migrated database and offline bootstrap fixture.
from test_pipeline_api import ROOT, client
from backend.app.database import SessionLocal
from backend.app.models import Turnout
from scripts.import_data import reconcile
from scripts.normalize_governor_historical import normalize
from scripts.senate_sources import verify_provenance

# year: (candidates, write-in rows, total votes, winner, winner votes, counties)
EXPECTED = {
    1966: (2, 0, 378342, "Jack Williams", 203438, 14),
    1970: (2, 0, 411409, "Jack Williams", 209356, 14),
    1974: (3, 1, 552202, "Raul Castro", 278375, 14),
    1978: (4, 0, 538556, "Bruce Babbitt", 282605, 14),
    1982: (4, 1, 726364, "Bruce Babbitt", 453795, 14),
    1986: (3, 0, 866984, "Evan Mecham", 343913, 15),
    1990: (4, 2, 1055406, "Fife Symington", 523984, 15),
}
RAW = ROOT / "data/raw/governor-historical"


def contest_id(year):
    return f"az-{year}-governor"


@pytest.mark.parametrize("year", EXPECTED)
def test_results_are_shown_but_never_marked_verified(client, year):
    count, write_ins, total, winner, winner_votes, counties = EXPECTED[year]
    detail = client.get(f"/api/elections/{contest_id(year)}").json()
    election, state = detail["election"], detail["statewide"]
    assert election["status"] == "secondary" and state["status"] == "secondary"
    assert election["candidate_count"] == count and election["county_count"] == counties
    assert state["total_votes"] == total
    assert (state["winner"]["name"], state["winner"]["votes"]) == (winner, winner_votes)
    assert sum(c["write_in"] for c in state["candidates"]) == write_ins
    assert detail["reconciliation"]["status"] == "secondary"
    assert "NOT verified against an official canvass" in election["notes"]
    assert any(s["id"] == f"rightdatausa-{year}-governor" for s in detail["sources"])
    assert f"en.wikipedia.org/wiki/{year}_Arizona_gubernatorial_election" in election["notes"]
    rows = client.get(f"/api/elections/{contest_id(year)}/counties").json()
    assert len(rows) == counties
    for row in rows:
        assert row["winner"] is not None and row["status"] == "secondary"
        assert sum(c["percent"] for c in row["candidates"]) == pytest.approx(100)
    for candidate in state["candidates"]:
        county_sum = sum(next(c["votes"] for c in row["candidates"] if c["id"] == candidate["id"]) for row in rows)
        # 1990's reviewed Goddard shortfall is the only county/state difference.
        assert county_sum == candidate["votes"] - (200 if (year, candidate["name"]) == (1990, "Terry Goddard") else 0)


def test_1990_goddard_difference_is_reviewed_and_visible(client):
    report = client.get("/api/elections/az-1990-governor").json()["reconciliation"]
    differences = {c["candidate"]: c["difference"] for c in report["candidates"] if c["difference"]}
    assert differences == {"Terry Goddard": -200}


def test_pre_1983_elections_use_the_fourteen_county_boundary(client):
    for year in (1966, 1970, 1974, 1978, 1982):
        election = client.get(f"/api/elections/{contest_id(year)}").json()["election"]
        assert election["boundary_id"] == "county-1966-1982"
        assert client.get(f"/api/elections/{contest_id(year)}/counties/04012").status_code == 404
    for year in (1986, 1990):
        assert client.get(f"/api/elections/{contest_id(year)}").json()["election"]["boundary_id"] == "county-2022"
    old = {f["properties"]["geoid"]: f for f in client.get("/api/geography/county-1966-1982").json()["features"]}
    now = {f["properties"]["geoid"]: f for f in client.get("/api/geography/county-2022").json()["features"]}
    assert len(old) == 14 and "04012" not in old and len(now) == 15

    def bounds(*features):
        points = [p for f in features for p in f["geometry"]["coordinates"][0]]
        return tuple(f(p[i] for p in points) for i in (0, 1) for f in (min, max))

    # Pre-1983 Yuma County covers today's Yuma and La Paz; every other county is unchanged.
    assert bounds(old["04027"]) == bounds(now["04027"], now["04012"])
    assert all(old[g] == now[g] for g in old if g != "04027")


def test_turnout_belongs_to_the_election_not_to_a_governor_import(client):
    # 1986's official turnout comes from the Senate canvass and survives the Governor import.
    state = client.get("/api/elections/az-1986-governor").json()["statewide"]
    assert state["turnout"]["ballots_cast"] == 889668
    assert state["turnout"]["source_id"] == "canvass-1986-us-senate"
    # Elections without an official turnout source show none instead of an invented value.
    for year in (1966, 1970, 1974, 1978, 1982, 1990):
        assert client.get(f"/api/elections/{contest_id(year)}").json()["statewide"]["turnout"]["ballots_cast"] is None
    with SessionLocal() as s:
        before = s.scalar(select(func.count()).select_from(Turnout))
    subprocess.run([sys.executable, "scripts/import_data.py", "--office", "governor"], cwd=ROOT, check=True, capture_output=True)
    with SessionLocal() as s:
        assert s.scalar(select(func.count()).select_from(Turnout)) == before


def test_status_ceiling_is_what_keeps_these_years_unverified():
    for year in EXPECTED:
        path = ROOT / f"data/processed/governor-historical/{contest_id(year)}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["status_ceiling"] == "secondary" and data["turnout"] == {}
        assert reconcile(data, ROOT / data["reference_path"])["status"] == "secondary"
        uncapped = copy.deepcopy(data)
        del uncapped["status_ceiling"]
        # Without the ceiling the same data would reconcile; the cap is a source-quality decision.
        expected = {1990: "reported"}.get(year, "verified")
        assert reconcile(uncapped, ROOT / data["reference_path"])["status"] == expected
        if year == 1990:
            uncapped["reviewed_county_differences"] = {}
            assert reconcile(uncapped, ROOT / data["reference_path"])["status"] == "incomplete"


def test_sources_normalization_and_wikipedia_cross_check():
    comparison = json.loads((ROOT / "data/processed/governor-historical/validation/wikipedia-comparison.json").read_text(encoding="utf-8"))
    for year in EXPECTED:
        provenance = verify_provenance(RAW / f"{year}-provenance.json")
        path = ROOT / f"data/processed/governor-historical/{contest_id(year)}.json"
        before = path.read_bytes()
        assert normalize(RAW / f"{year}-transcription.csv").read_bytes() == before
        data = json.loads(before)
        assert len(data["candidates"]) == provenance["candidate_count"]
        assert len(data["expected_units"]) == (15 if year >= 1986 else 14)
        check = comparison[str(year)]
        assert check["totals_match"] and check["all_named_match"]
        assert check.get("write_ins", {"match": True})["match"]
        for c in data["candidates"]:
            shortfall = -200 if (year, c["name"]) == (1990, "Terry Goddard") else 0
            assert sum(c["county_votes"].values()) - c["statewide"] == shortfall
