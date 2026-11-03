"""Validate retained canvass transcriptions and import historical archive records.

Run with --year to scope an import. Existing reviewed statewide contests retain
their county-level evidence; their printed totals are audited, never overwritten.
"""
import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sqlalchemy import delete, select
from backend.app.database import SessionLocal
from backend.app.models import (
    BoundaryVersion, Candidate, Contest, ElectionEvent, GeographicUnit,
    ImportRun, Office, Participation, Party, Source, VoteResult,
    Geometry, Turnout,
)
from scripts.normalize import COUNTIES

OFFICES = {
    'us-house': 'U.S. House', 'us-senate': 'U.S. Senate',
    'president': 'Presidential electors', 'governor': 'Governor',
    'attorney-general': 'Attorney General', 'secretary-of-state': 'Secretary of State',
    'state-house': 'State House', 'state-senate': 'State Senate',
}
DISTRICT_OFFICES = {'us-house', 'state-house', 'state-senate', 'president'}
PARTIES = {'DEM': 'Democratic', 'REP': 'Republican', 'LBT': 'Libertarian',
           'NONE': 'No affiliation', 'IND': 'Independent', 'SWP': 'Socialist Workers'}
PARTY_ALIASES = {'L': 'LBT', 'I': 'IND', 'N': 'NONE', 'ND': 'NONE', 'WI': 'NONE',
                 'SW': 'SWP', 'SA': 'SAB', 'NP': 'NON', 'NPD': 'NONE'}
# Explicit source spellings of candidates already present in reviewed datasets.
# These aliases affect matching only; both original spellings remain in the audit.
NAME_ALIASES = {'johnrjackwilliams': 'jackwilliams', 'raulhcastro': 'raulcastro',
                'russwilliams': 'russellwilliams', 'evanevmecham': 'evanmecham'}
RAW = ROOT / 'data/raw/historical-canvasses'
EARLY_RAW = ROOT / 'data/raw/early-canvasses'
OUT = ROOT / 'data/processed/historical-canvasses'


def county_units(year):
    return {g for g, _ in COUNTIES if (year >= 1983 or g != '04012') and (year >= 1910 or g != '04011')}


def derive_registration_total(document):
    turnout = document.get('turnout', {})
    state = turnout.get('04', {})
    units = county_units(document['year'])
    if state.get('registered_voters') is not None or not all(turnout.get(g, {}).get('registered_voters') is not None for g in units):
        return document
    total = sum(turnout[g]['registered_voters'] for g in units)
    derived = dict(state, registered_voters=total, registered_voters_basis='sum_of_counties',
        definition=f'Statewide registration calculated from all {len(units)} county registration totals: {total:,}.')
    if document.get('registration_reference'):
        derived['reference'] = 'registration_history'
    return dict(document, turnout=dict(turnout, **{'04':derived}))


def party_id(label, year):
    # Abbreviations change meaning across eras; early NP remains as printed.
    if year < 1966 and label in {'NP', 'L', 'SW'}:
        return label
    return {'R': 'REP', 'Rep.': 'REP', 'D': 'DEM', 'None': 'NONE', 'Ind.': 'IND'}.get(label, PARTY_ALIASES.get(label, label))


def document_paths():
    return sorted([*RAW.glob('[12][0-9][0-9][0-9]*.json'), *EARLY_RAW.glob('[12][0-9][0-9][0-9]*.json')])


def document_sources(document):
    sources = {document['source_path']: {'sha256': document['source_sha256']}}
    for source in document.get('additional_sources', []):
        path = source.get('path', source.get('source_path'))
        digest = source.get('sha256', source.get('source_sha256'))
        if path in sources and sources[path]['sha256'] != digest:
            raise ValueError('Conflicting source checksums')
        sources[path] = dict(source, sha256=digest)
    return sources


def document_source_id(document, path=None):
    kind = document.get('kind', 'general')
    sid = f"historical-canvass-{document['year']}" + (f'-{kind}' if kind != 'general' else '')
    if path and path != document['source_path']:
        sid += '-supplement-' + document_sources(document)[path]['sha256'][:12]
    return sid


def contest_id(year, contest, kind='general'):
    office = contest['office_id']
    suffix = f'-{kind}' if kind != 'general' else ''
    if office not in DISTRICT_OFFICES:
        return f'az-{year}-{office}{suffix}'
    label = re.sub(r'[^A-Za-z0-9-]+', '-', contest['district']).strip('-')
    return f"az-{year}-historical-{office}-district-{label}{suffix}"


def validate_document(document, source_root=ROOT):
    sources = document_sources(document)
    for path, info in sources.items():
        source = (source_root / path).resolve()
        if not source.is_relative_to(source_root.resolve()):
            raise ValueError('Source must be within the source root')
        if hashlib.sha256(source.read_bytes()).hexdigest() != info['sha256']:
            raise ValueError(f'Source checksum mismatch: {source}')
    year = document['year']
    if not isinstance(year, int) or not re.fullmatch(rf'{year}-\d{{2}}-\d{{2}}', document['date']):
        raise ValueError('Invalid election date')
    if document.get('kind', 'general') not in {'general', 'special'}:
        raise ValueError('Only general and special candidate elections are supported')
    units = county_units(year)
    for geoid, turnout in document.get('turnout', {}).items():
        if geoid not in units | {'04'}:
            raise ValueError('Unknown turnout reporting unit')
        if turnout.get('source_path', document['source_path']) not in sources:
            raise ValueError('Turnout refers to an unretained source')
        for key in ['ballots_cast', 'registered_voters']:
            value = turnout.get(key)
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError('Invalid turnout count')
        if turnout.get('percent') is not None and not 0 <= turnout['percent'] <= 100:
            raise ValueError('Invalid turnout percentage')
    seen = set()
    for contest in document['contests']:
        office = contest['office_id']
        if office not in OFFICES:
            raise ValueError(f'Unknown office: {office}')
        district = contest.get('district')
        if (office in DISTRICT_OFFICES) != bool(district):
            raise ValueError('District identity does not match office')
        if district and (not isinstance(district, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 .,'()&-]*", district)):
            raise ValueError('Invalid historical district label')
        if contest.get('source_path', document['source_path']) not in sources:
            raise ValueError('Contest refers to an unretained source')
        cid = contest_id(year, contest, document.get('kind', 'general'))
        if cid in seen:
            raise ValueError(f'Duplicate contest: {cid}')
        seen.add(cid)
        if type(contest['page']) is not int or contest['page'] < 1:
            raise ValueError('Source page must be a positive integer')
        names = set()
        for candidate in contest['candidates']:
            name = candidate['name'].strip()
            identity = ('source-row', candidate['source_row_id']) if candidate.get('source_row_id') else ('name', name)
            if not name or identity in names or not candidate['party']:
                raise ValueError(f'Missing or duplicate candidate in {cid}')
            names.add(identity)
            if type(candidate['write_in']) is not bool:
                raise ValueError('Write-in flag must be explicit')
            cells = candidate.get('county_votes', {})
            if set(cells) - units:
                raise ValueError('Unknown county or county did not yet exist')
            for value in [candidate['votes'], *cells.values()]:
                if value is not None and (type(value) is not int or value < 0):
                    raise ValueError('Votes must be nonnegative integers or null')
        if not names:
            raise ValueError(f'Empty candidate roster: {cid}')
        grouped = set()
        for group in contest.get('county_groups', []):
            members = group['members']
            if (not group['name'] or not group['party'] or not members
                    or any(type(i) is not int or not 0 <= i < len(contest['candidates']) for i in members)
                    or len(set(members)) != len(members) or grouped.intersection(members)):
                raise ValueError('Invalid or overlapping county group')
            grouped.update(members)
            if set(group['county_votes']) - units or any(type(n) is not int or n < 0 for n in group['county_votes'].values()):
                raise ValueError('Invalid county group votes')
            if any(contest['candidates'][i].get('county_votes') for i in members):
                raise ValueError('County group cannot duplicate individual county votes')
    if set(document.get('absent_offices', [])) & {c['office_id'] for c in document['contests']}:
        raise ValueError('An office cannot be absent and present')
    return document


def reconcile_contest(contest, year):
    units = county_units(year)
    candidates = []
    for c in contest['candidates']:
        cells = c.get('county_votes', {})
        complete = set(cells) == units and all(v is not None for v in cells.values())
        total = sum(v for v in cells.values() if v is not None) if cells else None
        candidates.append({
            'candidate': c['name'], 'official_total': c['votes'],
            'official_statewide': c['votes'],
            'county_sum': total, 'county_coverage': len(cells),
            'missing_counties': sorted(g for g in units if cells.get(g) is None),
            'difference': total - c['votes'] if complete and c['votes'] is not None else None,
        })
    all_totals = all(c['votes'] is not None for c in contest['candidates'])
    # Reported means the printed contest totals were reviewed; county verification
    # is deliberately stricter and never inferred from missing cells.
    verified = all_totals and all(c['difference'] == 0 for c in candidates)
    return {
        'status': 'verified' if verified else 'reported' if all_totals else 'incomplete',
        'page': contest['page'], 'district': contest.get('district'),
        'candidates': candidates, 'county_count': len(units),
        'coverage': 'county' if verified else 'contest_totals',
        'multi_seat': contest.get('multi_seat', contest['office_id'] in {'state-house', 'state-senate', 'president'}),
        'result_basis': 'presidential-electors' if contest['office_id'] == 'president' else 'candidate-votes',
        'notes': contest.get('notes', ''),
        **({'county_groups': contest['county_groups']} if contest.get('county_groups') else {}),
    }


def ensure_county_geography(session, year):
    """Scoped statewide imports need the same retained county geometry as bootstrap."""
    old = year < 1983
    boundary = 'county-1966-1982' if old else 'county-2022'
    expected = {g for g, _ in COUNTIES if not old or g != '04012'}
    existing = set(session.scalars(select(Geometry.unit_id).where(Geometry.boundary_id == boundary)))
    if existing == expected:
        return
    geo_path = ROOT / ('data/geography/az-counties-1966-1982.geojson' if old else 'data/geography/az-counties-2022.geojson')
    info_path = ROOT / ('data/geography/az-counties-1966-1982-source.json' if old else 'data/geography/source.json')
    info = json.loads(info_path.read_text(encoding='utf-8'))
    geo = json.loads(geo_path.read_text(encoding='utf-8'))
    if {f['properties']['geoid'] for f in geo['features']} != expected:
        raise ValueError('County geography does not match the election period')
    if old and hashlib.sha256(geo_path.read_bytes()).hexdigest() != info['sha256']:
        raise ValueError('Historical county geography checksum mismatch')
    sid = 'census-2022-pre-1983' if old else 'census-2022'
    session.merge(Source(id=sid, title='U.S. Census Bureau — county boundaries' + (' with pre-1983 Yuma reconstruction' if old else ''),
        url=info['url'], sha256=info['sha256'], notes=info['notes']))
    session.flush()
    session.merge(BoundaryVersion(id=boundary, vintage=info['vintage'], source_id=sid))
    session.flush()
    for feature in geo['features']:
        geoid = feature['properties']['geoid']
        if geoid not in existing:
            session.add(Geometry(unit_id=geoid, boundary_id=boundary, feature=feature))
    session.flush()


def import_documents(documents, session_factory=SessionLocal, source_root=ROOT):
    documents = [validate_document(derive_registration_total(d), source_root) for d in documents]
    reports = []
    with session_factory.begin() as session:
        for doc in documents:
            year = doc['year']
            kind = doc.get('kind', 'general')
            event_id = doc.get('event_id', f'az-{year}-{kind}')
            for path, info in document_sources(doc).items():
                sid = document_source_id(doc, path)
                url = f'/api/historical-sources/{sid}'
                session.merge(Source(id=sid,
                    title=info.get('title') or (doc.get('source_title') if path == doc['source_path'] else None) or f'Arizona Secretary of State — {year} official canvass' + (' (supplement)' if path != doc['source_path'] else ''),
                    url=url, sha256=info['sha256'],
                    notes=info.get('notes') or (doc.get('source_notes') if path == doc['source_path'] else None) or 'Official returns supplied by the project maintainer. Candidate totals visually transcribed from the cited pages. County coverage varies by contest; missing figures remain unavailable.'))
            source_id = document_source_id(doc)
            registration_source_id = f"historical-registration-{year}"
            if doc.get('registration_reference'):
                reference = doc['registration_reference']
                session.merge(Source(id=registration_source_id,title=reference['title'],url=reference['url'],sha256='',notes=reference['notes']))
            prior_event = session.get(ElectionEvent, event_id)
            if prior_event and (prior_event.date != doc['date'] or prior_event.kind != kind):
                raise ValueError('Conflicting election date or kind')
            session.merge(ElectionEvent(id=event_id, year=year, date=doc['date'], kind=kind))
            session.merge(GeographicUnit(id='04', name='Arizona', kind='state'))
            for geoid, name in COUNTIES:
                if geoid in county_units(year):
                    session.merge(GeographicUnit(id=geoid, name=name, kind='county'))
            session.flush()
            if any(c['office_id'] not in DISTRICT_OFFICES for c in doc['contests']):
                ensure_county_geography(session, year)
            boundary = f'historical-results-{year}'
            session.merge(BoundaryVersion(id=boundary, vintage=year, source_id=source_id))
            session.flush()
            for geoid, value in doc.get('turnout', {}).items():
                turnout = session.scalar(select(Turnout).where(Turnout.event_id == event_id, Turnout.unit_id == geoid))
                if turnout is None:
                    turnout = Turnout(event_id=event_id,unit_id=geoid)
                    session.add(turnout)
                for key in ['ballots_cast','registered_voters','percent']:
                    setattr(turnout,key,value.get(key))
                turnout.definition = value.get('definition','Official election-wide turnout as printed.') + (f" Source PDF page {value['page']}." if value.get('page') else '')
                turnout.source_id = registration_source_id if value.get('reference') == 'registration_history' else document_source_id(doc,value.get('source_path'))
            for contest in doc['contests']:
                office = contest['office_id']
                source_path = contest.get('source_path', doc['source_path'])
                source_id = document_source_id(doc, source_path)
                cid = contest_id(year, contest, kind)
                report = reconcile_contest(contest, year)
                report.update(contest=cid, source_id=source_id, source_sha256=document_sources(doc)[source_path]['sha256'],
                    supplemental_source_ids=[document_source_id(doc, p) for p in document_sources(doc) if p != source_path] + ([registration_source_id] if doc.get('registration_reference') else []))
                existing = session.get(Contest, cid)
                # A retained supplement can correct this document's own rows.
                # Independently reviewed datasets still keep their evidence.
                owned_sources = {document_source_id(doc, p) for p in document_sources(doc)}
                if existing and existing.source_id not in owned_sources:
                    old_rows = session.execute(select(Candidate.name, Participation.party_id, Participation.write_in, VoteResult.votes)
                        .join(Participation, Participation.id == VoteResult.participation_id)
                        .join(Candidate, Candidate.id == Participation.candidate_id)
                        .where(Participation.contest_id == cid, VoteResult.unit_id == '04')).all()
                    report['existing_evidence_preserved'] = True
                    def key(name):
                        value = re.sub(r'[^a-z0-9]', '', name.lower())
                        return NAME_ALIASES.get(value, value)
                    previous = {key(r.name): {'party': r.party_id, 'write_in': r.write_in, 'votes': r.votes} for r in old_rows}
                    current = {key(c['name']): {'party': party_id(c['party'], year),
                        'write_in': c['write_in'], 'votes': c['votes']} for c in contest['candidates']}
                    report['existing_totals_match'] = set(previous) == set(current) and all(
                        previous[name]['votes'] == current[name]['votes'] for name in previous)
                    report['candidate_metadata_matches'] = previous == current
                    report['previous_candidates'] = previous
                    report['canvass_candidates'] = current
                    old_run = session.scalar(select(ImportRun).where(ImportRun.contest_id == cid).order_by(ImportRun.id.desc()))
                    combined = dict(old_run.report) if old_run else dict(report)
                    combined['canvass_audit'] = dict(report)
                    combined['supplemental_source_ids'] = sorted(set(combined.get('supplemental_source_ids', [])) | {source_id} | set(report['supplemental_source_ids']))
                    if not report['existing_totals_match'] or not report['candidate_metadata_matches']:
                        existing.status = 'reported'
                    warning = ' Supplied canvass audit: existing reviewed county evidence is preserved; see the reconciliation report for candidate metadata and total comparisons.'
                    if warning not in existing.notes:
                        existing.notes += warning
                    combined['status'] = existing.status
                    session.add(ImportRun(contest_id=cid, created_at=datetime.now(timezone.utc).isoformat(),
                        status=existing.status, report=combined))
                    reports.append(report)
                    continue
                session.merge(Office(id=office, name=OFFICES[office]))
                district = contest.get('district')
                unit = '04' if not district else cid.removesuffix('-special').replace('-historical-', '-')
                if district:
                    session.merge(GeographicUnit(id=unit, name=f'District {district}', kind='historical_district'))
                session.flush()
                notes = f"Retained {year} results source, PDF page {contest['page']}. "
                if report['multi_seat']:
                    notes += 'Multiple-member or elector contest; no single-winner inference is made. Vote shares are shares of candidate votes, not voters. '
                if office == 'president':
                    notes += 'Presidential elector results as printed; individual elector tallies are not combined into inferred presidential ticket votes. '
                notes += doc.get('notes', '') + ' '
                notes += contest.get('notes', '')
                limitations = [item['reason'] for item in doc.get('unresolved', [])
                    if item.get('office_id', office) == office
                    and item.get('district', district) == district and item.get('reason')]
                if limitations:
                    notes += ' Source limitations: ' + ' '.join(dict.fromkeys(limitations))
                contest_boundary = boundary if district else ('county-1966-1982' if year < 1983 else 'county-2022')
                if session.get(BoundaryVersion, contest_boundary) is None:
                    session.merge(BoundaryVersion(id=contest_boundary, vintage=year, source_id=source_id))
                    session.flush()
                session.merge(Contest(id=cid, event_id=event_id, office_id=office,
                    jurisdiction_id=unit, boundary_id=contest_boundary, source_id=source_id,
                    status=report['status'], notes=notes))
                session.flush()
                ids = list(session.scalars(select(Participation.id).where(Participation.contest_id == cid)))
                session.execute(delete(VoteResult).where(VoteResult.participation_id.in_(ids)))
                session.execute(delete(Participation).where(Participation.contest_id == cid))
                session.flush()
                for index, candidate in enumerate(contest['candidates']):
                    pid = f'{cid}-candidate-{index}'
                    party = party_id(candidate['party'], year)
                    session.merge(Party(id=party, name=PARTIES.get(party, f'{party} (as reported)')))
                    session.merge(Candidate(id=pid, name=candidate['name']))
                    session.flush()
                    session.add(Participation(id=pid, contest_id=cid, candidate_id=pid,
                        party_id=party, write_in=candidate['write_in'], category='named_candidate'))
                    session.flush()
                    for geoid, votes in {unit: candidate['votes'], **candidate.get('county_votes', {})}.items():
                        session.add(VoteResult(participation_id=pid, unit_id=geoid, votes=votes,
                            source_id=source_id, status='verified' if votes is not None else 'unavailable'))
                session.add(ImportRun(contest_id=cid, created_at=datetime.now(timezone.utc).isoformat(),
                    status=report['status'], report=report))
                reports.append(report)
    return reports


def import_all(year=None, office=None):
    paths = document_paths()
    docs = [derive_registration_total(json.loads(p.read_text(encoding='utf-8'))) for p in paths]
    docs = [d for d in docs if d.get('record_type') != 'inventory' and d.get('contests') and (year is None or d['year'] == year)]
    if office:
        docs = [dict(d, contests=[c for c in d['contests'] if c['office_id'] == office]) for d in docs]
        docs = [d for d in docs if d['contests']]
    if not docs:
        if paths:
            return []  # A modern year or absent office has no historical input.
        raise ValueError('Historical canvass inputs are missing')
    reports = import_documents(docs)
    OUT.mkdir(parents=True, exist_ok=True)
    for doc in docs:
        kind = doc.get('kind', 'general')
        normalized = {'year': doc['year'], 'date': doc['date'], 'kind': kind, 'source_sha256': doc['source_sha256'],
            'turnout': doc.get('turnout', {}),
            'absent_offices': doc.get('absent_offices', []), 'unresolved': doc.get('unresolved', []),
            'contests': [dict(c, contest_id=contest_id(doc['year'], c, kind),
                reconciliation=reconcile_contest(c, doc['year'])) for c in doc['contests']]}
        output_path = OUT / (f"{doc['year']}" + (f'-{kind}' if kind != 'general' else '') + '.json')
        if office and output_path.exists():
            previous = json.loads(output_path.read_text(encoding='utf-8'))
            normalized['contests'] = [c for c in previous['contests'] if c['office_id'] != office] + normalized['contests']
        output_path.write_text(json.dumps(normalized, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    report_path = OUT / 'reconciliation.json'
    if (year or office) and report_path.exists():
        updated = {r['contest'] for r in reports}
        reports = [r for r in json.loads(report_path.read_text(encoding='utf-8')) if r['contest'] not in updated] + reports
    report_path.write_text(json.dumps(reports, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Historical canvasses: {len(reports)} contests audited/imported')
    return reports


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--year', type=int)
    parser.add_argument('--office', choices=sorted(OFFICES))
    args = parser.parse_args()
    import_all(args.year, args.office)
