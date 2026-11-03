"""Historical import contracts, independent of the legacy full-import fixture."""
import copy
import hashlib
import sys
import json
import os
import subprocess
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backend.app.database import Base
from backend.app.models import Contest, VoteResult, Turnout, ImportRun, Source
from scripts.historical_canvasses import validate_document, import_documents


def document(tmp_path):
    source = tmp_path / 'canvass.pdf'
    source.write_bytes(b'retained source fixture')
    return {
        'year': 1966, 'date': '1966-11-08', 'source_path': 'canvass.pdf',
        'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'absent_offices': ['president', 'us-senate'], 'unresolved': [],
        'contests': [{
            'office_id': 'state-senate', 'district': '7-A', 'page': 3,
            'candidates': [
                {'name': 'First', 'party': 'DEM', 'write_in': False, 'votes': 20},
                {'name': 'Second', 'party': 'REP', 'write_in': False, 'votes': 10},
            ],
        }],
    }


def test_rejects_changed_source_and_duplicate_district(tmp_path):
    doc = document(tmp_path)
    validate_document(doc, tmp_path)
    bad = copy.deepcopy(doc)
    bad['source_sha256'] = '0' * 64
    with pytest.raises(ValueError, match='checksum'):
        validate_document(bad, tmp_path)
    bad = copy.deepcopy(doc)
    bad['contests'].append(copy.deepcopy(bad['contests'][0]))
    with pytest.raises(ValueError, match='Duplicate contest'):
        validate_document(bad, tmp_path)


def test_missing_votes_remain_missing_and_negative_votes_fail(tmp_path):
    doc = document(tmp_path)
    doc['contests'][0]['candidates'][0]['votes'] = None
    validate_document(doc, tmp_path)
    doc['contests'][0]['candidates'][0]['votes'] = -1
    with pytest.raises(ValueError, match='nonnegative'):
        validate_document(doc, tmp_path)


def test_import_repeatability_district_isolation_and_multiseat_safety(tmp_path):
    doc = document(tmp_path)
    other = copy.deepcopy(doc['contests'][0])
    other['district'] = '7-B'
    other['candidates'][0]['votes'] = 100
    doc['contests'].append(other)
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    for _ in range(2):
        import_documents([doc], factory, source_root=tmp_path)
    from backend.app.historical import overview, catalog
    with factory() as session:
        assert len(list(session.scalars(select(Contest)))) == 2
        assert len(list(session.scalars(select(VoteResult)))) == 4
        entry = catalog(session)[0]
        assert entry['district_count'] == 2
        result = overview(session, entry['id'])
        assert [c['district'] for c in result['contests']] == ['7-A', '7-B']
        assert [c['results'].total_votes for c in result['contests']] == [30, 110]
        assert all(c['results'].winner is None for c in result['contests'])
        assert result['map_available'] is False
        assert list(session.scalars(select(Turnout))) == []
    engine.dispose()


def test_historical_house_is_separate_from_modern_overviews(tmp_path):
    doc = document(tmp_path)
    doc['contests'][0]['office_id'] = 'us-house'
    doc['contests'][0]['district'] = '1'
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    import_documents([doc], factory, source_root=tmp_path)
    from backend.app import house
    from backend.app.main import elections, historical_election
    with factory() as session:
        assert house.catalog(session) == []
        entries = elections(session)
        assert [e['id'] for e in entries] == ['az-1966-historical-us-house']
        assert historical_election('az-1966-historical-us-house', session)['map_available'] is False
    engine.dispose()


def test_existing_county_evidence_is_preserved_and_source_discrepancy_is_visible(tmp_path):
    doc = document(tmp_path)
    doc['contests'][0].update(office_id='governor', district=None)
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    import_documents([doc], factory, source_root=tmp_path)
    with factory.begin() as session:
        session.add(Source(id='previous-reviewed-source', title='Reviewed evidence', url='https://example.test', sha256='1'*64, notes=''))
        session.flush()
        contest = session.get(Contest, 'az-1966-governor')
        contest.source_id = 'previous-reviewed-source'
        session.add(VoteResult(participation_id='az-1966-governor-candidate-0', unit_id='04001',
            votes=7, source_id='previous-reviewed-source', status='verified'))
        session.add(Turnout(event_id='az-1966-general', unit_id='04', ballots_cast=100,
            registered_voters=200, percent=50, definition='Reviewed event turnout', source_id='previous-reviewed-source'))
        session.flush()
        original = list(session.scalars(select(VoteResult.votes)))
    doc['contests'][0]['candidates'][0]['votes'] = 21
    import_documents([doc], factory, source_root=tmp_path)
    with factory() as session:
        assert list(session.scalars(select(VoteResult.votes))) == original
        contest = session.get(Contest, 'az-1966-governor')
        assert contest.status == 'reported'
        run = session.scalar(select(ImportRun).where(ImportRun.contest_id == contest.id).order_by(ImportRun.id.desc()))
        assert run.report['canvass_audit']['existing_totals_match'] is False
        assert run.report['supplemental_source_ids'] == ['historical-canvass-1966']
        assert session.scalar(select(Turnout.ballots_cast)) == 100
    # A swap retains the same multiset but must still fail candidate-specific audit.
    doc['contests'][0]['candidates'][0]['votes'] = 10
    doc['contests'][0]['candidates'][1]['votes'] = 20
    import_documents([doc], factory, source_root=tmp_path)
    with factory() as session:
        run = session.scalar(select(ImportRun).order_by(ImportRun.id.desc()))
        assert run.report['canvass_audit']['existing_totals_match'] is False
    engine.dispose()


def test_retained_document_inventory_and_known_source_gaps():
    expected = {1966: (60,158), 1970: (67,159), 1974: (68,175), 1978: (67,205),
                1982: (69,202), 1986: (69,160), 1990: (68,199), 1994: (70,190)}
    for year, counts in expected.items():
        doc = validate_document(json.loads((ROOT / f'data/raw/historical-canvasses/{year}.json').read_text(encoding='utf-8')))
        assert (len(doc['contests']), sum(len(c['candidates']) for c in doc['contests'])) == counts
        assert 'president' in doc['absent_offices']
        for office in ['state-house', 'state-senate']:
            labels = {c['district'] for c in doc['contests'] if c['office_id'] == office}
            assert len(labels) == (27 if year == 1966 else 30)
        assert bool(doc['unresolved']) == (year in [1970, 1974])


def test_modern_scoped_cli_import_does_not_require_a_historical_document(tmp_path):
    env = dict(os.environ, DATABASE_URL='sqlite:///' + (tmp_path / 'modern.db').as_posix(), PYTHONUTF8='1')
    report_path = ROOT / 'data/processed/reconciliation.json'
    previous = report_path.read_bytes()
    try:
        for command in [
            ['-m', 'alembic', '-c', 'backend/alembic.ini', 'upgrade', 'head'],
            ['scripts/import_data.py', '--year', '2022', '--office', 'governor'],
        ]:
            result = subprocess.run([sys.executable, *command], cwd=ROOT, env=env, capture_output=True, text=True)
            assert result.returncode == 0, result.stderr[-1500:]
    finally:
        report_path.write_bytes(previous)


def test_1986_senate_write_in_party_matches_the_supplied_canvass():
    data = json.loads((ROOT / 'data/processed/us-senate/az-1986-us-senate.json').read_text(encoding='utf-8'))
    zilly = next(c for c in data['candidates'] if c['name'] == 'David Zilly')
    assert zilly['party'] == 'SWP'
    assert zilly['write_in'] is True
    assert zilly['statewide'] == 18


def test_historical_house_scoped_cli_skips_modern_source_dependencies(tmp_path):
    env = dict(os.environ, DATABASE_URL='sqlite:///' + (tmp_path / 'historical.db').as_posix(), PYTHONUTF8='1')
    paths = [ROOT / f'data/processed/historical-canvasses/{name}.json' for name in ['1982', 'reconciliation']]
    originals = {p: p.read_bytes() if p.exists() else None for p in paths}
    try:
        for command in [
            ['-m', 'alembic', '-c', 'backend/alembic.ini', 'upgrade', 'head'],
            ['scripts/import_data.py', '--year', '1982', '--office', 'us-house'],
        ]:
            result = subprocess.run([sys.executable, *command], cwd=ROOT, env=env, capture_output=True, text=True)
            assert result.returncode == 0, result.stderr[-1500:]
    finally:
        for path, original in originals.items():
            if original is not None:
                path.write_bytes(original)
            elif path.exists():
                path.unlink()


@pytest.mark.parametrize('year,count', [(1982,14),(1986,15)])
def test_fresh_scoped_statewide_import_includes_counties_and_geography(year, count):
    doc = json.loads((ROOT / f'data/raw/historical-canvasses/{year}.json').read_text(encoding='utf-8'))
    doc['contests'] = [c for c in doc['contests'] if c['office_id'] == 'secretary-of-state']
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    import_documents([doc], factory)
    from backend.app.main import counties, geography
    with factory() as session:
        c = session.get(Contest, f'az-{year}-secretary-of-state')
        assert len(counties(c.id, session)) == count
        assert len(geography(c.boundary_id, session).features) == count
    engine.dispose()
