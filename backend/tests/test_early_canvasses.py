"""Early-source identity and reporting semantics; isolated database fixtures."""
import copy
import hashlib
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backend.app.database import Base
from backend.app.models import Contest, ElectionEvent
from scripts.historical_canvasses import validate_document, import_documents


def test_clearer_1916_report_replaces_uncertain_rows_without_duplicates():
    import json
    from backend.app.models import Candidate, Participation, GeographicUnit, Source
    from backend.app.services import results
    corrected = json.loads((ROOT/'data/raw/early-canvasses/1916.json').read_text(encoding='utf-8'))
    previous = copy.deepcopy(corrected)
    previous['contests'][0]['candidates'][0].update(name='Unreadable elector',votes=None)
    previous['contests'][-1]['candidates'][1]['name'] = 'Incorrect candidate'
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    import_documents([previous],factory)
    import_documents([corrected],factory)
    with factory() as session:
        assert len(list(session.scalars(select(Participation)))) == 28
        assert 'Incorrect candidate' not in set(session.scalars(select(Candidate.name)))
        from scripts.historical_canvasses import document_source_id
        supplement = session.get(Source, document_source_id(corrected, corrected['additional_sources'][0]['path']))
        assert supplement.title == corrected['additional_sources'][0]['title']
        assert 'superseded' in supplement.notes
        attorney = session.get(Contest,'az-1916-attorney-general')
        value = results(session,attorney,session.get(GeographicUnit,'04'))
        assert next(c.votes for c in value.candidates if c.name == 'John L. Gust') == 21297
        for contest in session.scalars(select(Contest)):
            assert contest.status == 'verified'
        from backend.app.historical import overview
        electors = overview(session,'az-1916-historical-president')
        assert electors['contests'][0]['results'].winner is None
        assert all(c.votes is not None for c in electors['contests'][0]['results'].candidates)
    engine.dispose()


def source_document(tmp_path, year=1933):
    path = tmp_path / 'source.pdf'
    path.write_bytes(b'early source fixture')
    return dict(year=year, date=f'{year}-10-03', kind='general', source_path='source.pdf',
        source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), absent_offices=[], unresolved=[],
        contests=[dict(office_id='state-senate', district='Cochise-1', page=1,
            candidates=[dict(name='First', party='DEM', write_in=False, votes=30),
                        dict(name='Second', party='REP', write_in=False, votes=20)])])


def test_county_districts_and_general_special_events_do_not_collide(tmp_path):
    doc = source_document(tmp_path)
    validate_document(doc, tmp_path)
    special = copy.deepcopy(doc)
    special.update(kind='special', date='1933-11-01')
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    import_documents([doc, special], factory, source_root=tmp_path)
    from backend.app.historical import catalog, overview
    with factory() as session:
        assert len(list(session.scalars(select(Contest)))) == 2
        assert {e.kind for e in session.scalars(select(ElectionEvent))} == {'general','special'}
        entries = catalog(session)
        assert len({e['id'] for e in entries}) == 2
        assert any(e['id'].endswith('-special') for e in entries)
        assert all(overview(session,e['id'])['contests'][0]['district'] == 'Cochise-1' for e in entries)
    engine.dispose()


def test_supplemental_source_hashes_are_validated(tmp_path):
    doc = source_document(tmp_path)
    doc['contests'][0]['district'] = '1'
    (tmp_path/'supplement.pdf').write_bytes(b'supplement')
    doc['additional_sources'] = [dict(path='supplement.pdf', sha256='0'*64)]
    with pytest.raises(ValueError, match='checksum'):
        validate_document(doc,tmp_path)


def test_greenlee_is_not_a_1906_county(tmp_path):
    doc = source_document(tmp_path,1906)
    doc['contests'][0].update(office_id='us-house',district='1')
    doc['contests'][0]['candidates'][0]['county_votes'] = {'04011':1}
    with pytest.raises(ValueError, match='county'):
        validate_document(doc,tmp_path)


def test_elector_votes_remain_separate_and_do_not_infer_a_presidential_winner(tmp_path):
    doc = source_document(tmp_path,1912)
    doc['contests'][0].update(office_id='president',district='at-large',multi_seat=True,
        notes='Individual presidential elector votes, not a combined ticket vote.')
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    import_documents([doc],factory,source_root=tmp_path)
    from backend.app.historical import catalog,overview
    with factory() as session:
        result = overview(session,catalog(session)[0]['id'])
        assert result['result_basis'] == 'presidential-electors'
        assert len(result['contests'][0]['results'].candidates) == 2
        assert result['contests'][0]['results'].winner is None
    engine.dispose()


def test_explicit_source_rows_preserve_repeated_write_in_labels(tmp_path):
    doc = source_document(tmp_path)
    doc['contests'][0]['district'] = '1'
    first = doc['contests'][0]['candidates'][0]
    first.update(name='Repeated printed label', write_in=True, source_row_id='write-in-row-1')
    second = copy.deepcopy(first)
    second.update(source_row_id='write-in-row-2',party='NONE',votes=1)
    doc['contests'][0]['candidates'].append(second)
    validate_document(doc,tmp_path)
    second['source_row_id']='write-in-row-1'
    with pytest.raises(ValueError, match='duplicate'):
        validate_document(doc,tmp_path)


def test_two_seat_senate_selection_has_no_single_winner(tmp_path):
    from backend.app.services import results
    from backend.app.models import GeographicUnit
    doc = source_document(tmp_path,1911)
    doc['contests'][0].update(office_id='us-senate',district=None,multi_seat=True)
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    import_documents([doc],factory,source_root=tmp_path)
    with factory() as session:
        contest = session.scalar(select(Contest))
        assert results(session,contest,session.get(GeographicUnit,'04')).winner is None
    engine.dispose()


def test_source_limitations_are_visible_with_the_contest(tmp_path):
    doc = source_document(tmp_path)
    doc['unresolved'] = [{'office_id':'state-senate','district':'Cochise-1',
        'reason':'Printed party label is damaged.'}]
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    import_documents([doc],factory,source_root=tmp_path)
    with factory() as session:
        assert 'Printed party label is damaged.' in session.scalar(select(Contest)).notes
    engine.dispose()


def test_statewide_reconciliation_matches_detail_display_contract():
    from scripts.historical_canvasses import reconcile_contest, county_units
    contest = dict(office_id='governor',page=1,candidates=[
        dict(name='Printed candidate',votes=None,county_votes={'04001':10})])
    row = reconcile_contest(contest,1911)['candidates'][0]
    assert row['official_statewide'] is None
    assert set(row['missing_counties']) == county_units(1911) - {'04001'}


def test_unallocated_write_in_does_not_hide_reported_county_results(tmp_path):
    from backend.app.models import GeographicUnit
    from backend.app.services import results
    doc = source_document(tmp_path,1932)
    contest = doc['contests'][0]
    contest.update(office_id='governor',district=None)
    contest['candidates'] = [dict(name='First',party='DEM',write_in=False,votes=60,county_votes={'04001':60}),
        dict(name='Second',party='REP',write_in=False,votes=40,county_votes={'04001':40}),
        dict(name='Write-in',party='DEM',write_in=True,votes=1)]
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    import_documents([doc],factory,source_root=tmp_path)
    with factory() as session:
        value = results(session,session.get(Contest,'az-1932-governor'),session.get(GeographicUnit,'04001'))
        assert value.total_votes == 100
        assert value.partial is True
        assert value.candidates[0].percent == 60
        assert value.winner.name == 'First'  # Missing statewide write-in cannot overcome 20-vote margin.
    engine.dispose()


def test_official_turnout_is_imported_without_inventing_missing_ballots(tmp_path):
    from backend.app.models import Turnout
    doc = source_document(tmp_path)
    doc['turnout'] = {'04':dict(registered_voters=100,ballots_cast=80,percent=80,definition='Official table.',page=2),
        '04001':dict(registered_voters=20,ballots_cast=None,percent=None,definition='Registration only.',page=2)}
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    import_documents([doc],factory,source_root=tmp_path)
    import_documents([doc],factory,source_root=tmp_path)
    with factory() as session:
        rows = {t.unit_id:t for t in session.scalars(select(Turnout))}
        assert len(rows)==2
        assert rows['04'].percent==80
        assert rows['04001'].registered_voters==20
        assert rows['04001'].ballots_cast is None
    engine.dispose()


def test_registration_and_race_votes_produce_calculated_participation():
    from backend.app.services import turnout_with_participation
    from backend.app.schemas import TurnoutOut
    value = turnout_with_participation(TurnoutOut(registered_voters=90272),68445)
    assert round(value.percent,2)==75.82
    assert value.votes_cast==68445
    assert value.basis=='contest_votes'
    assert value.ballots_cast is None
    published = TurnoutOut(registered_voters=181088,ballots_cast=141264,percent=78.1)
    assert turnout_with_participation(published,128686).percent==78.1
    assert turnout_with_participation(TurnoutOut(registered_voters=0),10).percent is None
    assert turnout_with_participation(TurnoutOut(registered_voters=100),None).percent is None


def test_statewide_registration_is_derived_only_from_complete_county_totals():
    from scripts.historical_canvasses import derive_registration_total,county_units
    doc = dict(year=1928,turnout={g:{'registered_voters':10} for g in county_units(1928)})
    assert derive_registration_total(doc)['turnout']['04']['registered_voters']==140
    doc['turnout']['04027']['registered_voters']=None
    assert '04' not in derive_registration_total(doc)['turnout']


def test_1928_registration_and_presidential_denominator_use_official_counties():
    import json
    from backend.app import presidential
    from backend.app.models import Source
    doc = json.loads((ROOT/'data/raw/early-canvasses/1928.json').read_text(encoding='utf-8'))
    assert doc['turnout']['04']['registered_voters']==sum(v['registered_voters'] for g,v in doc['turnout'].items() if g!='04')==119728
    assert doc['turnout']['04027']['registered_voters']==5294
    engine=create_engine('sqlite://');Base.metadata.create_all(engine);factory=sessionmaker(engine)
    import_documents([doc],factory)
    with factory() as session:
        turnout=presidential.detail(session,'az-1928-historical-president').statewide.turnout
        assert round(turnout.percent,2)==76.22
        assert turnout.registered_voters==119728
        assert '200-person' in turnout.definition
        assert 'azsos.gov' in session.get(Source,turnout.source_id).url
    engine.dispose()


def test_presidential_presentation_uses_nominees_and_one_elector_tally():
    import json
    from backend.app import presidential
    doc = json.loads((ROOT/'data/raw/early-canvasses/1916.json').read_text(encoding='utf-8'))
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    import_documents([doc],factory)
    with factory() as session:
        value = presidential.detail(session,'az-1916-historical-president')
        totals = {c.name:c.votes for c in value.statewide.candidates}
        assert totals['Woodrow Wilson']==33170
        assert totals['Charles E. Hughes']==20524
        assert len(totals)==4
        assert value.statewide.turnout.votes_cast==58021
        assert value.statewide.turnout.basis=='contest_votes'
        assert value.election.office=='President'
        assert len(presidential.counties(session,'az-1916-historical-president'))==14
        from backend.app import main
        assert main.statewide('az-1916-historical-president',session).candidates[0].name=='Woodrow Wilson'
        assert main.county('az-1916-historical-president','04001',session).candidates[0].name=='Woodrow Wilson'
        assert any('presidential-names' in s.id for s in main.sources('az-1916-historical-president',session))
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as absent:
            presidential.detail(session,'az-1930-historical-president')
        assert absent.value.status_code==404
    engine.dispose()


def test_retained_pdf_endpoint_checks_digest_and_rejects_unknown_id(tmp_path, monkeypatch):
    import scripts.historical_canvasses as archive
    from backend.app.main import historical_source
    from fastapi import HTTPException
    pdf = tmp_path / 'data/raw/source.pdf'
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b'PDF fixture')
    doc = source_document(tmp_path)
    doc.update(source_path='data/raw/source.pdf',source_sha256=hashlib.sha256(pdf.read_bytes()).hexdigest())
    path = tmp_path / '1933.json'
    import json
    path.write_text(json.dumps(doc))
    monkeypatch.setattr(archive,'ROOT',tmp_path)
    monkeypatch.setattr(archive,'document_paths',lambda:[path])
    assert historical_source('historical-canvass-1933').path == pdf
    pdf.write_bytes(b'changed')
    with pytest.raises(HTTPException) as changed:
        historical_source('historical-canvass-1933')
    assert changed.value.status_code == 409
    with pytest.raises(HTTPException) as missing:
        historical_source('unknown')
    assert missing.value.status_code == 404
