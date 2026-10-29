"""Bounded, allowlisted diagnostics: never serialize arbitrary messages or values."""

from collections import OrderedDict
from contextvars import ContextVar
from datetime import datetime, timezone
import logging
import os
import re
import sys
import threading
import time
import traceback
from uuid import uuid4

correlation_id = ContextVar('correlation_id', default=None)
log = logging.getLogger('elections')
FIELDS = {'outcome', 'duration_ms', 'status_code', 'exit_code', 'suppressed_count'}


def exception_details(exc):
    # Exception messages, source lines, SQL and local variables can contain secrets.
    return {
        'type': type(exc).__name__,
        'frames': [dict(file=os.path.basename(f.filename), function=f.name, line=f.lineno)
                   for f in traceback.extract_tb(exc.__traceback__)[-12:]],
    }


class JsonFormatter(logging.Formatter):
    def __init__(self, service):
        super().__init__()
        self.service = service

    def format(self, record):
        import json
        event = getattr(record, 'event', 'runtime_event')
        if not isinstance(event, str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,79}', event):
            event = 'runtime_event'
        value = dict(timestamp=datetime.fromtimestamp(record.created, timezone.utc).isoformat().replace('+00:00', 'Z'),
                     severity=record.levelname, service=self.service,
                     event=event)
        identity = getattr(record, 'correlation_id', None) or correlation_id.get()
        if isinstance(identity, str) and re.fullmatch(r'[0-9a-f]{32}', identity):
            value['correlation_id'] = identity
        for key in FIELDS:
            item = getattr(record, key, None)
            if isinstance(item, (int, float, bool)):
                value[key] = item
            elif key == 'outcome' and isinstance(item, str) and item in {'success', 'failed', 'skipped', 'cancelled'}:
                value[key] = item
        if getattr(record, 'feed', None) in {'requested', 'returned', 'inperson'}:
            value['feed'] = record.feed
        # Only route templates, never raw paths or queries, are accepted by callers.
        route = getattr(record, 'route_template', None)
        if route and re.fullmatch(r'[a-zA-Z0-9_/{}/.:-]{1,180}', route):
            value['route'] = route
        if record.exc_info and record.exc_info[1]:
            value['exception'] = exception_details(record.exc_info[1])
        return json.dumps(value, separators=(',', ':'), ensure_ascii=True)


class VolumeFilter(logging.Filter):
    """One warning/error per event/route/status/type per window, bounded state."""
    def __init__(self, window=300, capacity=1024, clock=time.monotonic):
        super().__init__()
        self.window, self.capacity, self.clock = window, capacity, clock
        self.seen = OrderedDict()
        self.lock = threading.Lock()

    def filter(self, record):
        if record.name == 'uvicorn.access':
            return False
        exc = record.exc_info[1] if record.exc_info else None
        if record.name != 'elections' and exc and getattr(exc, '_production_logged', False):
            return False
        if record.levelno < logging.WARNING:
            return record.name == 'elections'
        if record.levelno >= logging.CRITICAL:
            return True
        key = (getattr(record, 'event', record.name), getattr(record, 'route_template', None),
               getattr(record, 'status_code', None), type(exc).__name__ if exc else None,
               getattr(record, 'feed', None))
        with self.lock:
            now = self.clock()
            previous = self.seen.get(key)
            if previous and now - previous[0] < self.window:
                self.seen[key] = (previous[0], previous[1] + 1)
                return False
            record.suppressed_count = previous[1] if previous else 0
            self.seen[key] = (now, 0)
            self.seen.move_to_end(key)
            if len(self.seen) > self.capacity:
                self.seen.popitem(last=False)
        return True


def configure_logging(service, *, handler=None):
    if handler is None:
        from .log_export import configured_exporter, ExportingStreamHandler
        exporter = configured_exporter()
        handler = ExportingStreamHandler(exporter) if exporter else logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter(service))
    handler.addFilter(VolumeFilter())
    root = logging.getLogger()
    for previous in root.handlers:
        if hasattr(previous, 'exporter'):
            previous.exporter.close()
    root.handlers[:] = [handler]
    level = os.getenv('APP_LOG_LEVEL', 'INFO').upper()
    root.setLevel(level if level in {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'} else 'INFO')
    for name in ('uvicorn', 'uvicorn.error', 'uvicorn.access'):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True
    log.setLevel(logging.NOTSET)


def emit(level, event, *, exc=None, **fields):
    if not re.fullmatch(r'[a-z][a-z0-9_]{0,79}', event):
        raise ValueError('Event names must be static identifiers')
    log.log(level, event, extra={'event': event, **fields},
            exc_info=(type(exc), exc, exc.__traceback__) if exc else None)
    if exc:
        try:
            exc._production_logged = True
        except (AttributeError, TypeError):
            pass


def failure_level(exc):
    original = getattr(exc, 'orig', exc)
    code = getattr(original, 'sqlite_errorcode', 0) or 0
    return logging.CRITICAL if code & 255 in {11, 26} else logging.ERROR


class RequestLogging:
    """Pure ASGI middleware preserves SSE streaming and cancellation semantics."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        identity = uuid4().hex
        token = correlation_id.set(identity)
        started = time.monotonic()
        status = None

        async def response(message):
            nonlocal status
            if message['type'] == 'http.response.start':
                status = message['status']
                message = {**message, 'headers': [*message.get('headers', []),
                           (b'x-request-id', identity.encode())]}
            await send(message)

        try:
            await self.app(scope, receive, response)
        except Exception as exc:
            emit(failure_level(exc), 'database_failed' if hasattr(exc, 'orig') else 'request_failed',
                 exc=exc, route_template=getattr(scope.get('route'), 'path', '/unmatched'),
                 duration_ms=round((time.monotonic()-started)*1000), status_code=status or 500)
            # Uvicorn still sees the exception; avoid a second local traceback.
            try:
                exc._production_logged = True
            except (AttributeError, TypeError):
                pass
            raise
        else:
            if status and status >= 400 and status != 404:
                emit(logging.ERROR if status >= 500 else logging.WARNING, 'request_rejected',
                     route_template=getattr(scope.get('route'), 'path', '/unmatched'),
                     duration_ms=round((time.monotonic()-started)*1000), status_code=status)
        finally:
            correlation_id.reset(token)
