import json
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.app.log_export import LogExporter, ExportingStreamHandler
from backend.app.observability import JsonFormatter, VolumeFilter


def value(event='request_failed', severity='ERROR'):
    return dict(timestamp='2026-10-29T00:00:00Z', event=event, severity=severity,
                service='backend', correlation_id='a'*32)


def test_only_selected_levels_and_lifecycle_reach_ingest():
    batches = []
    exporter = LogExporter('test-key', sender=batches.append, start=False)
    for event, severity in [('routine', 'INFO'), ('backend_started', 'INFO'),
                            ('request_failed', 'ERROR'), ('warning', 'WARNING')]:
        exporter.submit(value(event, severity))
    assert exporter.flush_once()
    assert [r['event'] for r in batches[0]] == ['backend_started', 'request_failed', 'warning']
    assert exporter.accepted == 3


def test_export_happens_after_sanitization_and_duplicate_filter(capsys):
    exporter = LogExporter('test-key', start=False)
    handler = ExportingStreamHandler(exporter)
    handler.setFormatter(JsonFormatter('backend'))
    handler.addFilter(VolumeFilter())
    for _ in range(2):
        record = logging.LogRecord('elections', logging.ERROR, '', 0, 'PRIVATE_SENTINEL', (), None)
        record.event = 'request_failed'
        record.authorization = 'PRIVATE_SENTINEL'
        handler.handle(record)
    assert exporter.queue.qsize() == 1
    forwarded = exporter.queue.get_nowait()
    assert 'PRIVATE_SENTINEL' not in json.dumps(forwarded) + capsys.readouterr().out
    assert forwarded['message'] == 'request_failed'


def test_rate_limit_and_queue_bound_before_network():
    now = [0]
    exporter = LogExporter('test-key', per_minute=2, capacity=2, clock=lambda: now[0], start=False)
    for _ in range(20):
        exporter.submit(value())
    assert exporter.queue.qsize() == 2 and exporter.dropped == 18
    assert exporter.accepted == 0  # No network call from submit/request thread.
    now[0] = 61
    exporter.submit(value())
    assert exporter.queue.qsize() == 2 and exporter.dropped == 19
    exporter.queue.get_nowait()
    exporter.submit(value())
    assert exporter.queue.qsize() == 2


def test_delivery_failure_is_bounded_sanitized_and_not_reexported(caplog):
    def fail(batch):
        raise OSError('PRIVATE_SENTINEL')
    exporter = LogExporter('PRIVATE_SENTINEL', sender=fail, start=False)
    exporter.submit(value())
    assert not exporter.flush_once()
    assert exporter.failed == 1 and exporter.queue.empty()
    assert 'PRIVATE_SENTINEL' not in caplog.text
    exporter.submit(value('log_export_delivery_failed', 'WARNING'))
    assert exporter.queue.empty()


def test_log_api_uses_tls_header_auth_and_documented_payload(monkeypatch):
    import backend.app.log_export as module
    requests = []
    class Response:
        status = 202
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
    def send(request, timeout):
        requests.append(request)
        assert timeout == 5
        return Response()
    monkeypatch.setattr(module, 'urlopen', send)
    exporter = LogExporter('PRIVATE_SENTINEL', start=False)
    exporter.submit(value())
    assert exporter.flush_once()
    request = requests[0]
    assert request.full_url == 'https://log-api.newrelic.com/log/v1'
    assert request.get_header('Api-key') == 'PRIVATE_SENTINEL'
    assert 'PRIVATE_SENTINEL' not in request.full_url + request.data.decode()
    assert json.loads(request.data)[0]['logs'][0]['attributes']['event'] == 'request_failed'


def test_proxy_adapter_never_forwards_raw_message_query_or_headers(caplog):
    from production.run_caddy import caddy_event
    with caplog.at_level(logging.WARNING, logger='elections'):
        caddy_event(json.dumps({'severity':'error', 'msg':'PRIVATE_SENTINEL',
                               'request':{'uri':'?token=PRIVATE_SENTINEL'}, 'status':502}))
    assert 'PRIVATE_SENTINEL' not in caplog.text
    assert caplog.records[-1].event == 'caddy_proxy_failed'
