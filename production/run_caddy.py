"""Keep proxy diagnostics sanitized before stdout or New Relic export."""
import json
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.observability import emit
from production.run_tunnel import main


def caddy_event(line):
    try:
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError()
    except (ValueError, TypeError):
        emit(logging.WARNING, 'caddy_unstructured_diagnostic')
        return
    level = str(value.get('severity', value.get('level', ''))).upper()
    severity = {'WARN': logging.WARNING, 'WARNING': logging.WARNING, 'ERROR': logging.ERROR,
                'FATAL': logging.CRITICAL, 'PANIC': logging.CRITICAL}.get(level)
    if severity:
        emit(severity, 'caddy_proxy_failed' if severity >= logging.ERROR else 'caddy_warning',
             status_code=value.get('status'))


if __name__ == '__main__':
    try:
        raise SystemExit(main(binary='caddy', service='frontend', event_parser=caddy_event))
    except Exception as exc:
        emit(logging.CRITICAL, 'caddy_runtime_failed', exc=exc, outcome='failed')
        raise SystemExit(1)
