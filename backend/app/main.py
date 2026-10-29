from typing import Annotated
from contextlib import asynccontextmanager
import logging
import time
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import (
    Contest,
    GeographicUnit,
    Source,
    Geometry,
    BoundaryVersion,
    ImportRun,
    VoteResult,
    Participation,
    Turnout,
)
from .schemas import (
    ElectionOut,
    ResultsOut,
    DetailOut,
    SourceOut,
    GeometryOut,
    ActivityOut,
    EarlyVotingActivityOut,
    HouseElectionOut,
    HouseOverviewOut,
    HouseDistrictDetailOut,
    HouseDistrictOut,
)
from . import house
from . import early_vote_updates
from .lifecycle import activity, CONTEST, AG_CONTEST
from .services import metadata, results
from .observability import RequestLogging, emit


@asynccontextmanager
async def lifespan(app):
    started = time.monotonic()
    try:
        with SessionLocal() as s:
            s.execute(select(Contest.id).limit(1))
    except Exception as exc:
        emit(logging.CRITICAL, 'backend_startup_failed', exc=exc, outcome='failed')
        raise
    emit(logging.INFO, 'backend_started', outcome='success', duration_ms=round((time.monotonic()-started)*1000))
    try:
        yield
    finally:
        emit(logging.INFO, 'backend_stopped', outcome='success', duration_ms=round((time.monotonic()-started)*1000))

app = FastAPI(
    lifespan=lifespan,
    title="Arizona Election Explorer",
    version="1.0.0",
    description="Certified election results, reporting units, turnout and provenance. Null values mean unavailable; contest votes are distinct from ballots cast.",
)
app.add_middleware(RequestLogging)


def session():
    with SessionLocal() as s:
        yield s


DB = Annotated[Session, Depends(session)]
EARLY_VOTING = "az-2026-early-voting"


def contest(s, id):
    c = s.get(Contest, CONTEST if id == EARLY_VOTING else id)
    if not c:
        raise HTTPException(404, "Election contest not found")
    return c


def early_voting_metadata(s):
    """An event-level catalog view over the retained participation, not a new contest."""
    value = metadata(s, contest(s, EARLY_VOTING)).model_dump()
    value.update(
        id=EARLY_VOTING,
        office_id="early-voting",
        office="Early Voting",
        county_count=s.scalar(select(func.count()).select_from(GeographicUnit).where(GeographicUnit.kind == "county")),
        notes="2026 general-election early-voting participation and returned-ballot party-registration breakdowns. Registration does not indicate candidate choices.",
    )
    return ElectionOut(**value)


@app.get("/api/health")
def health(s: DB):
    s.execute(select(Contest.id).limit(1))
    return {"status": "ok"}


@app.get("/api/elections", response_model=list[HouseElectionOut | ElectionOut])
def elections(s: DB):
    shared = [early_voting_metadata(s)] if s.get(Contest, CONTEST) else []
    return shared + [
        metadata(s, c)
        for c in s.scalars(
            select(Contest)
            .where(Contest.office_id != "us-house", Contest.id.not_in([CONTEST, AG_CONTEST]))
            .order_by(Contest.id.desc())
        )
    ] + house.catalog(s)


@app.get(
    "/api/elections/{id}",
    response_model=HouseOverviewOut | HouseDistrictDetailOut | DetailOut,
)
def election(id: str, s: DB):
    if house.is_overview(id):
        return house.overview(s, id)
    requested_id = id
    c = contest(s, id)
    id = c.id
    if c.office_id == "us-house":
        return house.district_detail(s, c)
    run = s.scalar(
        select(ImportRun)
        .where(ImportRun.contest_id == id)
        .order_by(ImportRun.id.desc())
    )
    sources = [
        s.get(Source, c.source_id),
        s.get(Source, s.get(BoundaryVersion, c.boundary_id).source_id),
    ]
    # Keep the existing official/boundary order; append any supplemental inputs
    # actually attached to this contest's result or turnout records.
    source_ids = set(
        s.scalars(
            select(VoteResult.source_id)
            .join(Participation, Participation.id == VoteResult.participation_id)
            .where(Participation.contest_id == id)
        )
    )
    source_ids.update(
        s.scalars(select(Turnout.source_id).where(Turnout.event_id == c.event_id))
    )
    source_ids.difference_update(source.id for source in sources)
    sources.extend(s.get(Source, source_id) for source_id in sorted(source_ids))
    current_activity = activity(s, id)
    if current_activity:
        existing_ids = {source.id for source in sources}
        sources.extend(
            s.get(Source, source["id"])
            for source in current_activity["sources"]
            if source["id"] not in existing_ids
        )
    return DetailOut(
        election=early_voting_metadata(s) if requested_id == EARLY_VOTING else metadata(s, c),
        statewide=results(s, c, s.get(GeographicUnit, c.jurisdiction_id)),
        sources=[SourceOut.model_validate(x, from_attributes=True) for x in sources],
        reconciliation=run.report if run else None,
    )


@app.get("/api/elections/{id}/statewide", response_model=ResultsOut)
def statewide(id: str, s: DB):
    c = contest(s, id)
    if c.office_id == "us-house":
        raise HTTPException(
            404,
            "House results are district-specific; no statewide House contest exists",
        )
    return results(s, c, s.get(GeographicUnit, c.jurisdiction_id))


@app.get("/api/elections/{id}/counties", response_model=list[ResultsOut])
def counties(id: str, s: DB):
    c = contest(s, id)
    units = s.scalars(
        select(GeographicUnit)
        .join(Geometry, Geometry.unit_id == GeographicUnit.id)
        .where(Geometry.boundary_id == c.boundary_id, GeographicUnit.kind == "county")
    )
    return sorted(
        [results(s, c, u) for u in units],
        key=lambda r: -(r.total_votes if r.total_votes is not None else -1),
    )


@app.get("/api/elections/{id}/counties/{geoid}", response_model=ResultsOut)
def county(id: str, geoid: str, s: DB):
    c = contest(s, id)
    u = s.scalar(
        select(GeographicUnit)
        .join(Geometry, Geometry.unit_id == GeographicUnit.id)
        .where(
            GeographicUnit.id == geoid,
            GeographicUnit.kind == "county",
            Geometry.boundary_id == c.boundary_id,
        )
    )
    if not u:
        raise HTTPException(404, "County not found in contest boundary version")
    return results(s, c, u)


@app.get("/api/elections/{id}/sources", response_model=list[SourceOut])
def sources(id: str, s: DB):
    if house.is_overview(id):
        return house.overview(s, id)["sources"]
    c = contest(s, id)
    if c.office_id == "us-house":
        return house.source_rows(s, [c])
    return election(id, s).sources


@app.get("/api/elections/{id}/activity", response_model=EarlyVotingActivityOut | ActivityOut | None)
def election_activity(id: str, s: DB):
    if house.is_overview(id):
        house.resolve(s, id)
        return None
    current_contest = contest(s, id)
    value = activity(s, current_contest.id)
    if id == EARLY_VOTING and value and value.get('stale'):
        emit(logging.WARNING, 'early_voting_data_stale')
    if id == EARLY_VOTING and value:
        return EarlyVotingActivityOut(**value, revision=early_vote_updates.revision(value))
    return value


@app.get("/api/elections/az-2026-early-voting/updates")
async def early_voting_updates(request: Request):
    return StreamingResponse(
        early_vote_updates.events(request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )


@app.get("/api/elections/{id}/snapshots")
def election_snapshots(id: str, s: DB):
    from .models import PublicationSnapshot

    if house.is_overview(id):
        house.resolve(s, id)
        return []
    current_contest = contest(s, id)
    return [
        dict(
            id=snap.id,
            kind=snap.kind,
            stream=snap.stream,
            stage=snap.stage,
            reported_at=snap.reported_at,
            report_precision=snap.report_precision,
            retrieved_at=snap.retrieved_at,
            release_id=snap.release_id,
            source_id=snap.source_id,
            warnings=snap.warnings,
            payload=snap.payload,
        )
        for snap in s.scalars(
            select(PublicationSnapshot)
            .where(PublicationSnapshot.event_id == current_contest.event_id)
            .order_by(PublicationSnapshot.retrieved_at)
        )
        if snap.contest_id == current_contest.id or snap.payload.get("provider_participation")
    ]


@app.get("/api/elections/{id}/districts", response_model=list[HouseDistrictOut])
def house_districts(id: str, s: DB):
    return house.overview(s, id)["districts"]


@app.get("/api/geography/{boundary_id}", response_model=GeometryOut)
def geography(boundary_id: str, s: DB):
    b = s.get(BoundaryVersion, boundary_id)
    if not b:
        raise HTTPException(404, "Boundary version not found")
    return GeometryOut(
        boundary_id=b.id,
        vintage=b.vintage,
        features=list(
            s.scalars(select(Geometry.feature).where(Geometry.boundary_id == b.id))
        ),
    )
