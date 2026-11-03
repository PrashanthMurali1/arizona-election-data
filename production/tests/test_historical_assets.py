"""Historical sources remain usable after candidate data mounts disappear."""
import json
from pathlib import Path
import sqlite3

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from scripts import historical_assets as h


def fixture(tmp_path):
    source=tmp_path/'candidate/data'
    for name in h.DIRECTORIES:(source/'raw'/name).mkdir(parents=True)
    (source/'raw/early-canvasses/1911.json').write_text('{"votes":10476}')
    (source/'raw/early-canvasses/source.pdf').write_bytes(b'PDF fixture')
    database=tmp_path/'state/elections.db';database.parent.mkdir()
    with sqlite3.connect(database) as c:
        c.execute('CREATE TABLE data_release_history(version INTEGER, fingerprint TEXT, scopes_json TEXT)')
    return source,database


def test_bundle_is_invisible_until_ledger_commits_and_survives_staging_removal(tmp_path):
    source,database=fixture(tmp_path)
    fingerprint='a'*64
    bundle=h.stage_assets(source,database,fingerprint)
    engine=create_engine('sqlite:///'+database.as_posix())
    with Session(engine) as session:
        assert h.runtime_root(session,tmp_path/'fallback')==tmp_path/'fallback'
    with sqlite3.connect(database) as c:
        c.execute('INSERT INTO data_release_history VALUES(1,?,?)',(fingerprint,json.dumps(['historical'])))
        c.execute('INSERT INTO data_release_history VALUES(2,?,?)',('b'*64,json.dumps(['governor'])))
    import shutil
    shutil.rmtree(source)
    with Session(engine) as session:
        assert h.runtime_root(session)==bundle
        assert json.loads((bundle/'data/raw/early-canvasses/1911.json').read_text())=={'votes':10476}
    engine.dispose()


def test_bundle_copy_is_idempotent_and_rejects_modified_files(tmp_path):
    source,database=fixture(tmp_path)
    bundle=h.stage_assets(source,database,'a'*64)
    assert h.stage_assets(source,database,'a'*64)==bundle
    (bundle/'data/raw/early-canvasses/1911.json').write_text('corrupt')
    with pytest.raises(ValueError,match='differs'):h.stage_assets(source,database,'a'*64)
    with pytest.raises(ValueError):h.bundle_path(database,'../outside')


def test_missing_applied_bundle_does_not_fall_back_to_stale_sources(tmp_path):
    _,database=fixture(tmp_path)
    with sqlite3.connect(database) as c:c.execute('INSERT INTO data_release_history VALUES(1,?,?)',('a'*64,'["historical"]'))
    engine=create_engine('sqlite:///'+database.as_posix())
    with Session(engine) as session,pytest.raises(RuntimeError,match='bundle is missing'):h.runtime_root(session,tmp_path/'stale')
    engine.dispose()


def test_presidential_results_and_pdf_endpoint_use_committed_bundle(tmp_path,monkeypatch):
    import hashlib
    from backend.app.database import Base
    from backend.app import presidential
    from backend.app.main import historical_source
    from scripts import historical_canvasses as archive
    source=tmp_path/'data'
    for name in h.DIRECTORIES:(source/'raw'/name).mkdir(parents=True)
    pdf=source/'raw/early-canvasses/source.pdf';pdf.write_bytes(b'%PDF retained fixture')
    doc=dict(year=1956,date='1956-11-06',kind='general',
        source_path='data/raw/early-canvasses/source.pdf',source_sha256=hashlib.sha256(pdf.read_bytes()).hexdigest(),
        absent_offices=[],unresolved=[],contests=[dict(office_id='president',district='at-large',page=1,
        candidates=[dict(name='Stevenson ticket',party='DEM',votes=20,write_in=False),
                    dict(name='Eisenhower ticket',party='REP',votes=30,write_in=False)])])
    (source/'raw/early-canvasses/1956.json').write_text(json.dumps(doc))
    (source/'raw/early-canvasses/presidential-tickets.json').write_text(json.dumps({'1956':{
        'DEM':{'name':'Adlai E. Stevenson'},'REP':{'name':'Dwight D. Eisenhower'}}}))
    database=tmp_path/'state/elections.db';database.parent.mkdir()
    engine=create_engine('sqlite:///'+database.as_posix());Base.metadata.create_all(engine)
    from sqlalchemy.orm import sessionmaker
    factory=sessionmaker(engine)
    archive.import_documents([doc],factory,source_root=tmp_path)
    bundle=h.stage_assets(source,database,'a'*64)
    with engine.begin() as c:
        c.exec_driver_sql('CREATE TABLE data_release_history(version INTEGER,fingerprint TEXT,scopes_json TEXT)')
        c.exec_driver_sql('INSERT INTO data_release_history VALUES(1,?,?)',('a'*64,'["historical"]'))
    monkeypatch.setattr(archive,'ROOT',tmp_path/'unavailable')
    monkeypatch.setattr(presidential,'ROOT',tmp_path/'unavailable')
    with factory() as session:
        result=presidential.detail(session,'az-1956-historical-president')
        assert result.statewide.total_votes==50
        assert result.statewide.winner.name=='Dwight D. Eisenhower'
        served=historical_source('historical-canvass-1956',session)
        assert served.path==bundle/doc['source_path']
        assert served.path.read_bytes()==b'%PDF retained fixture'
    engine.dispose()
