"""Presidential nominee presentation of retained historical party returns."""
import json
import re
from pathlib import Path
from fastapi import HTTPException
from sqlalchemy import select
from .models import Contest, GeographicUnit, Turnout
from .schemas import DetailOut, ResultsOut, SourceOut, TurnoutOut
from .services import results

ROOT = Path(__file__).resolve().parents[2]


def is_archive(id):
    return bool(re.fullmatch(r'az-\d{4}-historical-president', id))


def context(s, id):
    if not is_archive(id):
        raise HTTPException(404, 'Presidential election not found')
    year = int(id.split('-')[1])
    from scripts.historical_canvasses import contest_id
    path = ROOT / f'data/raw/early-canvasses/{year}.json'
    if not path.is_file():
        raise HTTPException(404, 'Presidential source not found')
    doc = json.loads(path.read_text(encoding='utf-8'))
    raw = next((c for c in doc.get('contests',[]) if c['office_id'] == 'president'),None)
    if raw is None:
        raise HTTPException(404, 'Presidential election not found')
    contest = s.get(Contest, contest_id(year, raw))
    if contest is None:
        raise HTTPException(404, 'Presidential election has not been imported')
    mapping = json.loads((ROOT/'data/raw/early-canvasses/presidential-tickets.json').read_text(encoding='utf-8'))[str(year)]
    selected = []
    for party, ticket in mapping.items():
        rows = [(i, c) for i, c in enumerate(raw['candidates']) if c['party'] == party and not c['write_in']]
        if not rows:
            continue
        # Highest statewide elector, with the same county vector throughout.
        index, candidate = max(rows,key=lambda row: row[1]['votes'] if row[1]['votes'] is not None else -1)
        selected.append((f'{contest.id}-candidate-{index}',ticket,party))
    return doc, contest, selected


def unit_result(s, contest, selected, unit):
    raw = results(s,contest,s.get(GeographicUnit,contest.jurisdiction_id) if unit.id=='04' else unit)
    turnout = s.scalar(select(Turnout).where(Turnout.event_id==contest.event_id,Turnout.unit_id==unit.id))
    turnout_value = TurnoutOut(**{k:getattr(turnout,k) for k in TurnoutOut.model_fields}) if turnout else TurnoutOut()
    by_id = {c.id:c for c in raw.candidates}
    candidates = [by_id[pid].model_copy(update={
        'name': ticket['name'] or f'Unidentified candidate ({party})',
        'category':'presidential_candidate', 'write_in':False,
    }) for pid,ticket,party in selected]
    candidates.sort(key=lambda c: -(c.votes if c.votes is not None else -1))
    known = [c.votes for c in candidates if c.votes is not None]
    total = sum(known) if known else None
    for c in candidates:
        c.percent = 100*c.votes/total if total and c.votes is not None else None
    complete = len(known)==len(candidates)
    return ResultsOut(geoid=unit.id,name=unit.name,status='reported' if known else 'incomplete',
        total_votes=total,candidates=candidates,turnout=turnout_value,partial=bool(known) and not complete,
        winner=candidates[0] if complete and total and (len(candidates)==1 or candidates[0].votes>candidates[1].votes) else None)


def detail(s,id):
    from . import historical
    doc,contest,selected = context(s,id)
    archive = historical.overview(s,id)
    entry = dict(archive['election'],office='President',county_count=14,candidate_count=len(selected),
        boundary_id='county-1966-1982',status='reported')
    sources = list(archive['sources'])
    urls = {source.url for source in sources}
    for _, ticket, party in selected:
        url = ticket.get('tally_source_url') or ticket.get('source_url')
        if url and url not in urls:
            sources.append(SourceOut(id=f'presidential-names-{doc["year"]}-{party}',
                title='Official historical presidential candidate reference',url=url,sha256='',
                notes='Names identify the presidential nominee represented by the party returns.'))
            urls.add(url)
    note = ('Presidential candidate names identify the tickets represented by the official party returns. '
        'Printed party totals are used directly. Where separate elector tallies are printed, the highest statewide '
        'elector tally represents the ticket; the same row supplies county results. Elector votes are never added together. '
        'Elector write-ins that cannot be assigned to a presidential nominee remain in the linked original canvass.')
    entry['notes'] = note
    return DetailOut(election=entry,statewide=unit_result(s,contest,selected,s.get(GeographicUnit,'04')),
        sources=sources,reconciliation={'notes':note,'candidates':[]})


def counties(s,id):
    from scripts.historical_canvasses import county_units
    doc,contest,selected = context(s,id)
    return [unit_result(s,contest,selected,s.get(GeographicUnit,g)) for g in sorted(county_units(doc['year']))]
