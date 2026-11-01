"""Validate, reconcile and transactionally upsert normalized authoritative data."""

import csv, hashlib, json, sys
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import select, delete

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.database import SessionLocal
from backend.app.models import *
from scripts.normalize import COUNTIES


STATUS_RANK = {"incomplete": 0, "secondary": 1, "reported": 2, "verified": 3}
HISTORICAL_BOUNDARY = "county-1966-1982"


def reconcile(data, reference_path=None):
    if data.get("provenance_path"):
        from scripts.senate_sources import verify_provenance

        verify_provenance(ROOT / data["provenance_path"])
    # Counties that existed for this election (14 before La Paz County was created in 1983).
    expected = set(data.get("expected_units") or [c[0] for c in COUNTIES])
    for unit, turnout in data.get("turnout", {}).items():
        if unit not in expected | {"04"}:
            raise ValueError("Unknown turnout geographic identifier")
        for key in ["ballots_cast", "registered_voters"]:
            value = turnout.get(key)
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError("Turnout counts must be nonnegative integers or null")
        percent = turnout.get("percent")
        if percent is not None and (
            type(percent) not in (int, float) or not 0 <= percent <= 100
        ):
            raise ValueError(
                "Official turnout percent must be between 0 and 100 or null"
            )
    reference_path = (
        reference_path or ROOT / f"data/raw/{data['year']}-governor-transcription.csv"
    )
    # Authoritative reference is read independently of the normalized input.
    reference_rows = (
        list(csv.DictReader(reference_path.open(encoding="utf-8", newline="")))
        if reference_path.exists()
        else []
    )
    reference = {row["name"]: int(row["official_statewide"]) for row in reference_rows}
    source_cells = {row["name"]: row for row in reference_rows}
    if len(reference) != len(reference_rows):
        raise ValueError("Duplicate authoritative candidate names")
    discrepancies = []
    ids = set()
    names = set()
    represented = set()
    complete_counties = set(expected)
    for c in data["candidates"]:
        if c["id"] in ids or c["name"] in names:
            raise ValueError("Duplicate candidate ID or name")
        ids.add(c["id"])
        names.add(c["name"])
        votes = c["county_votes"]
        if set(votes) - expected:
            raise ValueError("Unknown geographic identifier")
        for value in [*votes.values(), c["statewide"]]:
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError("Votes must be nonnegative integers or null")
        present = {k for k, v in votes.items() if v is not None}
        represented |= present
        complete_counties &= present
        missing = sorted(expected - present)
        total = sum(v for v in votes.values() if v is not None)
        official = reference.get(c["name"])
        raw = source_cells.get(c["name"], {})
        mismatches = sorted(
            unit
            for unit in expected
            if votes.get(unit) is not None
            and (not raw.get(unit) or votes[unit] != int(raw[unit]))
        )
        metadata_matches = (
            bool(raw)
            and c["party"] == raw["party"]
            and c["write_in"] == (raw["write_in"] == "true")
        )
        discrepancy = None if official is None else total - official
        discrepancies.append(
            dict(
                candidate=c["name"],
                county_sum=total,
                official_statewide=official,
                normalized_statewide=c["statewide"],
                statewide_matches_reference=official is not None
                and c["statewide"] == official,
                difference=discrepancy,
                missing_counties=missing,
                county_reference_mismatches=mismatches,
                candidate_metadata_matches_reference=metadata_matches,
            )
        )
    missing_candidates = sorted(set(reference) - names)
    unexpected_candidates = sorted(names - set(reference))
    verified = (
        bool(ids)
        and bool(reference)
        and not missing_candidates
        and not unexpected_candidates
        and all(
            not d["missing_counties"]
            and d["difference"] == 0
            and d["statewide_matches_reference"]
            and not d["county_reference_mismatches"]
            and d["candidate_metadata_matches_reference"]
            for d in discrepancies
        )
    )
    # Explicitly reviewed arithmetic differences may be displayed as reported,
    # while missing data, source mismatches and any additional discrepancy fail.
    reviewed = data.get("reviewed_county_differences", {})
    actual = {d["candidate"]: d["difference"] for d in discrepancies if d["difference"] != 0}
    reported = bool(actual) and actual == reviewed and not missing_candidates and not unexpected_candidates and all(
        not d["missing_counties"] and d["statewide_matches_reference"]
        and not d["county_reference_mismatches"] and d["candidate_metadata_matches_reference"]
        for d in discrepancies
    )
    status = "verified" if verified else "reported" if reported else "incomplete"
    # A contest sourced from open or secondary data rather than the official canvass never claims more
    # than its ceiling: "reported" caps verified; "secondary" caps verified and reported.
    ceiling = data.get("status_ceiling")
    if ceiling and STATUS_RANK[status] > STATUS_RANK[ceiling]:
        status = ceiling
    # A source that publishes only statewide totals (no county table) is admitted, still
    # incomplete, when every candidate's printed statewide total and metadata match.
    statewide_only = (
        data.get("coverage") == "statewide_only"
        and bool(ids)
        and not missing_candidates
        and not unexpected_candidates
        and all(
            len(d["missing_counties"]) == len(expected)
            and d["statewide_matches_reference"]
            and d["candidate_metadata_matches_reference"]
            for d in discrepancies
        )
    )
    return dict(
        status=status,
        coverage="statewide_only" if statewide_only else "county",
        county_count=len(represented),
        complete_county_count=len(complete_counties) if ids else 0,
        expected_county_count=len(expected),
        missing_candidates=missing_candidates,
        unexpected_candidates=unexpected_candidates,
        reference=data["source_url"],
        reference_snapshot=str(reference_path.relative_to(ROOT))
        if reference_path.is_relative_to(ROOT)
        else str(reference_path)
        if reference_rows
        else None,
        reference_sha256=hashlib.sha256(reference_path.read_bytes()).hexdigest()
        if reference_rows
        else None,
        candidates=discrepancies,
    )


def import_all(year=None, office=None):
    selected_year = year
    geo = json.loads((ROOT / "data/geography/az-counties-2022.geojson").read_text())
    if len(geo["features"]) != 15 or {
        f["properties"]["geoid"] for f in geo["features"]
    } != {c[0] for c in COUNTIES}:
        raise ValueError("Geography must contain the 15 expected Arizona county GEOIDs")
    gs = json.loads((ROOT / "data/geography/source.json").read_text())
    reports = []
    with SessionLocal.begin() as s:
        s.merge(
            Source(
                id="census-2022",
                title="U.S. Census Bureau — 2022 county boundaries",
                **{k: gs[k] for k in ["url", "sha256", "notes"]},
            )
        )
        s.flush()
        s.merge(
            BoundaryVersion(id="county-2022", vintage=2022, source_id="census-2022")
        )
        for id, name in [("04", "Arizona"), *COUNTIES]:
            s.merge(
                GeographicUnit(
                    id=id, name=name, kind="state" if id == "04" else "county"
                )
            )
        s.merge(Office(id="governor", name="Governor"))
        s.merge(Office(id="attorney-general", name="Attorney General"))
        s.merge(Office(id="us-senate", name="U.S. Senate"))
        s.flush()

        def upsert_geometry(boundary_id, features):
            for f in features:
                old = s.scalar(
                    select(Geometry).where(
                        Geometry.unit_id == f["properties"]["geoid"],
                        Geometry.boundary_id == boundary_id,
                    )
                )
                if old:
                    old.feature = f
                else:
                    s.add(
                        Geometry(
                            unit_id=f["properties"]["geoid"],
                            boundary_id=boundary_id,
                            feature=f,
                        )
                    )

        upsert_geometry("county-2022", geo["features"])
        # Elections before La Paz County existed (1983) use the 14-county boundary, with the old
        # Yuma County derived by dissolving today's Yuma and La Paz.
        old_geo = json.loads((ROOT / "data/geography/az-counties-1966-1982.geojson").read_text())
        old_source = json.loads((ROOT / "data/geography/az-counties-1966-1982-source.json").read_text())
        if {f["properties"]["geoid"] for f in old_geo["features"]} != {c[0] for c in COUNTIES} - {"04012"}:
            raise ValueError("Pre-1983 geography must contain the 14 counties that then existed")
        s.merge(
            Source(
                id="census-2022-pre-1983",
                title="U.S. Census Bureau — 2022 county boundaries, Yuma and La Paz dissolved for 1966–1982",
                **{k: old_source[k] for k in ["url", "sha256", "notes"]},
            )
        )
        s.flush()
        s.merge(BoundaryVersion(id=HISTORICAL_BOUNDARY, vintage=old_source["vintage"], source_id="census-2022-pre-1983"))
        s.flush()
        upsert_geometry(HISTORICAL_BOUNDARY, old_geo["features"])
        datasets = [
            (p, "governor") for p in sorted((ROOT / "data/processed").glob("*.json"))
        ]
        datasets.extend(
            (p, "attorney-general")
            for p in sorted((ROOT / "data/processed/attorney-general").glob("*.json"))
        )
        datasets.extend(
            (p, "us-senate")
            for p in sorted((ROOT / "data/processed/us-senate").glob("*.json"))
        )
        datasets.extend(
            (p, "governor")
            for p in sorted((ROOT / "data/processed/governor-historical").glob("*.json"))
        )
        for p, office_id in datasets:
            if office is not None and office_id != office:
                continue
            data = json.loads(p.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or "candidates" not in data:
                continue
            if selected_year is not None and data.get("year") != selected_year:
                continue
            if "candidates" not in data:
                continue
            reference_path = (
                ROOT / data["reference_path"] if data.get("reference_path") else None
            )
            report = reconcile(data, reference_path=reference_path)
            if "input_validation" in data:
                report["input_validation"] = data["input_validation"]
            year = data["year"]
            cid = data.get("contest_id", f"az-{year}-{office_id}")
            source = data.get(
                "source_id",
                f"canvass-{year}"
                if office_id == "governor"
                else f"canvass-{year}-{office_id}",
            )
            event = data.get("event_id", f"az-{year}-general")
            s.merge(
                Source(
                    id=source,
                    title=(
                        data.get(
                            "source_title",
                            f"Arizona Secretary of State — {year} official canvass"
                            + (
                                " — " + data["office"]
                                if office_id != "governor"
                                else ""
                            ),
                        )
                    ),
                    url=data["source_url"],
                    sha256=data["source_sha256"],
                    notes=data["source_notes"],
                )
            )
            for additional_source in data.get("additional_sources", []):
                s.merge(Source(**additional_source))
            s.merge(
                ElectionEvent(id=event, year=year, date=data["date"], kind="general")
            )
            s.flush()
            s.merge(
                Contest(
                    id=cid,
                    event_id=event,
                    office_id=office_id,
                    jurisdiction_id="04",
                    boundary_id=data.get("boundary_id", "county-2022"),
                    source_id=source,
                    status=report["status"],
                    notes=data["source_notes"],
                )
            )
            s.flush()
            old_ids = list(
                s.scalars(
                    select(Participation.id).where(Participation.contest_id == cid)
                )
            )
            s.execute(
                delete(VoteResult).where(VoteResult.participation_id.in_(old_ids))
            )
            s.execute(delete(Participation).where(Participation.contest_id == cid))
            # Turnout is shared by every contest of the election: only a contest that supplies its own
            # replaces it, so a Governor import without turnout keeps the Senate's for that election.
            if office_id == "governor" and data.get("turnout"):
                s.execute(delete(Turnout).where(Turnout.event_id == event))
            s.flush()
            names = {
                "DEM": "Democratic",
                "REP": "Republican",
                "LBT": "Libertarian",
                "GRN": "Green",
                "NON": "Nonpartisan",
                "IND": "Independent",
                "UNK": "Unattributed",
                "AEL": "Americans Elect",
                "NONE": "No affiliation",
                "RPA": "Reform Party",
                "NAP": "New Alliance Party",
                "RTO": "RTO (as reported)",
                "HUM": "HUM (as reported)",
                "ATP": "ATP (as reported)",
                "TOR": "TOR (as reported)",
                "IRP": "IRP (as reported)",
                "UPA": "UPA (as reported)",
                "UAT": "UAT (as reported)",
                "SWP": "Socialist Workers",
                "SAB": "Stop Abortion",
            }
            for c in data["candidates"]:
                candidate_report = next(
                    r for r in report["candidates"] if r["candidate"] == c["name"]
                )
                s.merge(Party(id=c["party"], name=names[c["party"]]))
                s.merge(Candidate(id=c["id"], name=c["name"]))
                s.flush()
                s.add(
                    Participation(
                        id=c["id"],
                        contest_id=cid,
                        candidate_id=c["id"],
                        party_id=c["party"],
                        write_in=c["write_in"],
                        category=c["category"],
                    )
                )
                s.flush()
                for unit in ["04", *(data.get("expected_units") or [x[0] for x in COUNTIES])]:
                    value = (
                        c["statewide"] if unit == "04" else c["county_votes"].get(unit)
                    )
                    matches_source = (
                        candidate_report["statewide_matches_reference"]
                        if unit == "04"
                        else unit not in candidate_report["county_reference_mismatches"]
                    ) and candidate_report["candidate_metadata_matches_reference"]
                    s.add(
                        VoteResult(
                            participation_id=c["id"],
                            unit_id=unit,
                            votes=value,
                            source_id=source
                            if unit == "04"
                            else c.get("county_source_id", source),
                            status="unavailable"
                            if value is None
                            else ("verified" if matches_source else "unverified"),
                        )
                    )
            for unit, t in data.get("turnout", {}).items():
                turnout_source = t.get("source_id", source)
                existing = s.scalar(
                    select(Turnout).where(Turnout.event_id == event, Turnout.unit_id == unit)
                )
                if existing:
                    if existing.source_id != turnout_source:
                        if any(getattr(existing, key) != t.get(key) for key in ["ballots_cast", "registered_voters", "percent"]):
                            raise ValueError("Conflicting event turnout from another contest source")
                        continue
                    existing.ballots_cast = t.get("ballots_cast")
                    existing.registered_voters = t.get("registered_voters")
                    existing.percent = t.get("percent")
                    existing.definition = t.get("definition", existing.definition)
                    continue
                s.add(
                    Turnout(
                        event_id=event,
                        unit_id=unit,
                        ballots_cast=t.get("ballots_cast"),
                        registered_voters=t.get("registered_voters"),
                        percent=t.get("percent"),
                        definition=t.get("definition", "Official reported turnout: total ballots cast / total eligible registration; rounded by source."),
                        source_id=turnout_source,
                    )
                )
            s.add(
                ImportRun(
                    contest_id=cid,
                    created_at=datetime.now(timezone.utc).isoformat(),
                    status=report["status"],
                    report=report,
                )
            )
            reports.append(dict(contest=cid, **report))
    if not reports:
        raise ValueError("No normalized election matched the requested import")
    report_path = ROOT / "data/processed/reconciliation.json"
    all_reports = reports
    if (selected_year is not None or office is not None) and report_path.exists():
        updated = {r["contest"] for r in reports}
        all_reports = [
            r
            for r in json.loads(report_path.read_text())
            if r["contest"] not in updated
        ] + reports
        all_reports.sort(key=lambda r: r["contest"])
    report_path.write_text(json.dumps(all_reports, indent=2) + "\n")
    print(json.dumps(reports, indent=2))
    if any(
        r["status"] not in {"verified", "reported", "secondary"}
        and r.get("coverage") != "statewide_only"
        and (
            r["candidates"]
            or r["contest"] in {"az-2022-governor", "az-2022-attorney-general"}
        )
        for r in reports
    ):
        raise SystemExit("Import contains incomplete reconciliation; see report")
    for r in reports:
        if r["status"] == "reported":
            print(r["contest"], "REPORTED: reviewed county/state discrepancy; see source notes and reconciliation")
        elif r["status"] == "secondary":
            print(r["contest"], "SECONDARY SOURCE: reconciled to a secondary source only, not verified against an official canvass")
        elif r["status"] != "verified":
            print(r["contest"], "INCOMPLETE: source metadata only, no verified results")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--year", type=int, help="Import only this year; preserve other contests"
    )
    parser.add_argument(
        "--office",
        choices=["governor", "attorney-general", "us-senate", "us-house"],
        help="Import only this office; preserve other contests",
    )
    args = parser.parse_args()
    if args.office != "us-house":
        import_all(args.year, args.office)
    if args.office in {None, "us-house"}:
        from scripts.import_house import import_all as import_house

        import_house(args.year)
