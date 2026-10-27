from sqlalchemy import select, func
from sqlalchemy.orm import Session
from .models import *
from .schemas import *


def metadata(s: Session, c: Contest):
    e = s.get(ElectionEvent, c.event_id)
    count = s.scalar(
        select(func.count())
        .select_from(Participation)
        .where(Participation.contest_id == c.id)
    )
    counties = s.scalar(
        select(func.count(func.distinct(VoteResult.unit_id)))
        .join(Participation, Participation.id == VoteResult.participation_id)
        .join(GeographicUnit, GeographicUnit.id == VoteResult.unit_id)
        .where(
            Participation.contest_id == c.id,
            GeographicUnit.kind == "county",
            VoteResult.votes.is_not(None),
        )
    )
    return ElectionOut(
        id=c.id,
        year=e.year,
        date=e.date,
        office_id=c.office_id,
        office=s.get(Office, c.office_id).name,
        kind=e.kind,
        status=c.status,
        notes=c.notes,
        county_count=counties,
        candidate_count=count,
        boundary_id=c.boundary_id,
    )


def results(s: Session, c: Contest, unit: GeographicUnit):
    publication = s.get(ElectionPublication, c.id)
    if publication:
        from .lifecycle import utcnow, RELEASE_AFTER

        if publication.stage == "pre_results" or utcnow() < RELEASE_AFTER:
            return ResultsOut(
                geoid=unit.id,
                name=unit.name,
                status="not_released",
                total_votes=None,
                candidates=[],
                winner=None,
                turnout=TurnoutOut(),
            )
    provisional = publication is not None and publication.stage == "unofficial"
    rows = s.execute(
        select(Participation, Candidate, Party, VoteResult)
        .join(Candidate, Candidate.id == Participation.candidate_id)
        .join(Party, Party.id == Participation.party_id)
        .outerjoin(
            VoteResult,
            (VoteResult.participation_id == Participation.id)
            & (VoteResult.unit_id == unit.id),
        )
        .where(Participation.contest_id == c.id)
    ).all()
    complete = (
        bool(rows)
        and (c.status == "verified" or provisional)
        and all(
            v is not None
            and v.votes is not None
            and v.status == ("source_checked" if provisional else "verified")
            for _, _, _, v in rows
        )
    )
    total = sum(v.votes for _, _, _, v in rows) if complete else None
    candidates = [
        CandidateOut(
            id=p.id,
            name=n.name,
            party=p.party_id,
            party_name=party.name,
            write_in=p.write_in,
            category=p.category,
            votes=v.votes if v else None,
            percent=100 * v.votes / total if total else None,
            status=v.status if v else "unavailable",
        )
        for p, n, party, v in rows
    ]
    candidates.sort(key=lambda r: -(r.votes if r.votes is not None else -1))
    winner = (
        candidates[0]
        if complete
        and not provisional
        and total
        and (len(candidates) == 1 or candidates[0].votes > candidates[1].votes)
        else None
    )
    t = s.scalar(
        select(Turnout).where(
            Turnout.event_id == c.event_id, Turnout.unit_id == unit.id
        )
    )
    turnout = (
        TurnoutOut(**{k: getattr(t, k) for k in TurnoutOut.model_fields})
        if t
        else TurnoutOut()
    )
    return ResultsOut(
        geoid=unit.id,
        name=unit.name,
        status=("unofficial" if provisional else "verified")
        if complete
        else "incomplete",
        total_votes=total,
        candidates=candidates,
        winner=winner,
        turnout=turnout,
    )
