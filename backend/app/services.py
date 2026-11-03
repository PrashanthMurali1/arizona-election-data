from sqlalchemy import select, func
from sqlalchemy.orm import Session
from .models import *
from .schemas import *


def turnout_with_participation(turnout: TurnoutOut, votes: int | None):
    """Use the published turnout first, otherwise show calculated turnout."""
    if turnout.percent is not None or not turnout.registered_voters:
        return turnout
    if turnout.ballots_cast is not None:
        return turnout.model_copy(update=dict(percent=100*turnout.ballots_cast/turnout.registered_voters,
            basis='calculated_ballots',definition='Calculated turnout: official ballots cast / registered voters x 100. ' + turnout.definition))
    if votes is None or votes > turnout.registered_voters:
        return turnout
    return turnout.model_copy(update=dict(percent=100*votes/turnout.registered_voters,
        votes_cast=votes,basis='contest_votes',
        definition=f'Calculated turnout: {votes:,} reported votes / {turnout.registered_voters:,} registered voters x 100. '
        'Counts votes in this race; blank and invalid ballots are not included. '
        + (turnout.definition if 'Statewide registration calculated' in turnout.definition else '')))


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
    latest_report = None
    if c.source_id.startswith('historical-canvass-'):
        latest_report = s.scalar(select(ImportRun.report).where(ImportRun.contest_id == c.id).order_by(ImportRun.id.desc()).limit(1))
    groups = (latest_report or {}).get('county_groups', []) if unit.kind == 'county' else []
    groups = [g for g in groups if unit.id in g['county_votes']]
    # Some compilations publish combined county totals, with individual
    # candidates available only statewide. Substitute the published groups at
    # county level without allocating their votes or double-counting members.
    grouped_ids = {f'{c.id}-candidate-{i}' for g in groups if unit.id in g['county_votes'] for i in g['members']}
    rows = [row for row in rows if row[0].id not in grouped_ids]
    complete = (
        bool(rows or groups)
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
    group_votes = sum(g['county_votes'][unit.id] for g in groups if unit.id in g['county_votes'])
    partial = historical and bool(known) and len(known) != len(rows)
    missing_regular = any(not p.write_in and (v is None or v.votes is None) for p, _, _, v in rows)
    total = sum(known) + group_votes if complete or (historical and (known or groups) and not missing_regular) else None
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
    candidates.extend(CandidateOut(id=f'{c.id}-county-group-{i}', name=g['name'],
        party=g['party'], party_name=f"{g['party']} (combined)", write_in=False,
        category='county_group', votes=g['county_votes'][unit.id],
        percent=100*g['county_votes'][unit.id]/total if total else None, status='verified')
        for i,g in enumerate(groups) if unit.id in g['county_votes'])
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
        latest_report = latest_report or s.scalar(select(ImportRun.report).where(ImportRun.contest_id == c.id).order_by(ImportRun.id.desc()).limit(1))
        multi_seat = bool(latest_report and latest_report.get('multi_seat'))
    winner = (
        candidates[0]
        if complete
        and candidates[0].category != 'county_group'
        and not multi_seat
        and not provisional
        and total
        and (len(candidates) == 1 or candidates[0].votes > candidates[1].votes)
        else None
    )
    if partial and not multi_seat and len(candidates) > 1 and candidates[0].votes is not None and candidates[0].category != 'county_group':
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
        TurnoutOut(**{k: getattr(t, k) for k in TurnoutOut.model_fields if hasattr(t,k)})
        if t
        else TurnoutOut()
    )
    if historical and not multi_seat:
        turnout = turnout_with_participation(turnout,total)
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
