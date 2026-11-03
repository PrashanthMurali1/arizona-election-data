"""Offline controlled comparison. Run: .venv/Scripts/python.exe scripts/benchmark_midterm_persistence.py

HEAD supplies the baseline implementation. Each fake search/detail request sleeps 200ms.
All DB/files are temporary; no real upstream or application database is opened.
Cold means first application load in this process, not a flushed OS disk cache.
"""
import argparse
import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
import time
import types

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--delay-ms", type=float, default=200)
    parser.add_argument("--warm-loads", type=int, default=20)
    parser.add_argument("--baseline", default="HEAD", help="Git revision containing the previous file-based implementation")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="midterm-benchmark-") as directory:
        folder = Path(directory)
        os.environ["DATABASE_URL"] = "sqlite:///" + str(folder / "benchmark.db")
        import requests
        from backend.app import midterm, live_results
        from backend.app.database import engine, SessionLocal
        from backend.app.models import LiveRaceSnapshot

        # Fail closed if any implementation tries to bypass the controlled fake.
        def forbidden(*args, **kwargs):
            raise AssertionError("Real upstream access is forbidden in this benchmark")
        requests.get = forbidden
        source = subprocess.check_output(
            ["git", "show", f"{args.baseline}:backend/app/midterm.py"], cwd=ROOT, text=True)
        baseline = types.ModuleType("backend.app._benchmark_baseline")
        baseline.__file__ = str(ROOT / "backend/app/midterm.py")
        sys.modules[baseline.__name__] = baseline
        exec(compile(source, baseline.__file__, "exec"), baseline.__dict__)
        fixture = json.loads((ROOT / "backend/tests/midterm_search.json").read_text())
        county_detail = {"region_results": {
            str(i): {"type": "County", "fips": f"04{2*i+1:03d}",
                     "name": f"Synthetic county {i+1}", "percent_reporting": 0,
                     "candidates": copy.deepcopy(next(r["candidates"] for r in fixture["races"]
                                                       if r["type"] == "Governor"))}
            for i in range(15)}}
        calls = []

        class FakeResponse:
            def __init__(self, value):
                self.value = value
                self.content = json.dumps(value).encode()

            def json(self):
                return copy.deepcopy(self.value)

        def fake_get(url, **kwargs):
            calls.append(url)
            time.sleep(args.delay_ms / 1000)
            return FakeResponse(fixture if url == baseline.SEARCH_URL else county_detail)

        baseline.get = fake_get
        baseline.DIR = folder / "missing-snapshot"
        LiveRaceSnapshot.__table__.create(engine)
        value = midterm.normalize(fixture, datetime.now(timezone.utc).isoformat())
        for office in midterm.STATEWIDE:
            for race in value["offices"][office]:
                race.counties = midterm.counties(county_detail)
        live_results.publish(midterm.to_json(value), session_factory=SessionLocal)

        results = []

        def measure(name, loader, model):
            before = len(calls)
            start = time.perf_counter()
            result = loader()
            cold = (time.perf_counter() - start) * 1000
            cold_calls = len(calls) - before
            durations = []
            before = len(calls)
            for _ in range(args.warm_loads):
                start = time.perf_counter()
                loader()
                durations.append((time.perf_counter() - start) * 1000)
            output = result if hasattr(result, "model_dump_json") else model(**result)
            results.append({"path": name, "cold_ms": round(cold, 3),
                "warm_median_ms": round(statistics.median(durations), 3),
                "payload_bytes": len(output.model_dump_json().encode()),
                "races": sum(len(races) for races in output.offices.values()),
                "cold_upstream_calls": cold_calls, "warm_upstream_calls": len(calls)-before})

        old_cache = baseline.Cache()
        measure("HEAD missing snapshot aggregate", old_cache.get, baseline.MidtermOut)
        # A retained file was the usual HEAD path, so include it for a fair comparison.
        snapshot = baseline.to_json(baseline.normalize(fixture, value["retrieved_at"]))
        for office in baseline.STATEWIDE:
            for race in snapshot["offices"][office]:
                race["counties"] = [c.model_dump() for c in baseline.counties(county_detail)]
        baseline.write_json(baseline.DIR / "latest.json", snapshot)
        old_file_cache = baseline.Cache()
        measure("HEAD retained snapshot aggregate", old_file_cache.get, baseline.MidtermOut)
        new_cache = midterm.Cache()
        measure("database aggregate cache", new_cache.get, midterm.MidtermOut)
        measure("database governor only", lambda: live_results.read(midterm.ELECTION_DATE, "governor"), midterm.MidtermOut)
        print(json.dumps({"fake_request_delay_ms": args.delay_ms,
            "warm_loads": args.warm_loads, "baseline_commit": subprocess.check_output(
                ["git", "rev-parse", args.baseline], cwd=ROOT, text=True).strip(),
            "synthetic_counties_per_statewide_race": 15, "results": results,
            "limitations": ["In-process loader timings, excluding HTTP, compression, browser rendering and SSE.",
                "Fixture has 20 supported races; county details are synthetic, not live election data.",
                "SQLite and OS caches are not flushed; warm timing is the median of repeated loads.",
                "Database is seeded before measurement; scheduled ingestion is not timed."]}, indent=2))
        engine.dispose()


if __name__ == "__main__":
    main()
