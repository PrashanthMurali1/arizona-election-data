"""Dedicated persistent cron container; never runs inside a web worker."""

import fcntl
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import logging
from backend.app.observability import configure_logging, emit


def configure():
    hours = int(os.environ.get("REFRESH_INTERVAL_HOURS", "6"))
    if hours < 1 or hours > 24 or 24 % hours:
        raise ValueError("REFRESH_INTERVAL_HOURS must divide 24")
    zone = os.environ.get("TZ", "Asia/Kolkata")
    ZoneInfo(zone)
    source = (Path("/usr/share/zoneinfo") / zone).resolve()
    if not source.is_relative_to(Path("/usr/share/zoneinfo")):
        raise ValueError("Invalid timezone")
    Path("/etc/localtime").unlink(missing_ok=True)
    Path("/etc/localtime").symlink_to(source)
    Path("/etc/timezone").write_text(zone + "\n")
    entries = ",".join(str(hour) for hour in range(0, 24, hours))
    level = os.getenv('APP_LOG_LEVEL', 'INFO').upper()
    if level not in {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}:
        level = 'INFO'
    export = 'true' if os.getenv('NEW_RELIC_LOGS_ENABLED', '').lower() == 'true' else 'false'
    region = 'EU' if os.getenv('NEW_RELIC_LOGS_REGION') == 'EU' else 'US'
    export_limit = max(1, min(int(os.getenv('NEW_RELIC_LOGS_PER_MINUTE', '10')), 60))
    Path("/etc/cron.d/early-voting").write_text(
        "SHELL=/bin/sh\nPATH=/usr/local/bin:/usr/bin:/bin\n"
        "DATABASE_URL=sqlite:////app/backend/local/elections.db\n"
        f"APP_LOG_LEVEL={level}\n"
        f"NEW_RELIC_LOGS_ENABLED={export}\nNEW_RELIC_LOGS_REGION={region}\nNEW_RELIC_LOGS_PER_MINUTE={export_limit}\n"
        f"TZ={zone}\n0 {entries} * * * root runuser -u app -- /usr/local/bin/python /app/production/refresh_job.py > /proc/1/fd/1 2> /proc/1/fd/2\n"
    )
    Path("/etc/cron.d/early-voting").chmod(0o644)
    emit(logging.INFO, 'scheduler_configured')


def main():
    if "--check" in sys.argv:
        os.kill(int(Path("/run/crond.pid").read_text().split()[0]), 0)
        if not Path("/etc/cron.d/early-voting").is_file():
            raise SystemExit(1)
        return
    configure()
    started = time.monotonic()
    emit(logging.INFO, 'scheduler_started', outcome='success')
    # Catch up once on container startup; failures do not stop future cron slots.
    run = subprocess.Popen(
        [
            "runuser",
            "-u",
            "app",
            "--",
            sys.executable,
            str(ROOT / "production/refresh_job.py"),
        ]
    )

    def stop(signum, _frame):
        run.send_signal(signum)
        emit(logging.INFO, 'scheduler_stopped', outcome='cancelled', duration_ms=round((time.monotonic()-started)*1000))
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    run.wait()  # The refresh runtime logs its own outcome exactly once.
    cron = subprocess.Popen(["/usr/sbin/cron", "-f"])

    def drain(_signum, _frame):
        # Stop new slots, then allow an active transaction/network fetch to finish.
        cron.terminate()
        cron.wait(timeout=5)
        deadline = time.monotonic() + 100
        lock_path = ROOT / "backend/local/early-voting-refresh.lock"
        if lock_path.exists():
            with lock_path.open("r") as lock:
                while time.monotonic() < deadline:
                    try:
                        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        break
                    except BlockingIOError:
                        time.sleep(0.5)
        emit(logging.INFO, 'scheduler_stopped', outcome='success', duration_ms=round((time.monotonic()-started)*1000))
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, drain)
    signal.signal(signal.SIGINT, drain)
    code = cron.wait()
    emit(logging.CRITICAL, 'scheduler_cron_exited', outcome='failed', exit_code=code)
    raise SystemExit(code or 1)


if __name__ == "__main__":
    configure_logging('scheduler')
    try:
        main()
    except Exception as exc:
        emit(logging.CRITICAL, 'scheduler_failed', exc=exc, outcome='failed')
        raise SystemExit(1)
