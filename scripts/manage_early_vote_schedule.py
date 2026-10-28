"""Prepare/install/inspect/remove the local macOS early-voting LaunchAgent."""

import argparse
import json
import os
import plistlib
import re
import subprocess
import sys
from datetime import datetime, time, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABEL = "org.arizona-election-explorer.early-voting"
LOCAL = ROOT / "backend/local"
STAGED = LOCAL / "launchd" / f"{LABEL}.plist"


def configuration(root=ROOT, hours=6):
    if hours < 1 or hours > 24 or 24 % hours:
        raise ValueError("Interval hours must be a positive divisor of 24")
    root = Path(root).absolute()
    database = os.environ.get("DATABASE_URL", f"sqlite:///{root / 'backend/local/elections.db'}")
    if database.startswith("sqlite:///"):
        path = database[len("sqlite:///"):]
        if path == ":memory:":
            raise ValueError("Scheduled refresh requires a persistent database")
        if not Path(path).is_absolute():
            database = f"sqlite:///{root / path}"
    logs = root / "backend/local/logs"
    return {
        "Label": LABEL,
        "ProgramArguments": [str(root / ".venv/bin/python"), str(root / "scripts/refresh_2026.py"), "--early-voting"],
        "WorkingDirectory": str(root),
        "EnvironmentVariables": {"DATABASE_URL": database, "PYTHONUNBUFFERED": "1", "PATH": "/usr/bin:/bin:/usr/sbin:/sbin"},
        "StartCalendarInterval": [{"Hour": hour, "Minute": 0} for hour in range(0, 24, hours)],
        "RunAtLoad": True,
        "ProcessType": "Background",
        "StandardOutPath": str(logs / "early-voting-scheduler.stdout.log"),
        "StandardErrorPath": str(logs / "early-voting-scheduler.stderr.log"),
    }


def prepare(hours=6):
    config = configuration(hours=hours)
    for program in config["ProgramArguments"][:2]:
        if not Path(program).is_file():
            raise ValueError(f"Required runtime file is missing: {program}")
    (LOCAL / "logs").mkdir(parents=True, exist_ok=True)
    STAGED.parent.mkdir(parents=True, exist_ok=True)
    STAGED.write_bytes(plistlib.dumps(config))
    STAGED.chmod(0o600)
    return config


def next_run(config, now=None):
    now = now or datetime.now().astimezone()
    candidates = [
        datetime.combine((now + timedelta(days=day)).date(), time(entry["Hour"], entry.get("Minute", 0))).astimezone()
        for day in (0, 1)
        for entry in config["StartCalendarInterval"]
    ]
    return min(value for value in candidates if value > now).isoformat()


def launchctl(*args, check=False):
    return subprocess.run(["/bin/launchctl", *args], capture_output=True, text=True, check=check)


def report(target_file, target):
    query = launchctl("print", target)
    config_file = target_file if target_file.exists() else STAGED
    config = plistlib.loads(config_file.read_bytes()) if config_file.exists() else None
    state = re.search(r"^\s*state = (.+)$", query.stdout, re.M)
    exit_code = re.search(r"^\s*last exit code = (.+)$", query.stdout, re.M)
    timezone_path = str(Path("/etc/localtime").resolve())
    timezone_name = timezone_path.split("/zoneinfo/")[-1] if "/zoneinfo/" in timezone_path else datetime.now().astimezone().tzname()
    try:
        last_job = json.loads((LOCAL / "early-voting-refresh-status.json").read_text())
    except (OSError, ValueError):
        last_job = None
    # Never print the plist's database environment, which may contain credentials.
    print(json.dumps({
        "label": LABEL, "installed": target_file.exists(), "loaded": query.returncode == 0,
        "state": state[1] if state else None, "last_exit_code": exit_code[1] if exit_code else None,
        "calendar_hours": [entry["Hour"] for entry in config["StartCalendarInterval"]] if config else [],
        "timezone": timezone_name,
        "next_scheduled_run": next_run(config) if config and query.returncode == 0 else None,
        "agent_path": str(target_file), "prepared_path": str(STAGED),
        "log": str(LOCAL / "logs/early-voting-refresh.log"),
        "stdout_log": config.get("StandardOutPath") if config else None,
        "stderr_log": config.get("StandardErrorPath") if config else None,
        "last_job": last_job,
    }, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "install", "status", "remove"])
    parser.add_argument("--interval-hours", type=int, default=6)
    args = parser.parse_args()
    if sys.platform != "darwin":
        raise SystemExit("This checkout uses macOS launchd; activation must occur on its macOS host")
    target_file = Path.home() / "Library/LaunchAgents" / f"{LABEL}.plist"
    domain = f"gui/{os.getuid()}"
    target = f"{domain}/{LABEL}"
    if args.action == "prepare":
        prepare(args.interval_hours)
    elif args.action == "install":
        config = prepare(args.interval_hours)
        if launchctl("print", target).returncode == 0:
            launchctl("bootout", target, check=True)
        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.write_bytes(plistlib.dumps(config))
        target_file.chmod(0o600)
        launchctl("bootstrap", domain, str(target_file), check=True)
    elif args.action == "remove":
        if launchctl("print", target).returncode == 0:
            launchctl("bootout", target, check=True)
        target_file.unlink(missing_ok=True)
    report(target_file, target)


if __name__ == "__main__":
    main()
