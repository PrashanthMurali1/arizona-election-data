"""Exercise private Compose imports/SSE and persistence; no vote reconciliation.

Runs live civicAPI participation imports and a deliberate failed refresh, followed
by recovery. Requires the prepared production stack, with its scheduler stopped.
"""

import hashlib
import json
import subprocess
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:8080"
ACTIVITY = BASE + "/api/elections/az-2026-early-voting/activity"
COMPOSE = ["docker", "compose"]


def run(*args, code=0):
    result = subprocess.run(
        [*COMPOSE, *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    if result.returncode != code:
        raise RuntimeError(result.stdout + result.stderr)
    return result.stdout


def get(url):
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    return response.json()


def counts():
    return json.loads(
        run(
            "exec",
            "-T",
            "backend",
            "python",
            "-c",
            "import json,sqlite3; c=sqlite3.connect('backend/local/elections.db'); "
            "print(json.dumps({t:c.execute('SELECT count(*) FROM '+t).fetchone()[0] "
            "for t in ['contests','vote_results','metric_observations','publication_snapshots']}))",
        )
    )


def metrics(value):
    return [
        (unit["geoid"], [(m["key"], m["value"]) for m in unit["metrics"]])
        for unit in [value["statewide"], *value["counties"]]
    ]


def next_revision(lines):
    for line in lines:
        if line.startswith("data: "):
            return json.loads(line[6:])["revision"]
    raise RuntimeError("SSE closed before revision notification")


def historical():
    values = {}
    for election in get(BASE + "/api/elections"):
        if election["year"] < 2026:
            value = get(BASE + "/api/elections/" + election["id"])
            values[election["id"]] = hashlib.sha256(
                json.dumps(value, sort_keys=True).encode()
            ).hexdigest()
    return values


def main():
    history = historical()
    before = get(ACTIVITY)
    with requests.get(
        BASE + "/api/elections/az-2026-early-voting/updates",
        stream=True,
        timeout=(5, 30),
    ) as response:
        response.raise_for_status()
        assert "text/event-stream" in response.headers["Content-Type"]
        assert response.headers["X-Accel-Buffering"] == "no"
        lines = response.iter_lines(chunk_size=1, decode_unicode=True)
        assert next_revision(lines) == before["revision"]
        run(
            "run", "--rm", "--no-deps", "backend", "python", "production/refresh_job.py"
        )
        changed = next_revision(lines)
        after = get(ACTIVITY)
        assert changed != before["revision"] and changed == after["revision"]
    print("PASS production proxy + committed import SSE notification", flush=True)
    stored = counts()
    run("run", "--rm", "--no-deps", "backend", "python", "production/refresh_job.py")
    assert counts() == stored
    print("PASS repeat import: unchanged stored record counts", flush=True)

    holder = subprocess.Popen(
        [
            *COMPOSE,
            "exec",
            "-T",
            "backend",
            "python",
            "-c",
            (
                "import fcntl,time; f=open('backend/local/early-voting-refresh.lock','a+'); "
                "fcntl.flock(f,fcntl.LOCK_EX); print('locked',flush=True); time.sleep(8)"
            ),
        ],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert holder.stdout.readline().strip() == "locked"
    skipped = run(
        "run", "--rm", "--no-deps", "backend", "python", "production/refresh_job.py"
    )
    assert "already running; skipped" in skipped
    holder.communicate(timeout=15)
    print("PASS cross-container overlapping-job prevention", flush=True)

    before = get(ACTIVITY)
    run(
        "run",
        "--rm",
        "--no-deps",
        "-e",
        "HTTPS_PROXY=http://127.0.0.1:9",
        "backend",
        "python",
        "production/refresh_job.py",
        code=1,
    )
    failed = get(ACTIVITY)
    assert metrics(failed) == metrics(before) and failed["failures"]
    print(
        "PASS deliberate network failure preserves last successful metrics", flush=True
    )
    run("run", "--rm", "--no-deps", "backend", "python", "production/refresh_job.py")
    assert not get(ACTIVITY)["failures"]
    print("PASS recovery refresh clears active failure status", flush=True)

    revision = get(ACTIVITY)["revision"]
    run("up", "-d", "--no-deps", "--force-recreate", "--wait", "backend", "frontend")
    assert counts() == stored and get(ACTIVITY)["revision"] == revision
    assert historical() == history
    with requests.get(
        BASE + "/api/elections/az-2026-early-voting/updates",
        stream=True,
        timeout=(5, 10),
    ) as response:
        assert (
            next_revision(response.iter_lines(chunk_size=1, decode_unicode=True))
            == revision
        )
    print(
        f"PASS persistence, SSE reconnect and {len(history)} historical view fingerprints after recreation",
        flush=True,
    )
    report = {
        "historical_views": len(history),
        "stored_counts": stored,
        "revision": revision,
        "checks": "passed",
    }
    (ROOT / ".production/check-report.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
