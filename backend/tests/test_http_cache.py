"""HTTP validators without production database access."""
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.testclient import TestClient

from backend.app.http_cache import BrowserCacheRoute


def test_cache_policy_and_conditional_responses():
    app = FastAPI()
    app.router.route_class = BrowserCacheRoute
    value = {"revision": "first", "stale": False}

    @app.get("/api/elections/az-2026-early-voting/activity")
    @app.get("/api/elections/az-2024-us-senate/counties")
    @app.get("/api/elections/az-2025-us-house-special-07")
    @app.get("/api/elections/az-2026-us-house")
    @app.get("/api/elections/az-2022-governor")
    @app.get("/api/elections/az-2022-governor/counties")
    @app.get("/api/elections/az-2014-attorney-general/activity")
    @app.get("/api/elections/az-2026-governor/activity")
    @app.get("/api/elections/az-2026-attorney-general/activity")
    @app.get("/api/elections")
    @app.get("/api/geography/county-2022")
    @app.get("/api/health")
    def data():
        return value

    @app.get("/api/missing")
    def missing():
        raise HTTPException(404)

    @app.get("/api/updates")
    def updates():
        return StreamingResponse(iter(["data: revision\n\n"]), media_type="text/event-stream")

    with TestClient(app) as client:
        for path, directive in [
            ("/api/elections/az-2026-early-voting/activity", "max-age=300"),
            ("/api/geography/county-2022", "max-age=86400"),
            ("/api/elections", "no-cache"),
            ("/api/elections/az-2024-us-senate/counties", "max-age=86400"),
            ("/api/elections/az-2025-us-house-special-07", "max-age=86400"),
            ("/api/elections/az-2026-us-house", "no-cache"),
            ("/api/elections/az-2022-governor", "max-age=86400"),
            ("/api/elections/az-2022-governor/counties", "max-age=86400"),
            ("/api/elections/az-2014-attorney-general/activity", "max-age=86400"),
            ("/api/elections/az-2026-governor/activity", "no-cache"),
            ("/api/elections/az-2026-attorney-general/activity", "no-cache"),
        ]:
            first = client.get(path)
            assert directive in first.headers["cache-control"]
            assert "private" in first.headers["cache-control"]
            tag = first.headers["etag"]
            for validator in (tag, "W/" + tag, '"other", ' + tag, "*"):
                same = client.get(path, headers={"If-None-Match": validator})
                assert same.status_code == 304
                assert same.content == b""
                assert same.headers["etag"] == tag
                assert same.headers["cache-control"] == first.headers["cache-control"]
            # Staleness changes even when the SSE revision does not.
            value["stale"] = not value["stale"]
            changed = client.get(path, headers={"If-None-Match": tag})
            assert changed.status_code == 200
            assert changed.headers["etag"] != tag
            assert changed.json() == value
        for path in ("/api/health", "/api/missing", "/api/updates"):
            response = client.get(path)
            assert response.headers["cache-control"] == "no-store, no-transform"
            assert "etag" not in response.headers
