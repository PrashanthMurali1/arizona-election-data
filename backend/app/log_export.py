"""Nonblocking, bounded export of already-sanitized events to New Relic Logs."""
import atexit
import json
import logging
import os
from pathlib import Path
from queue import Empty, Full, Queue
import threading
import time
from urllib.request import Request, urlopen

LIFECYCLE = {'backend_started', 'backend_stopped', 'scheduler_started', 'scheduler_stopped',
             'refresh_completed', 'tunnel_started', 'tunnel_stopped', 'caddy_started', 'caddy_stopped',
             'deployment_adopted', 'deployment_started', 'deployment_succeeded', 'deployment_noop'}
ENDPOINTS = {'US': 'https://log-api.newrelic.com/log/v1',
             'EU': 'https://log-api.eu.newrelic.com/log/v1'}
FIELDS = {'timestamp', 'severity', 'service', 'event', 'correlation_id', 'route', 'feed',
          'outcome', 'duration_ms', 'status_code', 'exit_code', 'suppressed_count', 'exception',
          'trace.id', 'span.id', 'entity.guid', 'entity.name', 'entity.type'}
FIELDS.update({'commit_sha', 'services', 'phase', 'rollback', 'reason'})


class LogExporter:
    def __init__(self, key, *, region='US', per_minute=10, capacity=100,
                 sender=None, clock=time.monotonic, start=True):
        self.key = key
        self.endpoint = ENDPOINTS[region]
        self.per_minute = max(1, min(int(per_minute), 60))
        self.queue = Queue(maxsize=capacity)
        self.clock, self.started, self.count = clock, clock(), 0
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.sender = sender or self.send
        self.accepted = self.failed = self.dropped = 0
        self.thread = None
        if start:
            self.thread = threading.Thread(target=self.run, name='newrelic-log-export', daemon=True)
            self.thread.start()
            atexit.register(self.close)

    def submit(self, value):
        if value.get('event', '').startswith('log_export_'):
            return
        if value.get('severity') not in {'WARNING', 'ERROR', 'CRITICAL'} and value.get('event') not in LIFECYCLE:
            return
        # Callers must provide JsonFormatter output. Drop all non-allowlisted fields.
        event = {key: item for key, item in value.items() if key in FIELDS}
        event['message'] = value['event']
        event['application'] = 'Arizona Election Explorer (Production)'
        event['environment'] = 'production'
        if len(json.dumps(event).encode()) > 8192:
            event.pop('exception', None)
        with self.lock:
            now = self.clock()
            if now - self.started >= 60:
                self.started, self.count = now, 0
            if self.count >= self.per_minute:
                self.dropped += 1
                return
            self.count += 1
        try:
            self.queue.put_nowait(event)
        except Full:
            self.dropped += 1

    def send(self, batch):
        logs = [dict(timestamp=value['timestamp'], message=value['message'],
                     attributes={k: v for k, v in value.items() if k not in {'timestamp', 'message'}})
                for value in batch]
        request = Request(self.endpoint, data=json.dumps([{'logs': logs}]).encode(),
                          headers={'Content-Type': 'application/json', 'Api-Key': self.key}, method='POST')
        with urlopen(request, timeout=5) as response:
            if response.status != 202:
                raise OSError('Log ingest was not accepted')

    def flush_once(self):
        batch = []
        while len(batch) < 10:
            try:
                batch.append(self.queue.get_nowait())
            except Empty:
                break
        if not batch:
            return True
        try:
            self.sender(batch)
            first = self.accepted == 0
            self.accepted += len(batch)
            if first:
                logging.getLogger('elections').info('log_export_connected',
                    extra={'event': 'log_export_connected'})
        except Exception:
            # No recursive forwarding, raw HTTP errors, headers or key logging.
            self.failed += len(batch)
            logging.getLogger('elections').warning('log_export_delivery_failed',
                extra={'event': 'log_export_delivery_failed'})
            return False
        return True

    def run(self):
        while not self.stop.wait(5):
            if not self.flush_once():
                # No tight retry loop or unlimited backlog on an outage.
                self.stop.wait(60)
        self.flush_once()

    def close(self):
        self.stop.set()
        if self.thread:
            self.thread.join(timeout=2)


class ExportingStreamHandler(logging.StreamHandler):
    """Export after local volume filtering and formatting, never raw LogRecords."""
    def __init__(self, exporter):
        import sys
        super().__init__(sys.stdout)
        self.exporter = exporter

    def emit(self, record):
        super().emit(record)
        # Use exactly the formatter that strips arbitrary messages/attributes.
        value = json.loads(self.format(record))
        try:
            from newrelic.agent import get_linking_metadata
            value.update({key: item for key, item in get_linking_metadata().items()
                          if key in {'trace.id', 'span.id', 'entity.guid', 'entity.name', 'entity.type'}})
        except ImportError:
            pass
        self.exporter.submit(value)


def configured_exporter():
    if os.getenv('NEW_RELIC_LOGS_ENABLED', '').lower() != 'true':
        return None
    key = Path(os.getenv('NEW_RELIC_LOGS_KEY_FILE', '/run/secrets/newrelic_license_key')).read_text(encoding='utf-8-sig').strip()
    if not key or any(c.isspace() for c in key):
        raise ValueError('Invalid log ingest credential file')
    return LogExporter(key, region=os.getenv('NEW_RELIC_LOGS_REGION', 'US'),
                       per_minute=os.getenv('NEW_RELIC_LOGS_PER_MINUTE', '10'))
