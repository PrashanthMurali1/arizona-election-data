"""Browser caching for serialized API responses; no server-side response store."""
from hashlib import sha256

from fastapi import HTTPException, Request, Response
from fastapi.routing import APIRoute


class BrowserCacheRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def cached(request: Request):
            try:
                response = await handler(request)
            except HTTPException as exc:
                exc.headers = {**(exc.headers or {}), "Cache-Control": "no-store, no-transform"}
                raise
            # Never buffer streaming responses or cache health/error responses.
            if (request.method != "GET" or response.status_code != 200
                    or not response.headers.get("content-type", "").startswith("application/json")
                    or request.url.path == "/api/health"):
                response.headers["Cache-Control"] = "no-store, no-transform"
                return response

            path = request.url.path
            if path.startswith("/api/geography/"):
                policy = "private, max-age=86400, must-revalidate, no-transform"
            elif path == "/api/elections/az-2026-early-voting/activity":
                policy = "private, max-age=300, must-revalidate, no-transform"
            else:
                policy = "private, no-cache, no-transform"
            # Hash the actual representation, including time-dependent stale flags.
            # The SSE revision intentionally omits those flags and is not an ETag.
            etag = '"' + sha256(response.body).hexdigest() + '"'
            response.headers["Cache-Control"] = policy
            response.headers["ETag"] = etag
            validators = request.headers.get("if-none-match", "")
            if any(tag.strip().removeprefix("W/") in (etag, "*")
                   for tag in validators.split(",")):
                return Response(status_code=304, headers={
                    "Cache-Control": policy, "ETag": etag,
                })
            return response

        return cached
