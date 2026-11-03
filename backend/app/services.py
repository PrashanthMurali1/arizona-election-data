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
        kind="special" if c.office_id == "us-senate" and c.id.endswith("-special") else e.kind,
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

        if publication.stage == "pre_results" or (
            publication.verification != "provider_report" and utcnow() < RELEASE_AFTER
        ):
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
        and (c.status in {"verified", "reported", "secondary"} or provisional or c.source_id.startswith('historical-canvass-'))
        and all(
            v is not None
            and v.votes is not None
            and v.status == ("source_checked" if provisional else "verified")
            for _, _, _, v in rows
        )
    )
    historical = c.source_id.startswith('historical-canvass-')
    known = [v.votes for _, _, _, v in rows if v is not None and v.votes is not None]
    partial = historical and bool(known) and len(known) != len(rows)
    total = sum(known) if complete or (historical and known) else None
    candidates = [
        CandidateOut(
            id=p.id,
            name=n.name,
            party=p.party_id,
            party_name=party.name,
            write_in=p.write_in,
            category=p.category,
            votes=v.votes if v else None,
            percent=100 * v.votes / total if total and v is not None and v.votes is not None else None,
            status=v.status if v else "unavailable",
        )
        for p, n, party, v in rows
    ]
    candidates.sort(key=lambda r: -(r.votes if r.votes is not None else -1))
    if publication and publication.verification == "provider_report" and publication.result_snapshot_id:
        snapshot = s.get(PublicationSnapshot, publication.result_snapshot_id)
        report = snapshot.payload["provider_report"]
        percentages = (
            {c["name"]: c.get("percent") for c in report["candidates"]}
            if unit.id == "04"
            else report["county_percentages"].get(unit.id, {})
        )
        for candidate in candidates:
            candidate.percent = percentages.get(candidate.name)
    multi_seat = c.office_id in {'state-house', 'state-senate', 'president'}
    if c.office_id in {'us-senate','us-house'}:
        latest_report = s.scalar(select(ImportRun.report).where(ImportRun.contest_id == c.id).order_by(ImportRun.id.desc()).limit(1))
        multi_seat = bool(latest_report and latest_report.get('multi_seat'))
    winner = (
        candidates[0]
        if complete
        and not multi_seat
        and not provisional
        and total
        and (len(candidates) == 1 or candidates[0].votes > candidates[1].votes)
        else None
    )
    if partial and not multi_seat and len(candidates) > 1 and candidates[0].votes is not None:
        # An unallocated statewide write-in is unknown in this county, but its
        # statewide total bounds how much it could change the county outcome.
        missing = [p.id for p, _, _, v in rows if v is None or v.votes is None]
        bounds = list(s.scalars(select(VoteResult.votes).where(
            VoteResult.participation_id.in_(missing), VoteResult.unit_id == c.jurisdiction_id)))
        runner_up = max((x.votes for x in candidates[1:] if x.votes is not None),default=0)
        if len(bounds) == len(missing) and all(x is not None for x in bounds) and candidates[0].votes > runner_up + sum(bounds):
            winner = candidates[0]
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
        status=("unofficial" if provisional else 'reported' if partial or (historical and c.status == 'incomplete') else c.status)
        if complete
        else "reported" if partial else "incomplete",
        total_votes=total,
        candidates=candidates,
        winner=winner,
        turnout=turnout,
        partial=partial,
    )
