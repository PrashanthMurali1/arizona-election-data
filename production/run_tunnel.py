"""Supervise the pinned connector; never retain raw URL/header/error fields."""
import json
import logging
from pathlib import Path
import signal
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.observability import configure_logging, emit


def connector_event(line):
    try:
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError()
    except (ValueError, TypeError):
        emit(logging.WARNING, 'tunnel_unstructured_diagnostic')
        return
    # Raw cloudflared errors can contain the visitor URL, including its query.
    # Use only its severity and a static event classification.
    level = {'info': logging.INFO, 'warn': logging.WARNING, 'warning': logging.WARNING,
             'error': logging.ERROR, 'fatal': logging.CRITICAL,
             'panic': logging.CRITICAL}.get(value.get('level'))
    if level is None:
        return
    message = str(value.get('message', ''))
    if message.startswith('Registered tunnel connection'):
        event = 'tunnel_connection_registered'
    elif level >= logging.ERROR:
        event = 'tunnel_connection_failed'
    elif level == logging.WARNING:
        event = 'tunnel_warning'
    else:
        return  # Connection registration and lifecycle suffice at INFO.
    emit(level, event)


def main(*, binary='cloudflared', service='tunnel', event_parser=connector_event):
    configure_logging(service)
    prefix = 'tunnel' if binary == 'cloudflared' else 'caddy'
    started = time.monotonic()
    stopping = False
    process = subprocess.Popen([binary, *sys.argv[1:]], stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True, errors='replace')
    def stop(signum, _frame):
        nonlocal stopping
        stopping = True
        if process.poll() is None:
            process.send_signal(signum)
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    emit(logging.INFO, prefix + '_started')
    while line := process.stdout.readline(65536):
        event_parser(line)
    code = process.wait()
    emit(logging.INFO if stopping else logging.CRITICAL, prefix + '_stopped',
         outcome='success' if stopping else 'failed', exit_code=code,
         duration_ms=round((time.monotonic()-started)*1000))
    return code if stopping else code or 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        emit(logging.CRITICAL, 'tunnel_runtime_failed', exc=exc, outcome='failed')
        raise SystemExit(1)
