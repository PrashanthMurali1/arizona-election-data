"""Windows pull-based production deployer. Stdlib only; no shell or credential arguments."""
from __future__ import annotations

import argparse
from collections import deque
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
from urllib.request import Request, urlopen
from uuid import uuid4

SERVICES = ('backend', 'frontend', 'tunnel')
PROJECT = 'az-election-explorer'
REMOTE = 'https://github.com/PrashanthMurali1/arizona-election-data.git'
ADMIN = {'scripts/relay_diagnostics.py', 'scripts/deploy_worker.py', 'scripts/newrelic_admin.py', 'scripts/setup_newrelic_dashboard.py'}
SHARED = {'backend/app/observability.py', 'backend/app/log_export.py', 'production/run_tunnel.py'}


class Failure(Exception):
    def __init__(self, reason, phase='preflight', code=None):
        self.reason, self.phase, self.code = reason, phase, code
        super().__init__(reason)


class Deferred(Failure):
    pass


def now():
    return datetime.now(timezone.utc).isoformat()


def read_json(path, default=None):
    return json.loads(Path(path).read_text(encoding='utf-8-sig')) if Path(path).exists() else default


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    with temporary.open('w', encoding='utf-8') as handle:
        handle.write(json.dumps(value, indent=2) + '\n')
        handle.flush()
        os.fsync(handle.fileno())
    for attempt in range(10):
        try:
            temporary.replace(path)
            break
        except PermissionError:
            if attempt == 9:
                raise
            time.sleep(0.05)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def within(path, parent):
    result, parent = Path(path).resolve(), Path(parent).resolve()
    if result == parent or not result.is_relative_to(parent):
        raise Failure('unsafe_path')
    return result


@contextmanager
def exclusive_lock(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as handle:
        handle.seek(0, 2)
        if not handle.tell():
            handle.write(b'1')
            handle.flush()
        handle.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            yield False
            return
        try:
            yield True
        finally:
            handle.seek(0)
            if os.name == 'nt':
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def relevant(path, service):
    path = path.replace('\\', '/')
    if path in ADMIN or any(p in path for p in ('/tests/','/e2e/','/__tests__/','/__snapshots__/')) or path.endswith(('.md','.snap')) or re.search(r'\.(test|spec)\.[cm]?[jt]sx?$', path):
        return False
    if path == '.dockerignore':
        return True
    if service == 'backend':
        return (path.startswith('backend/') and path != 'backend/requirements-dev.txt') or (
            path.startswith('scripts/') and path.endswith('.py')) or path in {
                'production/backend.Dockerfile', 'production/requirements-monitoring.txt',
                'production/newrelic.ini', 'production/run_backend.py', 'production/start_monitored_backend.py',
                'production/manage_db.py', 'production/refresh_job.py',
                'production/migration-compatibility.json'} or path in SHARED or (
                path.startswith('production/') and path.endswith('.py') and path != 'production/run_caddy.py')
    if path in SHARED:
        return True
    if service == 'tunnel':
        return path == 'production/tunnel.Dockerfile'
    return (path.startswith('frontend/') and not path.startswith('frontend/playwright') and
            not path.startswith('frontend/test-results/')) or path in {
                'production/frontend.Dockerfile', 'production/Caddyfile', 'production/run_caddy.py'}


def source_fingerprints(entries, config=None):
    result = {}
    for service in SERVICES:
        recipe = None
        if config:
            group = service
            recipe = config['services'][group].get('build', {}).get('dockerfile')
        result[service] = digest([(p, blob) for p, blob in sorted(entries.items()) if relevant(p, service) or p == recipe])
    return result


def runtime_signature(config, service):
    value = json.loads(json.dumps(config['services'][service]))
    for name in ('image', 'build', 'depends_on'):
        value.pop(name, None)
    group = service
    build = dict(config['services'][group].get('build', {}))
    build.pop('context', None)
    return digest({'service': value, 'build':build,
                   'networks': {n:config.get('networks',{}).get(n) for n in value.get('networks', {'default':None})},
                   'secrets': {s['source']: config.get('secrets', {}).get(s['source']) for s in value.get('secrets', [])},
                   'volumes': {v['source']:config.get('volumes',{}).get(v['source']) for v in value.get('volumes',[]) if v['type']=='volume'}})


def affected_services(manifest, sources, config):
    return [s for s in SERVICES if manifest[s]['source_fingerprint'] != sources[s]
            or manifest[s]['config_fingerprint'] != runtime_signature(config, s)]


def validate_protected(config, previous):
    """A main push cannot silently move data/secrets or change hosting identities."""
    for service in SERVICES:
        new, old = config['services'][service], previous['services'][service]
        for field in ('volumes','user','logging','ports','networks'):
            if new.get(field) != old.get(field):
                raise Failure('protected_configuration_changed','render')
        for key,value in old.get('environment',{}).items():
            if key.startswith('NEW_RELIC_') or key in {'DATABASE_URL','TZ','REFRESH_INTERVAL_HOURS','APP_LOG_LEVEL'}:
                if new.get('environment',{}).get(key) != value:
                    raise Failure('protected_configuration_changed','render')
        if new.get('secrets',[]) != old.get('secrets',[]):
            raise Failure('protected_configuration_changed','render')
        for secret in old.get('secrets',[]):
            if config.get('secrets',{}).get(secret['source']) != previous.get('secrets',{}).get(secret['source']):
                raise Failure('protected_configuration_changed','render')
        for network in old.get('networks',{'default':None}):
            if config.get('networks',{}).get(network) != previous.get('networks',{}).get(network):
                raise Failure('protected_configuration_changed','render')
    if config['services']['backend'].get('build',{}).get('args') != previous['services']['backend'].get('build',{}).get('args'):
        raise Failure('protected_configuration_changed','render')


def migration_changed(paths):
    return any(p.startswith('backend/alembic/') or p in {'backend/alembic.ini','production/manage_db.py'} for p in paths)


def runtime_identity(container):
    return digest({'config': {k:container['Config'].get(k) for k in ('Cmd','Entrypoint','Env','User')},
                   'mounts': sorted(container.get('Mounts', []), key=lambda m:m['Destination']),
                   'ports': container['HostConfig'].get('PortBindings')})


def free_port():
    with socket.socket() as server:
        server.bind(('127.0.0.1', 0))
        return server.getsockname()[1]


class Worker:
    def __init__(self, config):
        self.cfg = config
        self.home = Path(config['home']).resolve()
        self.root = Path(config['production_root']).resolve()
        self.repo = self.home / 'checkout'
        self.state_path = self.home / 'state.json'
        self.state = read_json(self.state_path, {'failed': {}, 'notices': {}})
        self.phase = 'preflight'
        self.sha = None
        self.current_affected = []
        self.rollback_result = 'not_needed'
        self.emit = lambda *args, **kwargs: None

    def save(self):
        atomic_json(self.state_path, self.state)

    def event(self, level, event, **fields):
        self.emit(level, event, commit_sha=self.sha, phase=self.phase, **fields)

    def notice(self, reason):
        key = reason + ':' + str(self.sha)
        if time.time() - self.state.setdefault('notices', {}).get(key, 0) > 900:
            self.event(logging.WARNING, 'deployment_deferred', reason=reason)
            self.state['notices'][key] = time.time()
        self.state['last_result'] = {'status': 'deferred', 'reason': reason, 'at': now()}
        self.save()

    def command(self, args, *, cwd=None, timeout=900, phase=None, transient=False):
        self.phase = phase or self.phase
        env = {k: v for k, v in os.environ.items() if not k.startswith(('NEW_RELIC_', 'COMPOSE_', 'GIT_CONFIG_'))
               and k not in {'GITHUB_TOKEN','GH_TOKEN'}}
        env.update(GIT_TERMINAL_PROMPT='0', GCM_INTERACTIVE='Never', GIT_ASKPASS='', GCM_GUI_PROMPT='0',
                   GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1',
                   PLAYWRIGHT_BROWSERS_PATH=str(self.home / 'browser-cache'))
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        chunks = deque(maxlen=256)  # At most 1 MiB captured; never persisted or logged raw.
        try:
            process = subprocess.Popen([str(a) for a in args], cwd=cwd, env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=flags)
        except OSError:
            raise Deferred('tool_unavailable', self.phase) from None
        def consume():
            while chunk := process.stdout.read(4096):
                chunks.append(chunk)
        reader = threading.Thread(target=consume, daemon=True)
        reader.start()
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            if os.name == 'nt':
                subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                               capture_output=True, creationflags=flags)
            else:
                process.kill()
            reader.join(timeout=2)
            raise Failure('command_timeout', self.phase) from None
        reader.join(timeout=3)
        output = b''.join(chunks).decode('utf-8', errors='replace')
        if code:
            # Match Node error codes as tokens: FileNotFoundError contains
            # ENOTFOUND but is a deterministic failure, not a DNS outage.
            temporary = transient or bool(re.search(
                r'\b(?:enotfound|etimedout|econnreset)\b', output, re.IGNORECASE)) or any(
                x in output.lower() for x in ('could not resolve host',
                'network is unreachable', 'tls handshake timeout', 'i/o timeout'))
            # Local structural diagnostics are best effort and never include raw output.
            try:
                from scripts.relay_diagnostics import record_failure
                record_failure(self.home, output, self.phase, code, self.sha,
                               severity='WARNING' if temporary else 'ERROR')
            except Exception:
                pass
            raise (Deferred if temporary else Failure)('command_failed', self.phase, code)
        return output.strip()

    def docker(self, *args, **kwargs):
        return self.command([self.cfg['docker'], *args], **kwargs)

    def git(self, *args, cwd=None, **kwargs):
        return self.command([self.cfg['git'], '-c', 'credential.helper=', '-c', 'core.askPass=', *args],
                            cwd=cwd or self.repo, **kwargs)

    def compose(self, path, *args, **kwargs):
        return self.docker('compose', '-p', PROJECT, '--project-directory', self.root,
                           '--env-file', self.root / '.env', '-f', path,
                           '--profile', 'public', *args, **kwargs)

    def inspect(self):
        values = json.loads(self.docker('inspect', *[f'{PROJECT}-{s}-1' for s in SERVICES], transient=True))
        return dict(zip(SERVICES, values))

    def check_engine(self):
        try:
            if self.docker('info', '--format', '{{.OSType}}', timeout=20, transient=True) != 'linux':
                raise Deferred('docker_unavailable')
        except Deferred:
            if self.cfg.get('start_docker') and time.time()-self.state.get('docker_launch_at', 0) > 600:
                executable = Path(self.cfg['docker_desktop'])
                if executable.is_file():
                    flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                    startup = None
                    if os.name == 'nt':
                        startup = subprocess.STARTUPINFO()
                        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                        startup.wShowWindow = 0
                    subprocess.Popen([str(executable)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                     creationflags=flags, startupinfo=startup)
                    self.state['docker_launch_at'] = time.time()
                    self.save()
            raise Deferred('docker_unavailable') from None

    def fetch(self):
        self.phase = 'fetch'
        if not self.repo.exists():
            self.git('clone', '--no-tags', '--single-branch', '--branch', 'main', REMOTE, self.repo, cwd=self.home, transient=True)
        if self.git('remote', 'get-url', 'origin') != REMOTE:
            raise Failure('unexpected_remote', self.phase)
        if self.git('status', '--porcelain'):
            raise Failure('dirty_checkout', self.phase)
        self.git('fetch', '--no-tags', 'origin', 'main', transient=True)
        self.sha = self.git('rev-parse', 'origin/main')
        if not re.fullmatch('[0-9a-f]{40}', self.sha):
            raise Failure('invalid_commit', self.phase)
        return self.sha

    def release(self, sha):
        path = within(self.home / 'releases' / sha, self.home / 'releases')
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            self.git('worktree', 'add', '--detach', path, sha)
        if self.git('rev-parse', 'HEAD', cwd=path) != sha or self.git('status', '--porcelain', cwd=path):
            raise Failure('dirty_release', 'preflight')
        return path

    def entries(self, sha):
        rows = self.git('ls-tree', '-r', sha).splitlines()
        return {line.split('\t', 1)[1]: line.split('\t', 1)[0].split()[2]
                for line in rows if line.startswith('100')}

    def render(self, release):
        self.phase = 'render'
        args = ['compose', '-p', PROJECT, '--project-directory', release,
                '--env-file', self.root / '.env', '-f', release / 'compose.yaml',
                '-f', release / 'compose.newrelic.yaml', '--profile', 'public',
                'config', '--format', 'json']
        config = json.loads(self.docker(*args))
        private = (release / '.production').resolve()
        def remap(source):
            path = Path(source).resolve()
            return str(self.root / '.production' / path.relative_to(private)) if path.is_relative_to(private) else str(path)
        for service in config['services'].values():
            for mount in service.get('volumes', []):
                if mount['type'] == 'bind':
                    mount['source'] = remap(mount['source'])
        for secret in config.get('secrets', {}).values():
            if secret.get('file'):
                secret['file'] = remap(secret['file'])
        if config['name'] != PROJECT or config['volumes']['state']['name'] != PROJECT + '_state':
            raise Failure('protected_storage_changed', self.phase)
        for name in ('backend', 'migrate'):
            mounts = config['services'][name].get('volumes', [])
            if not any(m.get('type') == 'volume' and m.get('source') == 'state' and
                       m.get('target') == '/app/backend/local' for m in mounts):
                raise Failure('protected_storage_changed', self.phase)
        if self.state.get('config'):
            validate_protected(config, read_json(self.state['config']))
        return config

    def config_path(self, label, config):
        path = self.home / 'configs' / (label + '.json')
        atomic_json(path, config)
        return path

    def drift_check(self):
        live = self.inspect()
        # Historical manifests may retain the retired cron image as audit evidence.
        for name in SERVICES:
            record = self.state['manifest'][name]
            if live[name]['Image'] != record['image_id']:
                raise Failure('runtime_drift', 'preflight')
            if record.get('runtime_identity') != runtime_identity(live[name]):
                raise Failure('runtime_drift', 'preflight')
            if not live[name]['State']['Running'] or live[name]['State'].get('Health', {}).get('Status') != 'healthy':
                raise Deferred('production_unhealthy', 'preflight')
        return live

    def preserved_images(self, config, changed=()):
        for service in SERVICES:
            if service not in changed:
                config['services'][service]['image'] = self.state['manifest'][service]['image']
        backend = config['services']['backend']['image']
        for service in ('initialize', 'migrate'):
            config['services'][service]['image'] = backend

    def build(self, release, config, affected):
        self.phase = 'build'
        build_id = uuid4().hex[:10]
        groups = set(affected)
        for group in groups:
            tag = f'{PROJECT}-{group}:git-{self.sha}-{build_id}'
            spec = config['services'][group].get('build')
            if not spec or set(spec) - {'context', 'dockerfile', 'args'}:
                raise Failure('unsupported_build_config', self.phase)
            if Path(spec['context']).resolve() != release.resolve():
                raise Failure('unsafe_build_context', self.phase)
            command = ['build', '-f', within(release / spec['dockerfile'], release), '-t', tag,
                       '--label', 'org.opencontainers.image.revision=' + self.sha]
            for key, value in spec.get('args', {}).items():
                if key not in {'APP_UID', 'APP_GID'} or not str(value).isdigit() or int(value)>65535:
                    raise Failure('unsupported_build_config', self.phase)
                command += ['--build-arg', f'{key}={value}']
            self.docker(*command, release, timeout=1200)
            for service in affected:
                if service == group:
                    config['services'][service]['image'] = tag
        self.preserved_images(config, affected)

    def request(self, base, path):
        # The public edge rejects urllib's generic Python user-agent. Identify
        # these authorized read-only probes; do not disable TLS or edge rules.
        request = Request(base + path, headers={'User-Agent':'ArizonaElectionDeploy/1.0'})
        with urlopen(request, timeout=30) as response:
            if response.status != 200:
                raise Failure('health_failed', 'verify')
            return response.read()

    def verify_http(self, base, assets=None, html=True):
        try:
            health = json.loads(self.request(base, '/api/health'))
            catalog = json.loads(self.request(base, '/api/elections'))
            if health.get('status') != 'ok' or not catalog:
                raise Failure('health_failed', 'verify')
            for election in catalog:
                if election['year'] < 2026:
                    self.request(base, '/api/elections/' + election['id'])
            self.request(base, '/api/elections/az-2026-early-voting/activity')
            for path in ('/', '/elections/az-2026-early-voting') if html else ():
                content = self.request(base, path).decode()
                if '<!doctype html>' not in content.lower():
                    raise Failure('health_failed', 'verify')
                if assets and set(re.findall(r'/assets/[a-zA-Z0-9._-]+', content)) != set(assets):
                    raise Failure('asset_mismatch', 'verify')
            for asset in assets or ():
                body = self.request(base, asset)
                if not body or b'<html' in body[:100].lower():
                    raise Failure('asset_mismatch','verify')
        except Failure:
            raise
        except Exception:
            raise Failure('health_failed', 'verify') from None

    def image_id(self, image):
        return self.docker('image', 'inspect', image, '--format', '{{.Id}}')

    def cleanup_candidates(self):
        marker = 'az-election.deploy.check=' + digest(str(self.home))[:16]
        try:
            for resource, listing in (('container', ['ps','-aq']), ('network', ['network','ls','-q'])):
                ids = self.docker(*listing, '--filter', 'label=' + marker).split()
                if any(not re.fullmatch('[0-9a-f]{12,64}', value) for value in ids):
                    raise Failure('command_failed','test')
                if ids:
                    self.docker(*(['rm','-f'] if resource=='container' else ['network','rm']), *ids)
            return True
        except Failure:
            return False

    def image_assets(self, image):
        html = self.docker('run', '--rm', '--network', 'none', '--entrypoint', 'cat', image, '/srv/index.html')
        return sorted(set(re.findall(r'/assets/[a-zA-Z0-9._-]+', html)))

    def adopt(self):
        """Bootstrap only from audited live files and the previous verified UI deployment."""
        if self.state.get('manifest'):
            raise Failure('already_initialized', 'adopt')
        self.check_engine()
        self.fetch()
        live = self.inspect()
        proof = read_json(self.root / '.production/redeploy-ea59cce.json', {})
        if proof.get('status') != 'verified' or proof.get('frontend_image') != live['frontend']['Image']:
            raise Failure('frontend_evidence_mismatch', 'adopt')
        front_sha = proof['commit']
        self.sha = front_sha  # Adopt the audited deployed release, even if main has advanced.
        release = self.release(self.sha)
        entries = self.entries(self.sha)
        config = self.render(release)
        original = self.render(self.root)
        self.phase = 'adopt'
        for service in SERVICES:
            if runtime_signature(config, service) != runtime_signature(original, service):
                raise Failure('runtime_drift', self.phase)
            desired_env = config['services'][service].get('environment', {})
            actual_env = dict(e.split('=', 1) for e in live[service]['Config']['Env'])
            if any(actual_env.get(k) != str(v) for k, v in desired_env.items()):
                raise Failure('runtime_drift', self.phase)
            if not live[service]['State']['Running'] or live[service]['State'].get('Health', {}).get('Status') != 'healthy':
                raise Deferred('production_unhealthy', self.phase)
        # Backend image retains source files; compare normalized bytes, not checkout HEAD.
        for service in SERVICES:
            paths = [p for p in entries if relevant(p, service) and (
                (service == 'backend' and p.startswith(('backend/', 'scripts/', 'production/')))
                or (service in ('tunnel', 'frontend') and p in SHARED | {'production/run_caddy.py'})
                or (service == 'frontend' and p == 'production/Caddyfile'))]
            if service == 'tunnel':
                paths = [p for p in paths if p != 'production/run_caddy.py']
            mapping = {p: '/etc/caddy/Caddyfile' if p == 'production/Caddyfile' else '/app/' + p for p in paths}
            code = ("import json,hashlib;from pathlib import Path;mapping=" + repr(mapping) +
                    ";print(json.dumps({p:hashlib.sha256(Path(v).read_bytes().replace(b'\\r\\n',b'\\n')).hexdigest() if Path(v).is_file() else None for p,v in mapping.items()}))")
            observed = json.loads(self.docker('exec', live[service]['Id'], 'python3' if service == 'frontend' else 'python', '-c', code))
            for path in paths:
                expected = (release / path).read_bytes().replace(b'\r\n', b'\n')
                if observed.get(path) != hashlib.sha256(expected).hexdigest():
                    raise Failure('source_evidence_mismatch', self.phase)
        front_entries = self.entries(front_sha)
        if source_fingerprints(front_entries)['frontend'] != source_fingerprints(entries)['frontend']:
            raise Failure('frontend_evidence_mismatch', self.phase)
        fingerprints = source_fingerprints(entries, config)
        manifest = {}
        for service in SERVICES:
            group = service
            image = live[service]['Config']['Image']
            if self.image_id(image) != live[service]['Image']:
                raise Failure('image_reference_drift', self.phase)
            tag = f'{PROJECT}-{group}:git-{self.sha}-live-{live[service]["Image"].split(":")[1][:12]}'
            self.docker('image', 'tag', image, tag)
            config['services'][service]['image'] = tag
            manifest[service] = dict(image=tag, image_id=live[service]['Image'], source_sha=self.sha,
                source_fingerprint=fingerprints[service], config_fingerprint=runtime_signature(config, service),
                runtime_identity=runtime_identity(live[service]))
        for name in ('initialize', 'migrate'):
            config['services'][name]['image'] = manifest['backend']['image']
        assets = self.image_assets(manifest['frontend']['image'])
        self.verify_http('http://127.0.0.1:' + str(self.cfg['local_port']), assets)
        self.verify_http(self.cfg['public_url'], assets)
        self.state.update(manifest=manifest, config=str(self.config_path('adopted-' + self.sha, config)),
                          assets=assets, adopted_at=now(), failed={}, notices={}, last_checked=None)
        self.save()
        self.event(logging.INFO, 'deployment_adopted', outcome='success', services=list(SERVICES))

    def backup(self):
        output = self.compose(self.state['config'], 'exec', '-T', 'backend', 'python', 'production/manage_db.py', 'backup', phase='backup')
        match = re.search(r'/backups/([a-zA-Z0-9_.-]+\.db)', output)
        if not match:
            raise Failure('backup_failed', 'backup')
        path = within(self.root / '.production/backups' / match[1], self.root / '.production/backups')
        if not path.is_file():
            raise Failure('backup_failed', 'backup')
        return path

    def candidate_checks(self, release, config, changed):
        self.phase = 'test'
        backend_changed = 'backend' in changed
        test_image = config['services']['backend']['image']
        check_root = within(self.home / 'checks' / (self.sha + '-' + uuid4().hex[:8]), self.home / 'checks')
        check_root.mkdir(parents=True)
        containers, network = [], None
        marker = 'az-election.deploy.check=' + digest(str(self.home))[:16]
        def cleanup():
            for name in reversed(containers):
                try:
                    self.docker('rm', '-f', name, timeout=45)
                except Failure:
                    pass
            if network:
                try:
                    self.docker('network', 'rm', network, timeout=30)
                except Failure:
                    pass
        try:
            if backend_changed:
                data_mount = f'type=bind,source={release / "data"},target=/reference-data,readonly'
                code = ("import shutil,subprocess,sys;shutil.copytree('/reference-data','/app/data',dirs_exist_ok=True);"
                        "sys.exit(subprocess.call([sys.executable,'-m','pytest','production/tests',"
                        "'backend/tests/test_early_vote_schedule.py','backend/tests/test_early_vote_updates.py','-q']))")
                self.docker('run', '--rm', '--network', 'none', '--user', '0:0', '--mount', data_mount,
                            '--label',marker,test_image, 'python', '-c', code, timeout=600)
            if backend_changed or 'frontend' in changed:
                self.phase = 'test'
                # Public aggregates copied through SQLite online backup, never a live DB bind.
                saved = self.backup()
                local = check_root / 'state'
                local.mkdir()
                shutil.copy2(saved, local / 'elections.db')
                (check_root / 'backups').mkdir()
                self.docker('run', '--rm', '--network', 'none', '--user', '0:0',
                    '--label',marker,
                    '--mount', f'type=bind,source={local},target=/app/backend/local',
                    '--mount', f'type=bind,source={check_root / "backups"},target=/backups',
                    test_image, 'python', 'production/manage_db.py', 'migrate', phase='test')
                network = PROJECT + '-check-' + uuid4().hex[:10]
                # A separate bridge isolates service discovery from production.
                # Docker Desktop internal networks cannot publish to host Playwright.
                self.docker('network', 'create', '--label',marker, network)
                back = PROJECT + '-check-back-' + uuid4().hex[:10]
                containers.append(back)
                self.docker('run', '-d', '--name', back, '--label',marker,'--network', network, '--network-alias', 'backend',
                    '--user', '0:0', '--mount', f'type=bind,source={local},target=/app/backend/local',
                    '-e', 'DATABASE_URL=sqlite:////app/backend/local/elections.db',
                    test_image, 'python', 'production/run_backend.py')
            if backend_changed or 'frontend' in changed:
                port = free_port()
                front = PROJECT + '-check-front-' + uuid4().hex[:10]
                containers.append(front)
                self.docker('run', '-d', '--name', front, '--label',marker, '--network', network,
                    '-p', f'127.0.0.1:{port}:80', '--read-only', '--tmpfs', '/tmp', '--tmpfs', '/data', '--tmpfs', '/config',
                    config['services']['frontend']['image'])
                base = f'http://127.0.0.1:{port}'
                for attempt in range(30):
                    try:
                        self.verify_http(base)
                        break
                    except Failure:
                        if attempt == 29:
                            raise
                        time.sleep(1)
                self.command([self.cfg['npm'], 'ci'], cwd=release / 'frontend', phase='test')
                self.command([self.cfg['npm'], 'test'], cwd=release / 'frontend', phase='test')
                node = Path(self.cfg['npm']).parent / ('node.exe' if os.name == 'nt' else 'node')
                cli = release / 'frontend/node_modules/@playwright/test/cli.js'
                self.command([node, cli, 'install', 'chromium'], cwd=release / 'frontend', timeout=600, transient=True)
                # Only these reviewed specs are allowed: no live importer smoke test.
                os.environ['PLAYWRIGHT_BASE_URL'] = base
                try:
                    self.command([node, cli, 'test', 'catalog.spec.ts', 'explorer.spec.ts', 'house.spec.ts', '--workers=1'],
                                 cwd=release / 'frontend', timeout=600)
                finally:
                    os.environ.pop('PLAYWRIGHT_BASE_URL', None)
                declaration = read_json(release / 'production/migration-compatibility.json', {})
                if declaration.get('backward_compatible_with') == self.state['manifest']['backend']['source_sha']:
                    legacy = PROJECT + '-check-legacy-' + uuid4().hex[:10]
                    containers.append(legacy)
                    legacy_port = free_port()
                    self.docker('run', '-d', '--name', legacy, '--label',marker,'--network', network,
                        '-p', f'127.0.0.1:{legacy_port}:8000', '--user', '0:0',
                        '--mount', f'type=bind,source={local},target=/app/backend/local',
                        '-e', 'DATABASE_URL=sqlite:////app/backend/local/elections.db',
                        self.state['manifest']['backend']['image'], 'python', 'production/run_backend.py')
                    for attempt in range(30):
                        try:
                            self.verify_http(f'http://127.0.0.1:{legacy_port}', html=False)
                            break
                        except Failure:
                            if attempt == 29:
                                raise
                            time.sleep(1)
            if 'tunnel' in changed:
                self.docker('run', '--rm', '--network', 'none', '--entrypoint', 'cloudflared',
                            config['services']['tunnel']['image'], '--version')
                self.docker('run','--rm','--network','none','--entrypoint','python',
                            config['services']['tunnel']['image'],'-c','import production.run_tunnel')
        finally:
            cleanup()
            if self.cleanup_candidates():
                shutil.rmtree(within(check_root, self.home / 'checks'))

    def verify_live(self, config, affected, assets):
        self.phase = 'verify'
        live = self.inspect()
        for service in SERVICES:
            if not live[service]['State']['Running'] or live[service]['State'].get('Health', {}).get('Status') != 'healthy':
                raise Failure('health_failed', self.phase)
            if live[service]['Image'] != self.image_id(config['services'][service]['image']):
                raise Failure('image_reference_drift', self.phase)
            desired = config['services'][service]
            actual_env = dict(e.split('=', 1) for e in live[service]['Config']['Env'])
            if any(actual_env.get(k) != str(v) for k,v in desired.get('environment', {}).items()):
                raise Failure('runtime_drift', self.phase)
            if desired.get('command') and desired['command'] != live[service]['Config']['Cmd']:
                raise Failure('runtime_drift', self.phase)
        self.verify_http('http://127.0.0.1:' + str(self.cfg['local_port']), assets)
        self.verify_http(self.cfg['public_url'], assets)
        if affected:
            for attempt in range(20):
                ready = True
                for service in affected:
                    if self.cfg.get('external_scheduler') and service == 'scheduler':
                        continue
                    env = config['services'][service].get('environment', {})
                    logs = self.docker('logs', '--tail', '80', f'{PROJECT}-{service}-1')
                    if str(env.get('NEW_RELIC_LOGS_ENABLED', '')).lower() == 'true' and 'log_export_connected' not in logs:
                        ready = False
                    if service == 'backend' and env.get('NEW_RELIC_CONFIG_FILE') and 'Reporting to:' not in logs:
                        ready = False
                if ready:
                    break
                if attempt == 19:
                    raise Failure('monitoring_failed', self.phase)
                time.sleep(1)
        return live

    def bring_up(self, path, services, phase):
        # Old rollback journals may mention cron; never recreate or restart it.
        if set(services) - set(SERVICES) - {'scheduler'}:
            raise Failure('unsupported_service', phase)
        services = [service for service in services if service in SERVICES]
        if services:
            self.compose(path, 'up', '-d', '--no-deps', '--wait', '--wait-timeout', '180', *services, phase=phase)

    def rollback(self, journal):
        self.phase = 'rollback'
        if not journal['rollback_allowed']:
            self.rollback_result = 'blocked'
            self.state['blocked'] = True
            self.save()
            raise Failure('migration_recovery_required', self.phase)
        self.bring_up(journal['previous']['config'], journal['restore_services'], 'rollback')
        previous = journal['previous']
        live = self.verify_live(read_json(previous['config']), [], previous['assets'])
        for service in SERVICES:
            previous['manifest'][service]['runtime_identity'] = runtime_identity(live[service])
        for key in ('manifest', 'config', 'assets'):
            self.state[key] = previous[key]
        self.state.pop('journal', None)
        self.state['blocked'] = False
        self.rollback_result = 'succeeded'
        self.save()
        self.event(logging.WARNING, 'deployment_rolled_back', rollback='succeeded', services=journal['restore_services'])

    def activate(self, config_path, config, changed, sources, schema_change):
        started = getattr(self, 'started', time.monotonic())
        previous = {k: self.state[k] for k in ('manifest', 'config', 'assets')}
        restore = sorted(set(changed))
        journal = dict(commit=self.sha, previous=previous, target_config=str(config_path),
                       affected=changed, restore_services=restore, rollback_allowed=True, schema_change=schema_change)
        target_manifest = dict(previous['manifest'])
        for service in changed:
            target_manifest[service] = dict(image=config['services'][service]['image'],
                image_id=self.image_id(config['services'][service]['image']), source_sha=self.sha,
                source_fingerprint=sources[service], config_fingerprint=runtime_signature(config,service))
        journal['target_manifest'] = target_manifest
        self.state['journal'] = journal
        self.save()  # Recovery intent is durable before any production mutation.
        self.event(logging.INFO, 'deployment_started', services=changed)
        try:
            if 'backend' in changed:
                # Candidate image is explicit; initialize/migrate services are never auto-started.
                self.compose(previous['config'], 'stop', 'backend', phase='migrate')
                if schema_change:
                    journal['rollback_allowed'] = False  # Unknown/failed migrations cannot revert app blindly.
                    self.save()
                self.compose(config_path, 'run', '--rm', '--no-deps', 'backend',
                             'python', 'production/manage_db.py', 'migrate', phase='migrate')
                if schema_change:
                    declaration = read_json(Path(config['services']['backend']['build']['context']) /
                                            'production/migration-compatibility.json', {})
                    journal['rollback_allowed'] = declaration.get('backward_compatible_with') == previous['manifest']['backend']['source_sha']
                    self.save()
            self.bring_up(config_path, restore, 'activate')
            assets = self.image_assets(config['services']['frontend']['image'])
            live = self.verify_live(config, restore, assets)
            manifest = dict(previous['manifest'])
            for service in changed:
                manifest[service] = dict(image=config['services'][service]['image'], image_id=live[service]['Image'],
                    source_sha=self.sha, source_fingerprint=sources[service],
                    config_fingerprint=runtime_signature(config, service), runtime_identity=runtime_identity(live[service]))
            self.state.update(manifest=manifest, config=str(config_path), assets=assets,
                              previous=journal, deployed_at=now(), last_checked=self.sha,
                              last_result={'status':'deployed','commit':self.sha,'at':now()})
            self.state.pop('journal', None)
            self.save()
            self.event(logging.INFO, 'deployment_succeeded', services=changed, outcome='success',
                       duration_ms=round((time.monotonic()-started)*1000), rollback='not_needed')
        except Exception:
            try:
                self.rollback(journal)
            except Exception:
                self.rollback_result = 'blocked' if not journal['rollback_allowed'] else 'failed'
                self.state['blocked'] = True
                self.save()
                self.event(logging.CRITICAL, 'deployment_recovery_required', rollback='blocked', services=restore)
            raise Failure('activation_failed', self.phase) from None

    def cycle(self, retry=False):
        self.started = time.monotonic()
        self.current_affected = []
        self.rollback_result = 'not_needed'
        self.check_engine()
        self.cleanup_candidates()
        if self.state.get('journal') and self.state.get('blocked') and not self.state['journal']['rollback_allowed']:
            raise Deferred('migration_recovery_required')
        if self.state.get('journal'):
            journal = self.state['journal']
            self.sha = journal['commit']
            self.state['failed'][self.sha] = {'reason':'interrupted','at':now()}
            self.save()
            self.rollback(journal)
        if self.state.get('blocked'):
            raise Deferred('recovery_required')
        self.drift_check()
        self.fetch()
        if retry:
            self.state['failed'].pop(self.sha, None)
            self.save()
        if self.sha in self.state.get('failed', {}):
            self.state['last_result'] = {'status':'failed_commit_skipped','commit':self.sha,'at':now()}
            self.save()
            return
        release = self.release(self.sha)
        config = self.render(release)
        entries = self.entries(self.sha)
        sources = source_fingerprints(entries, config)
        old_sha = self.state['manifest']['backend']['source_sha']
        paths = self.git('diff', '--name-only', old_sha, self.sha).splitlines()
        if any(p.startswith('data/') for p in paths) and self.sha not in self.state.get('data_release_ack', {}):
            raise Failure('data_release_required', 'preflight')
        changed = affected_services(self.state['manifest'], sources, config)
        self.current_affected = changed
        if not changed:
            if self.state.get('last_checked') != self.sha:
                self.event(logging.INFO, 'deployment_noop', outcome='skipped')
            self.state.update(last_checked=self.sha, last_result={'status':'noop','commit':self.sha,'at':now()})
            self.save()
            return
        self.build(release, config, changed)
        self.candidate_checks(release, config, changed)
        candidate = self.config_path(self.sha, config)
        self.activate(candidate, config, changed, sources, migration_changed(paths))

    def run(self, retry=False):
        with exclusive_lock(self.home / 'deploy.lock') as locked:
            if not locked:
                return 0
            for _ in range(3):  # Finish an active deployment, then catch newer main; next task catches further churn.
                try:
                    self.cycle(retry=retry)
                    retry = False
                    observed = self.sha
                    self.fetch()
                    if self.sha == observed:
                        return 0
                except Deferred as exc:
                    self.notice(exc.reason)
                    return 0
                except Exception as exc:
                    if not isinstance(exc, Failure):
                        exc = Failure('command_failed', self.phase)
                    if self.sha:
                        self.state['failed'][self.sha] = {'reason':exc.reason,'phase':exc.phase,'at':now()}
                    self.state['last_result'] = {'status':'failed','reason':exc.reason,'phase':exc.phase,'commit':self.sha,'at':now()}
                    self.save()
                    self.event(logging.ERROR, 'deployment_failed', reason=exc.reason, outcome='failed', exit_code=exc.code,
                               services=self.current_affected, rollback=self.rollback_result,
                               duration_ms=round((time.monotonic()-getattr(self,'started',time.monotonic()))*1000))
                    return 1
            return 0

    def acknowledge_data_release(self, sha):
        """Record that an operator imported the data changes in `sha` into production."""
        self.state.setdefault('data_release_ack', {})[sha] = now()
        self.save()

    def accept_recovery(self):
        journal = self.state.get('journal')
        if not journal:
            raise Failure('no_previous_release')
        self.sha = journal['commit']
        for config_path, manifest in ((journal['previous']['config'], journal['previous']['manifest']),
                                      (journal['target_config'], journal['target_manifest'])):
            config = read_json(config_path)
            try:
                assets = self.image_assets(config['services']['frontend']['image'])
                live = self.verify_live(config, [], assets)
                code = ("from production.manage_db import check,DB;check(DB);"
                        "from alembic.config import Config;from alembic.script import ScriptDirectory;"
                        "import sqlite3;heads=set(ScriptDirectory.from_config(Config('backend/alembic.ini')).get_heads());"
                        "c=sqlite3.connect('file:/app/backend/local/elections.db?mode=ro',uri=True);"
                        "assert heads=={r[0] for r in c.execute('select version_num from alembic_version')}")
                self.docker('exec', live['backend']['Id'], 'python','-c',code)
            except Failure:
                continue
            for service in SERVICES:
                manifest[service]['runtime_identity'] = runtime_identity(live[service])
            self.state.update(manifest=manifest, config=config_path, assets=assets, blocked=False)
            self.state['failed'][journal['commit']] = {'reason':'operator_recovery','at':now()}
            self.state.pop('journal', None)
            self.save()
            self.event(logging.WARNING,'deployment_recovered',outcome='success')
            return
        raise Failure('migration_recovery_required','verify')


def setup_logging(worker):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from backend.app.observability import configure_logging, JsonFormatter, correlation_id, emit
    os.environ.update(NEW_RELIC_LOGS_ENABLED='true', NEW_RELIC_LOGS_REGION=worker.cfg.get('log_region','US'),
                      NEW_RELIC_LOGS_PER_MINUTE=str(worker.cfg.get('log_limit',10)),
                      NEW_RELIC_LOGS_KEY_FILE=str(worker.root / '.production/secrets/newrelic-license-key'))
    configure_logging('deploy_worker')
    folder = worker.home / 'logs'
    folder.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(folder / 'deploy.jsonl', maxBytes=1024*1024, backupCount=3, encoding='utf-8')
    handler.setFormatter(JsonFormatter('deploy_worker'))
    logging.getLogger().addHandler(handler)
    correlation_id.set(uuid4().hex)
    worker.emit = emit


def main():
    if sys.stdout is None:
        sys.stdout = open(os.devnull, 'w')
    if sys.stderr is None:
        sys.stderr = open(os.devnull, 'w')
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('action', choices=['run','retry','adopt','status','rollback','recover','accept-recovery','ack-data-release'])
    parser.add_argument('--commit', help='full commit SHA for ack-data-release')
    args = parser.parse_args()
    worker = Worker(read_json(args.config))
    if args.action == 'status':
        value = {k:worker.state.get(k) for k in ('last_result','last_checked','deployed_at','blocked','manifest','failed')}
        if worker.state.get('journal'):
            value['pending'] = {k:worker.state['journal'].get(k) for k in ('commit','affected','rollback_allowed')}
        print(json.dumps(value, indent=2))
        return 0
    setup_logging(worker)
    if args.action in ('run','retry'):
        if not worker.state.get('manifest'):
            raise Failure('not_initialized')
        return worker.run(retry=args.action == 'retry')
    with exclusive_lock(worker.home / 'deploy.lock') as locked:
        if not locked:
            raise Failure('deployment_in_progress')
        if args.action == 'adopt':
            worker.adopt()
        elif args.action == 'rollback':
            journal = worker.state.get('previous')
            if not journal:
                raise Failure('no_previous_release')
            worker.sha = journal['commit']
            worker.state['failed'][worker.sha] = {'reason':'manual_rollback','at':now()}
            worker.rollback(journal)
        elif args.action == 'recover':
            journal = worker.state.get('journal')
            if journal:
                worker.sha = journal['commit']
                worker.rollback(journal)
            else:
                worker.drift_check()
                worker.state['blocked'] = False
                worker.save()
        elif args.action == 'accept-recovery':
            worker.accept_recovery()
        elif args.action == 'ack-data-release':
            if not re.fullmatch(r'[0-9a-f]{40}', args.commit or ''):
                raise Failure('invalid_commit')
            worker.acknowledge_data_release(args.commit)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        # pythonw has no console; keep last-resort diagnostics static and redacted.
        logging.getLogger('elections').critical('deployment_worker_failed',
            extra={'event':'deployment_worker_failed', 'reason':getattr(exc,'reason',None),
                   'phase':getattr(exc,'phase',None)}, exc_info=False)
        raise SystemExit(1)
