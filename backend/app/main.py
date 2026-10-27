from typing import Annotated
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import select
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
)
from .lifecycle import activity
from .services import metadata, results

app = FastAPI(
    title="Arizona Election Explorer",
    version="1.0.0",
    description="Certified election results, reporting units, turnout and provenance. Null values mean unavailable; contest votes are distinct from ballots cast.",
)


def session():
    with SessionLocal() as s:
        yield s


DB = Annotated[Session, Depends(session)]


def contest(s, id):
    c = s.get(Contest, id)
    if not c:
        raise HTTPException(404, "Election contest not found")
    return c


@app.get("/api/health")
def health(s: DB):
    s.execute(select(Contest.id).limit(1))
    return {"status": "ok"}


@app.get("/api/elections", response_model=list[ElectionOut])
def elections(s: DB):
    return [
        metadata(s, c) for c in s.scalars(select(Contest).order_by(Contest.id.desc()))
    ]


@app.get("/api/elections/{id}", response_model=DetailOut)
def election(id: str, s: DB):
    c = contest(s, id)
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
        election=metadata(s, c),
        statewide=results(s, c, s.get(GeographicUnit, c.jurisdiction_id)),
        sources=[SourceOut.model_validate(x, from_attributes=True) for x in sources],
        reconciliation=run.report if run else None,
    )


@app.get("/api/elections/{id}/statewide", response_model=ResultsOut)
def statewide(id: str, s: DB):
    c = contest(s, id)
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
    return election(id, s).sources


@app.get("/api/elections/{id}/activity", response_model=ActivityOut | None)
def election_activity(id: str, s: DB):
    contest(s, id)
    return activity(s, id)


@app.get("/api/elections/{id}/snapshots")
def election_snapshots(id: str, s: DB):
    from .models import PublicationSnapshot

    contest(s, id)
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
            .where(PublicationSnapshot.contest_id == id)
            .order_by(PublicationSnapshot.retrieved_at)
        )
    ]


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
