"""Failure-path checks use synthetic ASGI apps and disposable job state only."""
import io
import json
import logging
from pathlib import Path
import sqlite3
import sys

import pytest
from starlette.applications import Starlette
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Route
from starlette.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.app.observability import (
    JsonFormatter, RequestLogging, VolumeFilter, configure_logging, emit, failure_level,
)


@pytest.fixture
def output():
    root = logging.getLogger()
    previous = root.handlers[:], root.level
    stream = io.StringIO()
    configure_logging('test', handler=logging.StreamHandler(stream))
    yield stream
    root.handlers[:], root.level = previous


def rows(output):
    return [json.loads(line) for line in output.getvalue().splitlines()]


def test_exception_redaction_drops_messages_headers_sql_and_unknown_fields(output):
    secret = 'PRIVATE_SENTINEL_DO_NOT_LOG'
    try:
        raise ValueError(f'password={secret} https://user:{secret}@host/?token={secret}')
    except ValueError as exc:
        emit(logging.ERROR, 'request_failed', exc=exc, password=secret,
             request_body=secret, headers={'Authorization': secret}, outcome=secret)
        # Even arbitrary third-party log messages are not serialized.
        logging.getLogger('library').error('secret=%s', secret)
    assert secret not in output.getvalue()
    event = rows(output)[0]
    assert event['exception']['type'] == 'ValueError'
    assert event['exception']['frames'][-1]['function'].startswith('test_exception')
    assert event['timestamp'].endswith('Z') and event['severity'] == 'ERROR'
    assert event['service'] == 'test' and 'outcome' not in event


def test_duplicate_suppression_window_count_and_bounded_memory():
    now = [0]
    limiter = VolumeFilter(window=10, capacity=2, clock=lambda: now[0])
    def record(name='repeated'):
        r = logging.LogRecord('elections', logging.WARNING, '', 0, '', (), None)
        r.event = name
        return r
    assert limiter.filter(record())
    assert not limiter.filter(record())
    assert not limiter.filter(record())
    now[0] = 10
    recovered = record()
    assert limiter.filter(recovered) and recovered.suppressed_count == 2
    for name in ('second', 'third'):
        assert limiter.filter(record(name))
    assert len(limiter.seen) == 2


def test_request_failures_have_correlation_but_no_raw_request_data(output):
    async def endpoint(request):
        await request.body()
        raise ValueError('PRIVATE_SENTINEL')
    app = Starlette(routes=[Route('/items/{item}', endpoint, methods=['POST'])])
    app.add_middleware(RequestLogging)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post('/items/PRIVATE_SENTINEL?token=PRIVATE_SENTINEL',
                               headers={'Authorization': 'PRIVATE_SENTINEL', 'Cookie': 'PRIVATE_SENTINEL'},
                               content='PRIVATE_SENTINEL')
    assert response.status_code == 500
    events = rows(output)
    assert len(events) == 1 and events[0]['event'] == 'request_failed'
    assert events[0]['route'] == '/items/{item}'
    assert len(events[0]['correlation_id']) == 32
    assert 'PRIVATE_SENTINEL' not in output.getvalue()


def test_success_health_404_and_streaming_are_quiet(output):
    async def healthy(request):
        return JSONResponse({'status': 'ok'})
    async def stream(request):
        async def events():
            yield ': heartbeat\n\n'
            yield 'data: complete\n\n'
        return StreamingResponse(events(), media_type='text/event-stream')
    app = Starlette(routes=[Route('/api/health', healthy), Route('/updates', stream)])
    app.add_middleware(RequestLogging)
    with TestClient(app) as client:
        a, b = client.get('/api/health'), client.get('/api/health')
        assert a.headers['x-request-id'] != b.headers['x-request-id']
        assert 'data: complete' in client.get('/updates').text
        assert client.get('/missing').status_code == 404
    assert not rows(output)


@pytest.mark.parametrize('status,severity', [(403, 'WARNING'), (503, 'ERROR')])
def test_handled_failure_status_and_repetition(output, status, severity):
    async def endpoint(request):
        return JSONResponse({}, status_code=status)
    app = Starlette(routes=[Route('/failed', endpoint)])
    app.add_middleware(RequestLogging)
    with TestClient(app) as client:
        for _ in range(3):
            assert client.get('/failed').status_code == status
    assert len(rows(output)) == 1
    assert rows(output)[0]['severity'] == severity


def test_duplicate_uvicorn_exception_is_suppressed(output):
    try:
        raise RuntimeError('never copy this')
    except RuntimeError as exc:
        emit(logging.ERROR, 'request_failed', exc=exc)
        logging.getLogger('uvicorn.error').error('ASGI exception', exc_info=True)
    assert len(rows(output)) == 1


def test_corrupt_database_is_critical_and_temporary_failure_is_error():
    exc = sqlite3.DatabaseError('secret SQL omitted')
    exc.sqlite_errorcode = sqlite3.SQLITE_CORRUPT
    assert failure_level(exc) == logging.CRITICAL
    assert failure_level(sqlite3.OperationalError('database is locked')) == logging.ERROR


def test_backend_database_startup_failure_is_critical(output, monkeypatch):
    import asyncio
    from backend.app import main
    def unavailable():
        raise RuntimeError('PRIVATE_SENTINEL')
    monkeypatch.setattr(main, 'SessionLocal', unavailable)
    async def start():
        async with main.lifespan(main.app):
            pytest.fail('backend started without database')
    with pytest.raises(RuntimeError):
        asyncio.run(start())
    assert rows(output)[0]['event'] == 'backend_startup_failed'
    assert rows(output)[0]['severity'] == 'CRITICAL'
    assert 'PRIVATE_SENTINEL' not in output.getvalue()


def test_refresh_success_failure_skip_preserve_state_and_sanitize(tmp_path, capsys):
    from scripts.early_vote_runtime import run_refresh
    import fcntl
    assert run_refresh(lambda: 0, local=tmp_path) == 0
    status_path = tmp_path / 'early-voting-refresh-status.json'
    previous = json.loads(status_path.read_text())['last_success_at']
    def fail():
        raise RuntimeError('PRIVATE_SENTINEL')
    assert run_refresh(fail, local=tmp_path) == 1
    failed = json.loads(status_path.read_text())
    assert failed['last_success_at'] == previous and failed['status'] == 'failed'
    with (tmp_path / 'early-voting-refresh.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert run_refresh(lambda: pytest.fail('overlap ran'), local=tmp_path) == 0
        assert json.loads(status_path.read_text()) == failed
    content = (tmp_path / 'logs/early-voting-refresh.log').read_text()
    assert 'PRIVATE_SENTINEL' not in content + capsys.readouterr().out + status_path.read_text()
    events = [json.loads(line) for line in content.splitlines()]
    assert any(r['event'] == 'refresh_exception' and r['severity'] == 'ERROR' for r in events)
    assert any(r.get('outcome') == 'skipped' for r in events)
    assert all(len(r['correlation_id']) == 32 for r in events)


def test_retired_cron_is_not_packaged_or_configured():
    root = Path(__file__).resolve().parents[2]
    assert not (root / 'production/start_scheduler.py').exists()
    assert '\n  scheduler:' not in (root / 'compose.yaml').read_text()
    assert '\n  scheduler:' not in (root / 'compose.newrelic.yaml').read_text()
    assert ' cron ' not in (root / 'production/backend.Dockerfile').read_text()


def test_newrelic_log_instrumentation_and_forwarding_disabled():
    import configparser
    config = configparser.ConfigParser()
    config.read(Path(__file__).resolve().parents[1] / 'newrelic.ini')
    assert not config.getboolean('newrelic', 'application_logging.enabled')
    assert not config.getboolean('newrelic', 'application_logging.forwarding.enabled')
    assert config.getboolean('newrelic', 'strip_exception_messages.enabled')


def test_connector_errors_cannot_leak_visitor_url_or_credentials(output):
    from production.run_tunnel import connector_event
    connector_event(json.dumps({'level': 'error', 'message': 'Request failed PRIVATE_SENTINEL',
                               'error': 'PRIVATE_SENTINEL', 'dest': 'https://host/?token=PRIVATE_SENTINEL'}))
    connector_event('unstructured PRIVATE_SENTINEL')
    connector_event(json.dumps({'level': 'debug', 'message': 'PRIVATE_SENTINEL'}))
    assert 'PRIVATE_SENTINEL' not in output.getvalue()
    assert [r['severity'] for r in rows(output)] == ['ERROR', 'WARNING']


def test_deployment_failure_guidance_fields_are_allowlisted_and_bounded():
    import json
    from backend.app.observability import JsonFormatter
    formatter = JsonFormatter('deploy_worker')
    def render(**fields):
        record = logging.LogRecord('deploy_worker', logging.ERROR, __file__, 1, '', (), None)
        record.__dict__.update(event='deployment_failed', **fields)
        return json.loads(formatter.format(record))
    good = render(reason='data_release_required', phase='preflight', next_action='ack_data_release', changed_data_paths=56)
    assert good['next_action'] == 'ack_data_release' and good['changed_data_paths'] == 56 and good['phase'] == 'preflight'
    bad = render(next_action='run; rm -rf /', changed_data_paths='secret')
    assert 'next_action' not in bad and 'changed_data_paths' not in bad
