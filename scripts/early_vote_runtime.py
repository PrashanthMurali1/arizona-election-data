"""Single-process refresh lock and local job audit, shared by manual/scheduled runs."""

import fcntl
import json
import logging
import os
import sys
import time
from uuid import uuid4
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / "backend/local"
LOG = LOCAL / "logs/early-voting-refresh.log"
STATUS = LOCAL / "early-voting-refresh-status.json"
LOCK = LOCAL / "early-voting-refresh.lock"
sys.path.insert(0, str(ROOT))
from backend.app.observability import JsonFormatter, VolumeFilter, correlation_id, emit, failure_level


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def run_refresh(callback, *, local=LOCAL):
    local = Path(local)
    logs = local / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger('elections')
    previous_level, previous_propagate = logger.level, logger.propagate
    level = os.getenv('APP_LOG_LEVEL', 'INFO').upper()
    logger.setLevel(level if level in {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'} else 'INFO')
    logger.propagate = False
    handler = RotatingFileHandler(logs / LOG.name, maxBytes=1024 * 1024, backupCount=3)
    handler.setFormatter(JsonFormatter('refresh'))
    limiter = VolumeFilter()
    logger.addFilter(limiter)
    from backend.app.log_export import configured_exporter, ExportingStreamHandler
    # Production refresh_job already configured a sanitized exporting handler.
    # Reuse it so one job never creates two forwarding paths.
    root_handler = next((h for h in logging.getLogger().handlers if hasattr(h, 'exporter')), None)
    exporter = None if root_handler else configured_exporter()
    console = root_handler or (ExportingStreamHandler(exporter) if exporter else logging.StreamHandler(sys.stdout))
    console.setFormatter(JsonFormatter('refresh'))
    logger.addHandler(handler)
    logger.addHandler(console)
    identity = correlation_id.set(uuid4().hex)
    started = time.monotonic()
    lock = (local / LOCK.name).open("a+")
    status_path = local / STATUS.name

    def save(status):
        temporary = status_path.with_suffix(f".{os.getpid()}.tmp")
        temporary.write_text(json.dumps(status, indent=2) + "\n")
        temporary.chmod(0o600)
        temporary.replace(status_path)

    try:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            emit(logging.WARNING, 'refresh_overlap_skipped', outcome='skipped')
            return 0
        lock.seek(0)
        lock.truncate()
        lock.write(str(os.getpid()))
        lock.flush()
        try:
            previous = json.loads(status_path.read_text())
        except (OSError, ValueError):
            previous = {}
        status = {
            "started_at": timestamp(), "status": "running", "pid": os.getpid(),
            "last_success_at": previous.get("last_success_at"),
        }
        save(status)
        emit(logging.INFO, 'refresh_started')
        if previous.get('last_success_at'):
            try:
                if (datetime.now(timezone.utc) - datetime.fromisoformat(previous['last_success_at'])).total_seconds() > 43200:
                    emit(logging.WARNING, 'refresh_last_success_stale')
            except (ValueError, TypeError):
                emit(logging.WARNING, 'refresh_status_invalid')
        try:
            code = int(callback() or 0)
            error = None if code == 0 else "One or more participation feeds failed; see refresh logs and source status."
        except Exception as exc:
            emit(failure_level(exc), 'refresh_exception', exc=exc, outcome='failed')
            code, error = 1, 'Refresh failed; see structured logs for exception type and location.'
        status.update(finished_at=timestamp(), exit_code=code, error=error, status="success" if code == 0 else "failed")
        if code == 0:
            status["last_success_at"] = status["finished_at"]
        save(status)
        emit(logging.INFO if code == 0 else logging.ERROR, 'refresh_completed',
             outcome='success' if code == 0 else 'failed', exit_code=code,
             duration_ms=round((time.monotonic()-started)*1000))
        return code
    finally:
        lock.close()  # flock is released even after exceptions or process termination.
        logger.removeHandler(handler)
        logger.removeHandler(console)
        logger.removeFilter(limiter)
        logger.setLevel(previous_level)
        logger.propagate = previous_propagate
        correlation_id.reset(identity)
        handler.close()
        if exporter:
            exporter.close()
