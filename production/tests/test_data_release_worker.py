"""Versioned release orchestration: only disposable files and mocked containers."""
import json
import pytest
from scripts import deploy_worker as d
from test_deploy_worker import worker, config, SHA, stub_cycle


def prepare(worker, monkeypatch, tmp_path, version=2, applied=1):
    release=tmp_path/'release'; (release/'data').mkdir(parents=True)
    (release/'data/data-release.json').write_text(json.dumps({'version':version,'summary':'Reviewed election data'}))
    entries={'data/processed/1994.json':'new'}
    prior={'data/processed/1994.json':'old'}
    monkeypatch.setattr(worker,'entries',lambda sha:entries if sha==SHA else prior)
    monkeypatch.setattr(worker,'git',lambda *args:'data/processed/1994.json')
    ledger={'version':applied,'release':{'commit_sha':'b'*40,'fingerprint':d.data_fingerprint(prior)},'pending':None}
    monkeypatch.setattr(worker,'data_database_state',lambda:ledger)
    calls=[]
    monkeypatch.setattr(worker,'backup',lambda:calls.append('backup'))
    monkeypatch.setattr(worker,'import_data_release',lambda *args:calls.append('import'))
    return release,entries,ledger,calls


def test_versioned_import_precedes_build_and_tests(worker,monkeypatch,tmp_path):
    stub_cycle(worker,monkeypatch,tmp_path)
    release,entries,ledger,calls=prepare(worker,monkeypatch,tmp_path)
    monkeypatch.setattr(worker,'release',lambda sha:release)
    monkeypatch.setattr(d,'affected_services',lambda *a:['backend'])
    monkeypatch.setattr(worker,'build',lambda *a:calls.append('build'))
    monkeypatch.setattr(worker,'candidate_checks',lambda *a:calls.append('test'))
    monkeypatch.setattr(worker,'activate',lambda *a:calls.append('activate'))
    worker.cycle()
    assert calls==['backup','import','build','test','activate']


def test_same_version_changed_content_is_rejected(worker,monkeypatch,tmp_path):
    release,entries,ledger,calls=prepare(worker,monkeypatch,tmp_path,version=1)
    with pytest.raises(d.Failure,match='data_version_not_bumped'):
        worker.apply_data_release(release,entries,['data/processed/1994.json'])
    assert calls==[]


def test_applied_data_survives_failed_image_build(worker,monkeypatch,tmp_path):
    release,entries,ledger,calls=prepare(worker,monkeypatch,tmp_path,version=1)
    ledger['release']['fingerprint']=d.data_fingerprint(entries)
    worker.apply_data_release(release,entries,['data/processed/1994.json'])
    assert calls==[]


@pytest.mark.parametrize('path,reason',[
    ('data/geography/counties.json','data_path_unmapped'),
    ('backend/alembic/versions/new.py','data_schema_incompatible'),
    ('backend/app/models.py','data_schema_incompatible'),
    ('backend/requirements.txt','data_schema_incompatible'),
])
def test_unsafe_release_fails_before_backup(worker,monkeypatch,tmp_path,path,reason):
    release,entries,ledger,calls=prepare(worker,monkeypatch,tmp_path)
    monkeypatch.setattr(worker,'git',lambda *a:'data/processed/1994.json\0'+path)
    with pytest.raises(d.Failure,match=reason):
        worker.apply_data_release(release,entries,[path])
    assert calls==[]


def test_failed_import_stops_before_build(worker,monkeypatch,tmp_path):
    release,entries,ledger,calls=prepare(worker,monkeypatch,tmp_path)
    monkeypatch.setattr(worker,'import_data_release',lambda *a:(_ for _ in ()).throw(d.Failure('data_import_failed','migrate')))
    with pytest.raises(d.Failure,match='data_import_failed'):
        worker.apply_data_release(release,entries,[])
    assert calls==['backup']


def test_pending_different_data_is_not_overwritten(worker,monkeypatch,tmp_path):
    release,entries,ledger,calls=prepare(worker,monkeypatch,tmp_path)
    ledger['pending']={'version':2,'fingerprint':'different'}
    with pytest.raises(d.Failure,match='data_import_incomplete'):
        worker.apply_data_release(release,entries,[])
    assert calls==[]


def test_shared_senate_canvass_imports_house_too():
    assert d.data_offices(['data/raw/us-senate/2024-indexed-canvass.txt'])==['us-house','us-senate']


def test_fingerprint_ignores_only_declared_generated_reports():
    entries={'data/processed/1994.json':'one'}
    assert d.data_fingerprint(entries)==d.data_fingerprint({**entries,'data/data-release.json':'version','data/processed/reconciliation.json':'report'})
    assert d.data_fingerprint(entries)!=d.data_fingerprint({**entries,'data/geography/map.json':'two'})


def test_already_deployed_schema_does_not_block_later_data(worker,monkeypatch,tmp_path):
    release,entries,ledger,calls=prepare(worker,monkeypatch,tmp_path)
    monkeypatch.setattr(worker,'git',lambda *a:'data/processed/1994.json\0backend/app/models.py')
    worker.apply_data_release(release,entries,['data/processed/1994.json'])
    assert calls==['backup','import']


def test_git_inventory_keeps_unusual_paths_and_rejects_data_symlinks(worker,monkeypatch):
    path='data/raw/us-house/unicode-é\nrecord.txt'
    monkeypatch.setattr(worker,'git',lambda *a:'100644 blob abc\t'+path+'\0')
    assert worker.entries(SHA)=={path:'abc'}
    monkeypatch.setattr(worker,'git',lambda *a:'120000 blob abc\tdata/processed/1994.json\0')
    with pytest.raises(d.Failure,match='data_path_unmapped'):
        worker.entries(SHA)
