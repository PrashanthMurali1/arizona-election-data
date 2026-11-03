"""Midterm live-results normalization and caching, using a trimmed real civicAPI search response."""
import json
import time
from pathlib import Path

import pytest
import requests
from fastapi.testclient import TestClient

from backend.app import midterm
from backend.app.main import app

PAYLOAD = json.loads((Path(__file__).parent / "midterm_search.json").read_text())


def test_normalizes_the_six_offices_and_ignores_local_races():
    value = midterm.normalize(PAYLOAD, "2026-11-04T00:00:00+00:00")
    offices = value["offices"]
    assert set(offices) == {"governor", "attorney-general", "secretary-of-state", "us-house", "state-senate", "state-house"}
    assert [len(offices[o]) for o in ("governor", "attorney-general", "secretary-of-state")] == [1, 1, 1]
    assert [r.district for r in offices["us-house"]] == list(range(1, 10))
    # Chamber-control summary first, then districts in numeric order.
    assert [r.district for r in offices["state-senate"]] == [None, 1, 2, 3]
    assert offices["state-house"][0].seats == 60
    assert all("Mayor" not in r.name for items in offices.values() for r in items)


def test_zero_percent_before_results_and_leader_ordering():
    governor = midterm.normalize(PAYLOAD, "t")["offices"]["governor"][0]
    assert governor.total_votes == 0 and governor.called is False and governor.percent_reporting == 0
    raw = json.loads(json.dumps(PAYLOAD))
    race = next(r for r in raw["races"] if r["type"] == "Governor")
    race["candidates"][1].update(votes=500, percent=62.5)
    race["candidates"][0].update(votes=300, percent=37.5, winner=False)
    race["candidates"][1]["winner"] = True
    leader = midterm.normalize(raw, "t")["offices"]["governor"][0]
    assert leader.candidates[0].votes == 500 and leader.total_votes == 800 and leader.called is True


@pytest.mark.parametrize("payload", [{}, {"races": "x"}, {"races": []}, None])
def test_rejects_unusable_responses(payload):
    with pytest.raises(ValueError):
        midterm.normalize(payload, "t")


def test_cache_shares_one_fetch_and_serves_stale_on_failure():
    now, calls, fail = [0.0], [], [False]

    def loader():
        calls.append(1)
        if fail[0]:
            raise requests.Timeout("down")
        return midterm.normalize(PAYLOAD, "t")

    cache = midterm.Cache(loader, ttl=20, clock=lambda: now[0], stamp=lambda: None)
    assert cache.get().stale is False and cache.get().stale is False and len(calls) == 1
    now[0] = 21
    fail[0] = True
    stale = cache.get()
    assert stale.stale is True and "Timeout" in stale.refresh_error and len(calls) == 2
    fail[0] = False
    now[0] = 42
    assert cache.get().stale is False


def test_cold_failure_raises_and_endpoint_reports_503(monkeypatch):
    def down():
        raise requests.ConnectionError("no route")

    monkeypatch.setattr(midterm, "cache", midterm.Cache(down, stamp=lambda: None))
    with pytest.raises(requests.ConnectionError):
        midterm.cache.get()
    response = TestClient(app, raise_server_exceptions=False).get("/api/midterm-2026")
    assert response.status_code == 503 and response.headers["cache-control"].startswith("no-store")


def test_endpoint_serves_normalized_json_with_validators(monkeypatch):
    monkeypatch.setattr(midterm, "cache", midterm.Cache(lambda: {**midterm.normalize(PAYLOAD, "2026-11-04T00:00:00+00:00"), "revision": "abc"}, stamp=lambda: None))
    client = TestClient(app)
    response = client.get("/api/midterm-2026")
    assert response.status_code == 200 and "max-age=7200" in response.headers["cache-control"]
    assert response.json()["offices"]["governor"][0]["candidates"][0]["name"]
    assert client.get("/api/midterm-2026", headers={"if-none-match": response.headers["etag"]}).status_code == 304


def test_county_results_are_parsed_and_zero_before_counting():
    detail = {"region_results": {
        "apache": {"name": "Apache", "type": "County", "fips": "04001", "percent_reporting": 0,
                   "candidates": [{"name": "A", "party": "Republican", "votes": 0, "percent": 0}]},
        "x": {"name": "Not a county", "type": "Precinct", "fips": "9"},
    }}
    assert [(c.fips, c.total_votes) for c in midterm.counties(detail)] == [("04001", 0)]
    assert midterm.counties({}) == []


TOPOLOGY = {
    "type": "Topology",
    "transform": {"scale": [0.5, 0.5], "translate": [-115.0, 32.0]},
    # Square (0,0)-(2,0)-(2,2)-(0,2)-(0,0): arc 0 runs the first two sides; arc 1 is stored in the
    # opposite direction (0,0)-(0,2)-(2,2), so the ring uses it reversed (-2 is arc 1 reversed).
    "arcs": [[[0, 0], [2, 0], [0, 2]], [[0, 0], [0, 2], [2, 0]]],
    "objects": {"districts": {"type": "GeometryCollection", "geometries": [
        {"type": "Polygon", "arcs": [[0, -2]], "properties": {"district": "19", "id": "04019"}},
        {"type": "Polygon", "arcs": [[0, -2]], "properties": {"district": "2"}},
    ]}},
}


def test_topology_decodes_to_ordered_district_features():
    collection = midterm.decode_topology(TOPOLOGY)
    assert [f["properties"]["district"] for f in collection["features"]] == [2, 19]
    assert collection["features"][1]["properties"] == {"district": 19, "name": "District 19", "label": "19"}
    ring = collection["features"][0]["geometry"]["coordinates"][0]
    assert ring[0] == [-115.0, 32.0] and ring[1] == [-114.0, 32.0] and ring[2] == [-114.0, 33.0]
    assert ring == [[-115.0, 32.0], [-114.0, 32.0], [-114.0, 33.0], [-115.0, 33.0], [-115.0, 32.0]]  # closed


def test_refresh_publishes_snapshot_atomically_and_api_prefers_it(monkeypatch, tmp_path):
    class Response:
        content = json.dumps(PAYLOAD).encode()

        def json(self):
            return PAYLOAD

    monkeypatch.setattr(midterm, "search", lambda: Response())
    monkeypatch.setattr(midterm, "fetch_counties", lambda race_id: [])
    monkeypatch.setattr(midterm, "fetch_geography", lambda chamber: {"type": "FeatureCollection", "features": []})
    value = midterm.refresh(tmp_path)
    assert value["raw_sha256"]
    assert (tmp_path / "latest.json").exists() and not list(tmp_path.glob("*.tmp"))
    assert {p.name for p in tmp_path.glob("geography-*.json")} == {"geography-state-senate.json", "geography-state-house.json"}
    assert len(list((tmp_path / "raw").glob("search-*.json"))) == 1
    snapshot = midterm.read_snapshot(tmp_path)
    assert len(snapshot["offices"]["us-house"]) == 9
    assert midterm.MidtermOut(**snapshot, stale=False, refresh_error=None).offices["governor"][0].candidates
    # Too old: the API falls back to a live fetch instead of serving it.
    assert midterm.read_snapshot(tmp_path, now=lambda: time.time() + midterm.MAX_SNAPSHOT_AGE + 60) is None
    assert midterm.read_snapshot(tmp_path / "missing") is None


def test_failed_refresh_keeps_previous_snapshot(monkeypatch, tmp_path):
    (tmp_path / "latest.json").write_text('{"keep": true}')

    def down():
        raise requests.ConnectionError("no route")

    monkeypatch.setattr(midterm, "search", down)
    with pytest.raises(requests.ConnectionError):
        midterm.refresh(tmp_path)
    assert json.loads((tmp_path / "latest.json").read_text()) == {"keep": True}


def test_job_entry_point_reports_success_and_failure(monkeypatch, tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("midterm_job", Path(__file__).parents[2] / "production/midterm_refresh_job.py")
    job = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(job)
    monkeypatch.setattr(job, "STATUS", tmp_path / "status.json")
    monkeypatch.setattr(midterm, "refresh", lambda: {"offices": {"governor": [1]}, "raw_sha256": "abc"})
    assert job.main() == 0
    assert json.loads((tmp_path / "status.json").read_text())["status"] == "success"

    def broken():
        raise requests.Timeout("slow")

    monkeypatch.setattr(midterm, "refresh", broken)
    assert job.main() == 1
    status = json.loads((tmp_path / "status.json").read_text())
    assert status["status"] == "failed" and "Timeout" in status["error"]


def test_geography_endpoint(monkeypatch):
    monkeypatch.setattr(midterm, "chamber_geography", lambda chamber: (_ for _ in ()).throw(KeyError(chamber)) if chamber == "nope" else {"type": "FeatureCollection", "features": []})
    client = TestClient(app)
    ok = client.get("/api/midterm-2026/geography/state-house")
    assert ok.status_code == 200 and "max-age=86400" in ok.headers["cache-control"]
    assert client.get("/api/midterm-2026/geography/nope").status_code == 404


def test_snapshot_revision_tracks_content_and_falls_back_to_live(tmp_path):
    def publish(stamp):
        (tmp_path / "latest.json").write_text(json.dumps(midterm.to_json(midterm.normalize(PAYLOAD, stamp))))

    assert midterm.snapshot_revision(tmp_path) == "live"
    publish("2026-11-04T00:00:00+00:00")
    first = midterm.snapshot_revision(tmp_path)
    assert first != "live" and first == midterm.read_snapshot(tmp_path)["revision"]
    assert midterm.snapshot_revision(tmp_path) == first
    publish("2026-11-04T00:30:00+00:00")
    assert midterm.snapshot_revision(tmp_path) != first


def test_cache_serves_a_newly_published_snapshot_before_its_ttl_expires():
    stamp = ["one"]
    loads = []

    def loader():
        loads.append(stamp[0])
        return midterm.normalize(PAYLOAD, "t")

    cache = midterm.Cache(loader, ttl=3600, clock=lambda: 0.0, stamp=lambda: stamp[0])
    cache.get()
    cache.get()
    assert loads == ["one"]
    stamp[0] = "two"  # the job published a new snapshot
    cache.get()
    assert loads == ["one", "two"]


def test_update_stream_announces_the_current_revision_then_each_new_publication(monkeypatch):
    import asyncio
    from backend.app import midterm_updates

    revision = ["r1"]
    finished = [None]
    monkeypatch.setattr(midterm, "snapshot_revision", lambda directory=None: revision[0])
    monkeypatch.setattr(midterm_updates, "finished_job", lambda: finished[0])

    real_sleep = asyncio.sleep

    async def instant(_seconds):
        await real_sleep(0)

    monkeypatch.setattr(midterm_updates.asyncio, "sleep", instant)

    class Request:
        calls = 0

        async def is_disconnected(self):
            self.calls += 1
            if self.calls == 3:  # the job publishes while the page is open
                revision[0], finished[0] = "r2", "2026-11-04T00:30:00+00:00"
            return self.calls > 8

    async def collect():
        return [chunk async for chunk in midterm_updates.events(Request()) if chunk.startswith("retry")]

    chunks = asyncio.run(collect())
    assert [json.loads(c.split("data: ")[1])["revision"] for c in chunks] == ["r1", "r2"]
    assert all("event: revision" in c for c in chunks)


def test_update_stream_is_not_cached_and_status_marker_parses(tmp_path, monkeypatch):
    from backend.app import midterm_updates

    status = tmp_path / "status.json"
    monkeypatch.setattr(midterm_updates, "STATUS", status)
    assert midterm_updates.finished_job() is None
    status.write_text('{"status": "running", "started_at": "x"}')
    assert midterm_updates.finished_job() is None
    status.write_text('{"status": "success", "finished_at": "2026-11-04T00:30:00+00:00"}')
    assert midterm_updates.finished_job() == "2026-11-04T00:30:00+00:00"
    status.write_text("not json")
    assert midterm_updates.finished_job() is None


def refresh_with(monkeypatch, tmp_path, *, counties):
    class Response:
        content = json.dumps(PAYLOAD).encode()

        def json(self):
            return PAYLOAD

    monkeypatch.setattr(midterm, "search", lambda: Response())
    monkeypatch.setattr(midterm, "county_results", counties)
    monkeypatch.setattr(midterm, "fetch_geography", lambda chamber: {"type": "FeatureCollection", "features": []})
    return midterm.refresh(tmp_path)


def county(name="Apache"):
    return midterm.County(fips="04001", name=name, percent_reporting=0, total_votes=0, candidates=[])


def test_failed_county_request_keeps_previous_counties_instead_of_publishing_a_blank_map(monkeypatch, tmp_path):
    first = refresh_with(monkeypatch, tmp_path, counties=lambda race_id: [county()])
    assert all(len(r.counties) == 1 for r in first["offices"]["governor"])

    def down(race_id):
        raise requests.Timeout("slow")

    again = refresh_with(monkeypatch, tmp_path, counties=down)
    assert [c.name for c in again["offices"]["governor"][0].counties] == ["Apache"]
    # An empty (not failed) response also keeps the previous counties.
    empty = refresh_with(monkeypatch, tmp_path, counties=lambda race_id: [])
    assert len(empty["offices"]["governor"][0].counties) == 1


def test_county_failure_with_nothing_to_keep_fails_the_run_and_publishes_nothing(monkeypatch, tmp_path):
    def down(race_id):
        raise requests.Timeout("slow")

    with pytest.raises(requests.Timeout):
        refresh_with(monkeypatch, tmp_path, counties=down)
    assert not (tmp_path / "latest.json").exists()


def test_boundary_outage_never_blocks_new_results(monkeypatch, tmp_path):
    class Response:
        content = json.dumps(PAYLOAD).encode()

        def json(self):
            return PAYLOAD

    def down(chamber):
        raise requests.ConnectionError("static path down")

    monkeypatch.setattr(midterm, "search", lambda: Response())
    monkeypatch.setattr(midterm, "county_results", lambda race_id: [county()])
    monkeypatch.setattr(midterm, "fetch_geography", down)
    midterm.refresh(tmp_path)
    assert (tmp_path / "latest.json").exists() and not list(tmp_path.glob("geography-*.json"))
    # Once fetched, boundaries are not downloaded again.
    monkeypatch.setattr(midterm, "fetch_geography", lambda chamber: {"type": "FeatureCollection", "features": []})
    midterm.refresh(tmp_path)
    monkeypatch.setattr(midterm, "fetch_geography", down)
    midterm.refresh(tmp_path)
    assert len(list(tmp_path.glob("geography-*.json"))) == 2


def test_truncated_search_result_is_rejected():
    with pytest.raises(ValueError, match="truncated"):
        midterm.normalize({**PAYLOAD, "count": len(PAYLOAD["races"]) + 1}, "t")


def test_unusable_snapshot_file_falls_back_to_live(monkeypatch, tmp_path):
    (tmp_path / "latest.json").write_text('{"offices": "nope"}')
    assert midterm.read_snapshot(tmp_path) is None
    (tmp_path / "latest.json").write_text("{truncated")
    assert midterm.read_snapshot(tmp_path) is None
    monkeypatch.setattr(midterm, "DIR", tmp_path)
    monkeypatch.setattr(midterm, "fetch", lambda: midterm.normalize(PAYLOAD, "t"))
    value = midterm.load()
    assert value["revision"] == "live" and value["offices"]["us-house"]


def test_live_and_stale_responses_are_not_cacheable_for_two_hours(monkeypatch):
    live = {**midterm.normalize(PAYLOAD, "t"), "revision": "live"}
    monkeypatch.setattr(midterm, "cache", midterm.Cache(lambda: live, stamp=lambda: None))
    response = TestClient(app).get("/api/midterm-2026")
    assert response.status_code == 200 and "no-cache" in response.headers["cache-control"]
    assert "x-cache-policy" not in response.headers
    fresh = {**live, "revision": "abc123"}
    monkeypatch.setattr(midterm, "cache", midterm.Cache(lambda: fresh, stamp=lambda: None))
    assert "max-age=7200" in TestClient(app).get("/api/midterm-2026").headers["cache-control"]


def test_geography_endpoint_distinguishes_unknown_chamber_from_a_bad_boundary_file(monkeypatch):
    client = TestClient(app, raise_server_exceptions=False)
    assert client.get("/api/midterm-2026/geography/nope").status_code == 404

    def malformed(chamber):
        raise KeyError("transform")

    monkeypatch.setattr(midterm, "chamber_geography", malformed)
    assert client.get("/api/midterm-2026/geography/state-house").status_code == 503


def test_other_requests_are_served_the_last_value_while_one_thread_reloads():
    import threading

    started, release = threading.Event(), threading.Event()
    calls = []

    def loader():
        calls.append(1)
        if len(calls) > 1:
            started.set()
            release.wait(5)
        return midterm.normalize(PAYLOAD, "t")

    now = [0.0]
    cache = midterm.Cache(loader, ttl=20, clock=lambda: now[0], stamp=lambda: None)
    cache.get()
    now[0] = 100  # due for a reload
    reloader = threading.Thread(target=cache.get)
    reloader.start()
    assert started.wait(5)
    waiting = cache.get()  # returns at once with the last good value instead of queueing
    assert waiting.offices["governor"] and len(calls) == 2
    release.set()
    reloader.join(5)
