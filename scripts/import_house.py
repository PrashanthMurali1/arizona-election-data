"""Transactionally import real House contests and plan-qualified districts."""

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sqlalchemy import delete, select
from backend.app.database import SessionLocal
from backend.app.models import (
    BoundaryVersion,
    Candidate,
    Contest,
    ElectionEvent,
    GeographicUnit,
    Geometry,
    ImportRun,
    Office,
    Participation,
    Party,
    Source,
    Turnout,
    VoteResult,
)
from scripts.normalize_house import normalize


def import_all(year=None, specials_only=False):
    # Revalidate the original snapshots and independent references before any mutation.
    elections = normalize()
    if year is not None:
        elections = [e for e in elections if e["year"] == year]
    if specials_only:
        elections = [e for e in elections if e["kind"] == "special"]
    if not elections:
        raise ValueError("No House election matched the requested year")
    reports = []
    with SessionLocal.begin() as s:
        s.merge(Office(id="us-house", name="U.S. House"))
        s.flush()
        for plan in [2012, 2022]:
            source = json.loads(
                (
                    ROOT / f"data/geography/az-congressional-{plan}-source.json"
                ).read_text()
            )
            path = ROOT / f"data/geography/az-congressional-{plan}.geojson"
            if (
                hashlib.sha256(path.read_bytes()).hexdigest()
                != source["geojson_sha256"]
            ):
                raise ValueError("House geography checksum mismatch")
            geo = json.loads(path.read_text())
            if len(geo["features"]) != 9:
                raise ValueError("Each congressional plan must contain nine districts")
            s.merge(
                Source(
                    **{k: source[k] for k in ["id", "title", "url", "sha256", "notes"]}
                )
            )
            s.flush()
            boundary = f"congressional-{plan}"
            s.merge(
                BoundaryVersion(
                    id=boundary, vintage=source["vintage"], source_id=source["id"]
                )
            )
            for feature in geo["features"]:
                props = feature["properties"]
                s.merge(
                    GeographicUnit(
                        id=props["geoid"],
                        name=props["name"],
                        kind="congressional_district",
                    )
                )
            s.flush()
            for feature in geo["features"]:
                unit = feature["properties"]["geoid"]
                existing = s.scalar(
                    select(Geometry).where(
                        Geometry.unit_id == unit, Geometry.boundary_id == boundary
                    )
                )
                if existing:
                    existing.feature = feature
                else:
                    s.add(Geometry(unit_id=unit, boundary_id=boundary, feature=feature))
        for event in elections:
            for source in [event["source"], *event.get("additional_sources", [])]:
                s.merge(Source(**source))
            old_event = s.get(ElectionEvent, event["event_id"])
            if old_event and (
                old_event.date != event["date"] or old_event.kind != event["kind"]
            ):
                raise ValueError(
                    "House election conflicts with an existing election event"
                )
            s.merge(
                ElectionEvent(
                    id=event["event_id"],
                    year=event["year"],
                    date=event["date"],
                    kind=event["kind"],
                )
            )
            s.flush()
            for contest in event["contests"]:
                cid = contest["id"]
                s.merge(
                    Contest(
                        id=cid,
                        event_id=event["event_id"],
                        office_id="us-house",
                        jurisdiction_id=contest["unit_id"],
                        boundary_id=f"congressional-{event['plan']}",
                        source_id=event["source"]["id"],
                        status=contest["status"],
                        notes=event["notes"],
                    )
                )
                s.flush()
                ids = list(
                    s.scalars(
                        select(Participation.id).where(Participation.contest_id == cid)
                    )
                )
                s.execute(
                    delete(VoteResult).where(VoteResult.participation_id.in_(ids))
                )
                s.execute(delete(Participation).where(Participation.contest_id == cid))
                s.flush()
                for candidate in contest["candidates"]:
                    party = candidate["party"]
                    if not s.get(Party, party):
                        s.add(
                            Party(
                                id=party,
                                name={
                                    "DEM": "Democratic",
                                    "REP": "Republican",
                                    "GRN": "Green",
                                    "LBT": "Libertarian",
                                    "IND": "Independent",
                                    "NONE": "No affiliation",
                                    "NOL": "No Labels",
                                }.get(party, f"{party} (as reported)"),
                            )
                        )
                    s.merge(Candidate(id=candidate["id"], name=candidate["name"]))
                    s.flush()
                    s.add(
                        Participation(
                            id=candidate["id"],
                            contest_id=cid,
                            candidate_id=candidate["id"],
                            party_id=party,
                            write_in=candidate["write_in"],
                            category=candidate["category"],
                        )
                    )
                    s.flush()
                    for unit, value in {
                        contest["unit_id"]: candidate["votes"],
                        **candidate["county_votes"],
                    }.items():
                        s.add(
                            VoteResult(
                                participation_id=candidate["id"],
                                unit_id=unit,
                                votes=value,
                                source_id=(
                                    candidate["district_source_id"]
                                    if unit == contest["unit_id"]
                                    else event.get("county_source_ids", {}).get(
                                        unit, candidate["county_source_id"]
                                    )
                                ),
                                status=(
                                    (
                                        "verified"
                                        if contest["status"] == "verified"
                                        else "source_checked"
                                    )
                                    if value is not None
                                    else "unavailable"
                                ),
                            )
                        )
                s.add(
                    ImportRun(
                        contest_id=cid,
                        created_at=datetime.now(timezone.utc).isoformat(),
                        status=contest["status"],
                        report=contest["reconciliation"],
                    )
                )
                reports.append({"contest": cid, **contest["reconciliation"]})
            # Only genuinely district-specific official metrics may be added.
            for district, values in event.get("district_turnout", {}).items():
                unit = f"az-cd-{event['plan']}-{int(district):02}"
                existing = s.scalar(
                    select(Turnout).where(
                        Turnout.event_id == event["event_id"], Turnout.unit_id == unit
                    )
                )
                if not existing:
                    s.add(Turnout(event_id=event["event_id"], unit_id=unit, **values))
                elif any(
                    getattr(existing, key) != value for key, value in values.items()
                ):
                    raise ValueError(
                        "Existing district turnout differs; review the source correction explicitly"
                    )
    out = ROOT / "data/processed/us-house/reconciliation.json"
    if year is not None and out.exists():
        replaced = {r["contest"] for r in reports}
        reports = [
            r for r in json.loads(out.read_text()) if r["contest"] not in replaced
        ] + reports
    out.write_text(json.dumps(reports, indent=2, ensure_ascii=False) + "\n")
    print(
        "House import:",
        len(reports),
        "district contests;",
        sum(r.get("kind") == "provider_results" for r in reports),
        "civicAPI reports;",
        sum(r["status"] == "verified" for r in reports),
        "county-reconciled;",
        sum(r["status"] == "incomplete" for r in reports),
        "incomplete",
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int)
    parser.add_argument(
        "--specials-only",
        action="store_true",
        help="import only the 2018 CD8 and 2025 CD7 special-election records",
    )
    args = parser.parse_args()
    import_all(args.year, specials_only=args.specials_only)
