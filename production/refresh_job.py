"""Cron/foreground adapter: existing importer, bounded diagnostics and signals."""

import logging
import signal
import subprocess
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    folder = ROOT / "backend/local/logs"
    folder.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("scheduled-refresh")
    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(
        folder / "early-voting-scheduler.log", maxBytes=1024 * 1024, backupCount=3
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    logger.addHandler(handler)
    process = subprocess.Popen(
        [sys.executable, str(ROOT / "scripts/refresh_2026.py"), "--early-voting"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    def stop(signum, _frame):
        process.send_signal(signum)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    for line in process.stdout:
        logger.info(line.rstrip())
        print(line, end="", flush=True)
    code = process.wait()
    logger.info("Importer exit_code=%s", code)
    handler.close()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
