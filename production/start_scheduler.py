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
    Path("/etc/cron.d/early-voting").write_text(
        "SHELL=/bin/sh\nPATH=/usr/local/bin:/usr/bin:/bin\n"
        "DATABASE_URL=sqlite:////app/backend/local/elections.db\n"
        f"TZ={zone}\n0 {entries} * * * app /usr/local/bin/python /app/production/refresh_job.py\n"
    )
    Path("/etc/cron.d/early-voting").chmod(0o644)
    print(f"Cron: hours {entries}, minute 00, timezone {zone}", flush=True)


def main():
    if "--check" in sys.argv:
        os.kill(int(Path("/run/crond.pid").read_text().split()[0]), 0)
        if not Path("/etc/cron.d/early-voting").is_file():
            raise SystemExit(1)
        return
    configure()
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
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    print("Startup refresh exit_code:", run.wait(), flush=True)
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
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, drain)
    signal.signal(signal.SIGINT, drain)
    raise SystemExit(cron.wait())


if __name__ == "__main__":
    main()
