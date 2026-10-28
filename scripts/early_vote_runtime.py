"""Single-process refresh lock and local job audit, shared by manual/scheduled runs."""

import fcntl
import json
import logging
import os
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / "backend/local"
LOG = LOCAL / "logs/early-voting-refresh.log"
STATUS = LOCAL / "early-voting-refresh-status.json"
LOCK = LOCAL / "early-voting-refresh.lock"


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def run_refresh(callback, *, local=LOCAL):
    local = Path(local)
    logs = local / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(f"early-voting-refresh.{os.getpid()}")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    handler = RotatingFileHandler(logs / LOG.name, maxBytes=1024 * 1024, backupCount=3)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%dT%H:%M:%S%z"))
    logger.addHandler(handler)
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
            logger.info("SKIPPED: another early-voting refresh is running")
            print("Early-voting refresh already running; skipped.", flush=True)
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
        logger.info("STARTED pid=%s", os.getpid())
        try:
            code = int(callback() or 0)
            error = None if code == 0 else "One or more participation feeds failed; see refresh logs and source status."
        except Exception as exc:
            logger.exception("FAILED: refresh raised an exception")
            code, error = 1, str(exc)
        status.update(finished_at=timestamp(), exit_code=code, error=error, status="success" if code == 0 else "failed")
        if code == 0:
            status["last_success_at"] = status["finished_at"]
        save(status)
        logger.info("%s exit_code=%s error=%s", status["status"].upper(), code, error)
        print(f"Early-voting refresh {status['status']}; log: {logs / LOG.name}", flush=True)
        return code
    finally:
        lock.close()  # flock is released even after exceptions or process termination.
        logger.removeHandler(handler)
        handler.close()
