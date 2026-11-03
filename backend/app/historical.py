"""Map-optional historical district archives, independent of modern House plans."""
import re
from fastapi import HTTPException
from sqlalchemy import select, func
from .models import Contest, ElectionEvent, Office, Source, ImportRun, GeographicUnit, Participation
from .schemas import SourceOut
from .services import results


def groups(session):
    grouped = {}
    for c in session.scalars(select(Contest).where(Contest.id.like('az-%-historical-%')).order_by(Contest.id)):
        grouped.setdefault((c.event_id, c.office_id), []).append(c)
    return grouped


def archive_id(event, office):
    return f'az-{event.year}-historical-{office}'


def entry(session, event, office, contests):
    return dict(id=archive_id(event, office), year=event.year, date=event.date,
        office_id=office, office=session.get(Office, office).name, kind=event.kind,
        status='reported' if all(c.status in {'verified', 'reported'} for c in contests) else 'incomplete',
        notes='Official historical canvass. District results are separate contests; historical district maps are unavailable.',
        county_count=0, candidate_count=session.scalar(select(func.count()).select_from(Participation).where(Participation.contest_id.in_([c.id for c in contests]))),
        boundary_id=contests[0].boundary_id, district_count=len(contests),
        selection_label=f'{event.year} General', district_label=None)


def catalog(session):
    return [entry(session, session.get(ElectionEvent, event), office, contests)
            for (event, office), contests in groups(session).items()]


def overview(session, id):
    for (event_id, office), contests in groups(session).items():
        event = session.get(ElectionEvent, event_id)
        if archive_id(event, office) != id:
            continue
        def district_key(c):
            label = session.get(GeographicUnit, c.jurisdiction_id).name.removeprefix('District ')
            parts = re.match(r'(\d+)(.*)', label)
            return (int(parts[1]), parts[2])
        rows = []
        for c in sorted(contests, key=district_key):
            unit = session.get(GeographicUnit, c.jurisdiction_id)
            run = session.scalar(select(ImportRun).where(ImportRun.contest_id == c.id).order_by(ImportRun.id.desc()))
            value = results(session, c, unit)
            # Neither chamber is assumed to have a single seat historically.
            if office in {'state-house', 'state-senate'}:
                value.winner = None
            rows.append(dict(district=unit.name.removeprefix('District '), contest_id=c.id,
                results=value, page=run.report.get('page') if run else None, notes=c.notes))
        source_ids = sorted({c.source_id for c in contests})
        return dict(election=entry(session, event, office, contests), contests=rows,
            map_available=False, multi_seat=office in {'state-house', 'state-senate'},
            sources=[SourceOut.model_validate(session.get(Source, sid), from_attributes=True) for sid in source_ids])
    raise HTTPException(404, 'Historical election archive not found')
