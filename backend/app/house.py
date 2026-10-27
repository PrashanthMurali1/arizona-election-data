"""House event overviews combine independent district contests without pooling candidates."""

import re
from sqlalchemy import select
from fastapi import HTTPException
from .models import (
    Contest,
    ElectionEvent,
    Office,
    Participation,
    ImportRun,
    GeographicUnit,
    Geometry,
    Source,
    BoundaryVersion,
    VoteResult,
    Turnout,
)
from .schemas import ElectionOut, ResultsOut, TurnoutOut, SourceOut
from .services import metadata, results


def overview_id(event, contests):
    if event.kind == "special":
        district = contests[0].jurisdiction_id.rsplit("-", 1)[1]
        return f"az-{event.year}-us-house-special-{district}"
    return f"az-{event.year}-us-house"


def groups(s):
    grouped = {}
    for contest in s.scalars(
        select(Contest)
        .where(Contest.office_id == "us-house")
        .order_by(Contest.jurisdiction_id)
    ):
        grouped.setdefault(contest.event_id, []).append(contest)
    return grouped


def catalog_entry(s, event, contests):
    special = event.kind == "special"
    district = (
        s.get(GeographicUnit, contests[0].jurisdiction_id).name if special else None
    )
    label = (
        f"{event.year} Special — {district} — {event.date}"
        if special
        else f"{event.year} General"
    )
    return dict(
        id=overview_id(event, contests),
        year=event.year,
        date=event.date,
        office_id="us-house",
        office="U.S. House",
        kind=event.kind,
        status=(
            "civicapi"
            if special
            else "verified"
            if all(c.status == "verified" for c in contests)
            else "incomplete"
        ),
        notes=(
            f"{len(contests)} independent congressional district contest. "
            f"Select {district} to view its civicAPI-reported candidate results. "
            f"This is a civicAPI report, not an official canvass result. {contests[0].notes}"
            if special
            else f"{len(contests)} independent congressional district contests. Select a district to view its own candidate records. Shares and winners require complete verification. {contests[0].notes}"
        ),
        county_count=0,
        district_count=len(contests),
        candidate_count=sum(metadata(s, c).candidate_count for c in contests),
        boundary_id=contests[0].boundary_id,
        selection_label=label,
        district_label=district,
    )


def catalog(s):
    return [
        catalog_entry(s, s.get(ElectionEvent, event_id), contests)
        for event_id, contests in groups(s).items()
    ]


def is_overview(id):
    return bool(re.fullmatch(r"az-\d{4}-us-house(?:-special-\d{2})?", id))


def resolve(s, id):
    for event_id, contests in groups(s).items():
        event = s.get(ElectionEvent, event_id)
        if overview_id(event, contests) == id:
            return event, contests
    raise HTTPException(404, "House election overview not found")


def report(s, contest):
    run = s.scalar(
        select(ImportRun)
        .where(ImportRun.contest_id == contest.id)
        .order_by(ImportRun.id.desc())
    )
    return run.report if run else None


def source_rows(s, contests):
    ids = {s.get(BoundaryVersion, c.boundary_id).source_id for c in contests} | {
        c.source_id for c in contests
    }
    for c in contests:
        ids.update(
            s.scalars(
                select(VoteResult.source_id)
                .join(Participation, Participation.id == VoteResult.participation_id)
                .where(Participation.contest_id == c.id)
            )
        )
        ids.update((report(s, c) or {}).get("additional_source_ids", []))
        ids.update(
            s.scalars(
                select(Turnout.source_id).where(
                    Turnout.event_id == c.event_id, Turnout.unit_id == c.jurisdiction_id
                )
            )
        )
    return [
        SourceOut.model_validate(s.get(Source, id), from_attributes=True)
        for id in sorted(ids)
    ]


def overview(s, id):
    event, contests = resolve(s, id)
    entry = catalog_entry(s, event, contests)
    if len({c.boundary_id for c in contests}) != 1:
        raise HTTPException(500, "House event has incompatible district plans")
    contest_by_unit = {c.jurisdiction_id: c for c in contests}
    districts = []
    units = s.scalars(
        select(GeographicUnit)
        .join(Geometry, Geometry.unit_id == GeographicUnit.id)
        .where(Geometry.boundary_id == entry["boundary_id"])
        .order_by(GeographicUnit.id)
    )
    for unit in units:
        contest = contest_by_unit.get(unit.id)
        value = (
            results(s, contest, unit)
            if contest
            else ResultsOut(
                geoid=unit.id,
                name=unit.name,
                status="not_contested",
                total_votes=None,
                candidates=[],
                winner=None,
                turnout=TurnoutOut(
                    definition="Not contested in this special election."
                ),
            )
        )
        districts.append(
            {
                **value.model_dump(),
                "contest_id": contest.id if contest else None,
                "contested": contest is not None,
            }
        )
    return dict(
        election=entry,
        districts=districts,
        default_district=contests[0].jurisdiction_id,
        sources=source_rows(s, contests),
        reconciliation={
            "status": entry["status"],
            "district_count": len(contests),
            "reports": {c.jurisdiction_id: report(s, c) for c in contests},
        },
    )


def district_detail(s, contest):
    return dict(
        election=metadata(s, contest),
        district=results(s, contest, s.get(GeographicUnit, contest.jurisdiction_id)),
        sources=source_rows(s, [contest]),
        reconciliation=report(s, contest),
    )
