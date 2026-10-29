"""Worker orchestration uses mocks only; no Docker, Git remote or production mounts."""
import copy
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts import deploy_worker as d

SHA = 'a' * 40


def config():
    return {'services': {s: {'image':s+'-old','environment':{},'networks':{'default':None},
                            'secrets':[], 'volumes':[], 'build':{'context':'/release','dockerfile':s+'.Dockerfile'}}
                         for s in d.SERVICES}, 'networks':{'default':{'name':d.PROJECT+'_default'}},
            'volumes':{'state':{'name':d.PROJECT+'_state'}}, 'secrets':{}}


def fake_live():
    return {s:dict(Id=s,Image=s+'-id',Config={'Env':[],'Cmd':[],'User':'','Entrypoint':[]},
                   HostConfig={'PortBindings':{}},Mounts=[],State={'Running':True,'Health':{'Status':'healthy'}})
            for s in d.SERVICES}


@pytest.fixture
def worker(tmp_path,monkeypatch):
    home=tmp_path/'private'
    home.mkdir()
    worker=d.Worker(dict(home=str(home),production_root=str(tmp_path),docker='docker',git='git',npm='npm',local_port=8080,public_url='https://example.test'))
    cfg=config()
    worker.sha=SHA
    fp=d.source_fingerprints({})
    live=fake_live()
    worker.state.update(manifest={s:dict(image=s+'-old',image_id=s+'-id',source_sha='b'*40,
        source_fingerprint=fp[s],config_fingerprint=d.runtime_signature(cfg,s),runtime_identity=d.runtime_identity(live[s])) for s in d.SERVICES},
        config=str(worker.config_path('previous',cfg)),assets=['/assets/old.js'])
    worker.save()
    monkeypatch.setattr(worker,'cleanup_candidates',lambda:True)
    return worker


@pytest.mark.parametrize('path,expected',[
    ('README.md',set()),('frontend/e2e/catalog.spec.ts',set()),('frontend/src/a.test.tsx',set()),
    ('backend/tests/test_api.py',set()),('scripts/deploy_worker.py',set()),
    ('frontend/src/Home.tsx',{'frontend'}),('frontend/public/logo.svg',{'frontend'}),
    ('backend/app/models.py',{'backend'}),('scripts/refresh_2026.py',{'backend'}),
        ('backend/app/log_export.py',set(d.SERVICES)),('backend/app/observability.py',set(d.SERVICES)),
    ('production/run_tunnel.py',set(d.SERVICES)),('production/frontend.Dockerfile',{'frontend'}),
    ('production/tunnel.Dockerfile',{'tunnel'}),('.dockerignore',set(d.SERVICES)),
])
def test_dependency_classification(path,expected):
    assert {s for s in d.SERVICES if d.relevant(path,s)} == expected


def test_config_change_targets_only_affected_service(worker):
    cfg=config()
    cfg['services']['frontend']['environment']['NEW_SETTING']='enabled'
    assert d.affected_services(worker.state['manifest'],d.source_fingerprints({}),cfg)==['frontend']
    cfg=config()
    cfg['volumes']['unused']={'name':'unused'}
    assert not d.affected_services(worker.state['manifest'],d.source_fingerprints({}),cfg)


@pytest.mark.parametrize('field',['volumes','user','logging','environment','secrets','ports','networks'])
def test_production_storage_identity_and_monitoring_cannot_silently_change(field):
    old=config()
    old['services']['backend']['environment']['NEW_RELIC_LOGS_ENABLED']='true'
    new=copy.deepcopy(old)
    if field=='environment':
        new['services']['backend'][field]['NEW_RELIC_LOGS_ENABLED']='false'
    else:
        new['services']['backend'][field]=[] if field=='secrets' else 'different'
        if field=='secrets': new['services']['backend'][field]=[{'source':'private-user-api-key'}]
    with pytest.raises(d.Failure,match='protected_configuration_changed'):
        d.validate_protected(new,old)


def test_build_args_and_secret_sources_are_part_of_runtime_plan(worker):
    cfg=config()
    cfg['services']['backend']['build']['args']={'APP_UID':'502'}
    assert set(d.affected_services(worker.state['manifest'],d.source_fingerprints({}),cfg))=={'backend'}


def test_retries_never_overwrite_a_previously_tagged_image(worker,monkeypatch,tmp_path):
    cfg=config()
    cfg['services']['frontend']['build']['context']=str(tmp_path)
    cfg['services']['initialize']={'image':'old'}
    cfg['services']['migrate']={'image':'old'}
    calls=[]
    monkeypatch.setattr(worker,'docker',lambda *args,**kwargs:calls.append(args))
    worker.build(tmp_path,cfg,['frontend'])
    first=cfg['services']['frontend']['image']
    worker.build(tmp_path,cfg,['frontend'])
    second=cfg['services']['frontend']['image']
    assert SHA in first and SHA in second and first!=second


def test_lock_prevents_overlap_and_releases_after_exception(tmp_path):
    path=tmp_path/'worker.lock'
    with pytest.raises(RuntimeError):
        with d.exclusive_lock(path) as locked:
            assert locked
            with d.exclusive_lock(path) as second:
                assert not second
            raise RuntimeError('test')
    with d.exclusive_lock(path) as locked:
        assert locked


def test_noop_compares_manifest_not_checkout_head(worker,monkeypatch,tmp_path):
    monkeypatch.setattr(worker,'check_engine',lambda:None)
    monkeypatch.setattr(worker,'drift_check',lambda:None)
    monkeypatch.setattr(worker,'fetch',lambda:SHA)
    monkeypatch.setattr(worker,'release',lambda sha:tmp_path)
    monkeypatch.setattr(worker,'render',lambda path:config())
    monkeypatch.setattr(worker,'entries',lambda sha:{})
    monkeypatch.setattr(worker,'git',lambda *args: '')
    monkeypatch.setattr(worker,'build',lambda *args:pytest.fail('no-op built image'))
    worker.cycle()
    assert worker.state['last_result']['status']=='noop'
    assert worker.state['manifest']['frontend']['source_sha']=='b'*40


@pytest.mark.parametrize('reason',['docker_unavailable','command_failed'])
def test_unavailable_infrastructure_defers_without_poisoning_commit(worker,monkeypatch,reason):
    def defer(**kwargs):
        raise d.Deferred(reason,'fetch')
    monkeypatch.setattr(worker,'cycle',defer)
    assert worker.run()==0
    assert not worker.state['failed']
    assert worker.state['last_result']['status']=='deferred'


@pytest.mark.parametrize('phase',['build','test'])
def test_failed_commit_is_recorded_and_keeps_manifest(worker,monkeypatch,phase):
    previous=copy.deepcopy(worker.state['manifest'])
    def fail(**kwargs):
        raise d.Failure('command_failed',phase,1)
    monkeypatch.setattr(worker,'cycle',fail)
    assert worker.run()==1
    assert worker.state['failed'][SHA]['phase']==phase
    assert worker.state['manifest']==previous


def test_failed_commit_skip_and_explicit_retry(worker,monkeypatch,tmp_path):
    worker.state['failed'][SHA]={'reason':'test'}
    for name in ('check_engine','drift_check'):
        monkeypatch.setattr(worker,name,lambda:None)
    monkeypatch.setattr(worker,'fetch',lambda:SHA)
    monkeypatch.setattr(worker,'release',lambda sha:tmp_path)
    monkeypatch.setattr(worker,'render',lambda path:config())
    monkeypatch.setattr(worker,'entries',lambda sha:{})
    monkeypatch.setattr(worker,'git',lambda *args:'')
    worker.cycle()
    assert worker.state['last_result']['status']=='failed_commit_skipped'
    worker.cycle(retry=True)
    assert SHA not in worker.state['failed'] and worker.state['last_result']['status']=='noop'


def test_dirty_checkout_is_never_reset(worker,monkeypatch):
    worker.repo.mkdir()
    calls=[]
    def git(*args,**kwargs):
        calls.append(args)
        return d.REMOTE if args[0]=='remote' else ' M source.py'
    monkeypatch.setattr(worker,'git',git)
    with pytest.raises(d.Failure,match='dirty_checkout'):
        worker.fetch()
    assert not any('reset' in call or 'clean' in call for call in calls)


def test_new_main_is_considered_after_older_failure(worker,monkeypatch,tmp_path):
    newer='c'*40
    worker.state['failed'][SHA]={'reason':'test'}
    for name in ('check_engine','drift_check'):
        monkeypatch.setattr(worker,name,lambda:None)
    def fetch():
        worker.sha=newer
        return newer
    monkeypatch.setattr(worker,'fetch',fetch)
    monkeypatch.setattr(worker,'release',lambda sha:tmp_path)
    monkeypatch.setattr(worker,'render',lambda path:config())
    monkeypatch.setattr(worker,'entries',lambda sha:{})
    monkeypatch.setattr(worker,'git',lambda *args:'')
    worker.cycle()
    assert worker.state['last_checked']==newer and SHA in worker.state['failed']


def test_newer_push_is_processed_after_current_cycle(worker,monkeypatch):
    calls=[]
    newer='c'*40
    def cycle(**kwargs):
        calls.append(worker.sha)
    def fetch():
        worker.sha=newer
    monkeypatch.setattr(worker,'cycle',cycle)
    monkeypatch.setattr(worker,'fetch',fetch)
    assert worker.run()==0
    assert calls==[SHA,newer]


def test_cleanup_targets_only_own_labeled_disposable_resources(worker,monkeypatch):
    calls=[]
    def docker(*args,**kwargs):
        calls.append(args)
        return 'a'*12 if args[0]=='ps' else ''
    monkeypatch.setattr(worker,'docker',docker)
    assert d.Worker.cleanup_candidates(worker)
    assert calls[0][:3]==('ps','-aq','--filter')
    assert calls[0][3].startswith('label=az-election.deploy.check=')
    assert ('rm','-f','a'*12) in calls


def test_drift_stops_deployment(worker,monkeypatch):
    live=fake_live()
    live['frontend']['Image']='external-new-image'
    monkeypatch.setattr(worker,'inspect',lambda:live)
    with pytest.raises(d.Failure,match='runtime_drift'):
        worker.drift_check()


def test_success_records_only_verified_service_versions(worker,monkeypatch):
    cfg=config()
    cfg['services']['frontend']['image']='frontend-new'
    calls=[]
    monkeypatch.setattr(worker,'compose',lambda *a,**k:calls.append(a))
    monkeypatch.setattr(worker,'image_id',lambda image:'new-id')
    monkeypatch.setattr(worker,'image_assets',lambda image:['/assets/new.js'])
    live=fake_live()
    live['frontend']['Image']='new-id'
    monkeypatch.setattr(worker,'verify_live',lambda *a:live)
    previous=worker.state['manifest']['backend'].copy()
    path=worker.config_path('new',cfg)
    worker.activate(path,cfg,['frontend'],d.source_fingerprints({}),False)
    assert worker.state['manifest']['frontend']['image']=='frontend-new'
    assert worker.state['manifest']['backend']==previous
    assert 'journal' not in worker.state
    assert '--no-deps' in calls[0]


def test_failed_activation_rolls_back_without_restoring_database(worker,monkeypatch):
    cfg=config()
    path=worker.config_path('new',cfg)
    calls=[]
    previous=copy.deepcopy(worker.state['manifest'])
    monkeypatch.setattr(worker,'compose',lambda *a,**k:calls.append(a))
    monkeypatch.setattr(worker,'image_id',lambda image:'id')
    monkeypatch.setattr(worker,'image_assets',lambda image:['/assets/new.js'])
    attempts=[0]
    def verify(*args):
        attempts[0]+=1
        if attempts[0]==1:
            raise d.Failure('health_failed','verify')
        return fake_live()
    monkeypatch.setattr(worker,'verify_live',verify)
    with pytest.raises(d.Failure):
        worker.activate(path,cfg,['frontend'],d.source_fingerprints({}),False)
    assert worker.state['manifest']==previous and 'journal' not in worker.state
    assert not any('restore' in call or 'initialize' in call for call in calls)


def test_failed_incompatible_migration_blocks_rollback_and_retry(worker,monkeypatch):
    cfg=config()
    path=worker.config_path('new',cfg)
    calls=[]
    def compose(*args,**kwargs):
        calls.append(args)
        if 'migrate' in args:
            raise d.Failure('command_failed','migrate')
    monkeypatch.setattr(worker,'compose',compose)
    monkeypatch.setattr(worker,'image_id',lambda image:'id')
    with pytest.raises(d.Failure):
        worker.activate(path,cfg,['backend'],d.source_fingerprints({}),True)
    assert worker.state['blocked'] and not worker.state['journal']['rollback_allowed']
    assert not any('restore' in call for call in calls)
    monkeypatch.setattr(worker,'check_engine',lambda:None)
    assert worker.run()==0
    assert worker.state['last_result']['reason']=='migration_recovery_required'


def test_migration_command_pins_candidate_and_bypasses_dependencies(worker,monkeypatch):
    cfg=config()
    path=worker.config_path('new',cfg)
    calls=[]
    monkeypatch.setattr(worker,'compose',lambda *a,**k:calls.append(a))
    monkeypatch.setattr(worker,'image_id',lambda image:'id')
    monkeypatch.setattr(worker,'image_assets',lambda image:['/assets/new.js'])
    monkeypatch.setattr(worker,'verify_live',lambda *a:fake_live())
    worker.activate(path,cfg,['backend'],d.source_fingerprints({}),False)
    migration=next(call for call in calls if 'migrate' in call)
    assert migration[0]==path and '--no-deps' in migration and 'backend' in migration
    assert not any('initialize' in call for call in calls)


def test_safe_path_rejects_workspace_parent(tmp_path):
    with pytest.raises(d.Failure,match='unsafe_path'):
        d.within(tmp_path.parent,tmp_path)


def test_public_probe_identifies_itself_and_keeps_tls_defaults(worker,monkeypatch):
    seen=[]
    class Response:
        status=200
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def read(self): return b'{}'
    def open_request(request,timeout):
        seen.append(request)
        assert timeout==30
        return Response()
    monkeypatch.setattr(d,'urlopen',open_request)
    assert worker.request('https://example.test','/api/health')==b'{}'
    assert seen[0].get_header('User-agent')=='ArizonaElectionDeploy/1.0'


@pytest.mark.parametrize('missing',[False,True])
def test_public_verification_fetches_expected_bundles(worker,monkeypatch,missing):
    seen=[]
    def request(base,path):
        seen.append(path)
        if path=='/api/health': return b'{"status":"ok"}'
        if path=='/api/elections': return b'[{"id":"fixture","year":2022}]'
        if path.startswith('/api/'): return b'{}'
        if path.startswith('/assets/'):
            if missing: raise d.Failure('health_failed','verify')
            return b'console.log(1)'
        return b'<!doctype html><script src="/assets/new.js"></script>'
    monkeypatch.setattr(worker,'request',request)
    if missing:
        with pytest.raises(d.Failure): worker.verify_http('https://example.test',['/assets/new.js'])
    else:
        worker.verify_http('https://example.test',['/assets/new.js'])
    assert '/assets/new.js' in seen


def test_deployment_logs_redact_unknown_metadata_and_export_summaries():
    import logging
    from backend.app.observability import JsonFormatter
    from backend.app.log_export import LogExporter
    record=logging.LogRecord('elections',logging.INFO,'',0,'SECRET',(),None)
    record.event='deployment_succeeded'
    record.commit_sha=SHA
    record.services=['backend']
    record.phase='verify'
    record.rollback='not_needed'
    record.reason='SECRET'
    record.password='SECRET'
    value=json.loads(JsonFormatter('deploy_worker').format(record))
    assert 'SECRET' not in json.dumps(value)
    assert value['commit_sha']==SHA and value['services']=='backend'
    exporter=LogExporter('not-a-real-key',start=False)
    exporter.submit(value)
    assert exporter.queue.qsize()==1


def test_old_manifest_cron_entry_does_not_require_a_container(worker, monkeypatch):
    worker.state['manifest']['scheduler'] = {'image_id': 'retired-image'}
    monkeypatch.setattr(worker, 'inspect', fake_live)
    assert set(worker.drift_check()) == set(d.SERVICES)


def test_old_rollback_journal_never_recreates_cron(worker, monkeypatch):
    calls = []
    monkeypatch.setattr(worker, 'compose', lambda *a, **k: calls.append(a))
    worker.bring_up('old-config.json', ['backend', 'scheduler'], 'rollback')
    assert len(calls) == 1 and calls[0][-1] == 'backend'
    assert 'scheduler' not in calls[0] and 'create' not in calls[0]
    worker.bring_up('old-config.json', ['scheduler'], 'rollback')
    assert len(calls) == 1
    with pytest.raises(d.Failure, match='unsupported_service'):
        worker.bring_up('old-config.json', ['arbitrary'], 'rollback')


@pytest.mark.parametrize('message,expected', [
    ("FileNotFoundError: [Errno 2] No such file or directory: '/app/compose.yaml'", d.Failure),
    ('getaddrinfo ENOTFOUND registry.npmjs.org', d.Deferred),
    ('connect ETIMEDOUT', d.Deferred),
    ('read ECONNRESET', d.Deferred),
    ('Could not resolve host: github.com', d.Deferred),
])
def test_command_distinguishes_missing_files_from_network_errors(worker, message, expected):
    with pytest.raises(d.Failure) as caught:
        worker.command([sys.executable, '-c',
                        'import sys; print(sys.argv[1]); sys.exit(1)', message], phase='test')
    assert type(caught.value) is expected
    assert caught.value.reason == 'command_failed'
    assert caught.value.phase == 'test'
    assert caught.value.code == 1
