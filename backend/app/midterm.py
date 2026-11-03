"""Scheduled civicAPI ingestion and database-only results serving.

Unofficial snapshots live separately from certified historical tables. HTTP requests never fetch
upstream; overdue snapshots remain visible and carry an explicit stale marker.
"""

import hashlib
import json
import math
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import requests
from pydantic import BaseModel

SEARCH_URL = "https://civicapi.org/api/v2/race/search"
ELECTION_DATE = "2026-11-03"
TTL_SECONDS = 20  # how long the API process reuses what it loaded (snapshot file or live fetch)
TIMEOUT = (5, 25)

# civicAPI race `type` -> our office id. Local races (clerks, councils, ...) are ignored.
OFFICES = {
    "Governor": "governor",
    "Attorney General": "attorney-general",
    "Secretary of State": "secretary-of-state",
    "House of Representatives": "us-house",
    "State Senate": "state-senate",
    "State House": "state-house",
}
DISTRICT = re.compile(r"^AZ-(?:SD-|HD-)?(\d{1,3})$")


class Candidate(BaseModel):
    name: str
    party: str | None
    color: str | None
    votes: int | None
    percent: float | None
    winner: bool
    seats: int | None = None


class County(BaseModel):
    fips: str
    name: str
    percent_reporting: float | None
    total_votes: int
    candidates: list[Candidate]


class Race(BaseModel):
    id: int
    name: str
    district: int | None
    percent_reporting: float | None
    total_votes: int
    called: bool
    source_url: str
    seats: int | None = None
    candidates: list[Candidate]
    counties: list[County] = []
    retrieved_at: str | None = None
    status: str = "unofficial"
    results_state: str = "unreported"
    source_updated_at: str | None = None
    attempted_at: str | None = None
    refresh_error: str | None = None


class MidtermOut(BaseModel):
    election_date: str
    source_url: str
    retrieved_at: str
    stale: bool
    refresh_error: str | None
    raw_sha256: str | None = None
    # Identifies the published snapshot; the update stream announces it so browsers can refetch.
    revision: str = "live"
    offices: dict[str, list[Race]]


def number(value, kind):
    if value is None or isinstance(value, bool):
        return None
    try:
        result = kind(value)
        return result if math.isfinite(result) and result >= 0 else None
    except (TypeError, ValueError):
        return None


def candidate(raw):
    return Candidate(
        name=str(raw.get("name") or "Unknown"), party=raw.get("party"), color=raw.get("color"),
        votes=number(raw.get("votes"), int), percent=number(raw.get("percent"), float),
        winner=raw.get("winner") is True, seats=number(raw.get("seats"), int),
    )


def race(raw, office):
    district = None
    if office in {"us-house", "state-senate", "state-house"} and raw.get("district"):
        match = DISTRICT.match(str(raw["district"]))
        if not match:
            return None
        district = int(match[1])
    candidates = [candidate(c) for c in raw.get("candidates") or []]
    # Stable sort: leaders first; ties (all zero before counting) keep civicAPI's order.
    candidates.sort(key=lambda c: -(c.votes or 0))
    return Race(
        id=raw["id"], name=str(raw.get("election_name") or ""), district=district,
        percent_reporting=number(raw.get("percent_reporting"), float),
        total_votes=sum(c.votes or 0 for c in candidates), called=any(c.winner for c in candidates),
        source_url=f"https://civicapi.org/api/v2/race/{raw['id']}",
        seats=number(raw.get("seats"), int), candidates=candidates,
        results_state="partial" if any(c.votes is None for c in candidates) else
            ("reported" if any((c.votes or 0) > 0 for c in candidates) else "unreported"),
    )


def counties(detail):
    """County results from a race detail response; empty when the race has none."""
    out = []
    for raw in (detail.get("region_results") or {}).values():
        if raw.get("type") != "County" or not raw.get("fips"):
            continue
        cands = [candidate(c) for c in raw.get("candidates") or []]
        cands.sort(key=lambda c: -(c.votes or 0))
        out.append(County(
            fips=str(raw["fips"]), name=str(raw.get("name") or ""),
            percent_reporting=number(raw.get("percent_reporting"), float),
            total_votes=sum(c.votes or 0 for c in cands), candidates=cands,
        ))
    return sorted(out, key=lambda c: c.fips)


def normalize(payload, retrieved_at):
    races = payload.get("races") if isinstance(payload, dict) else None
    if not isinstance(races, list):
        raise ValueError("civicAPI response has no race list")
    if isinstance(payload.get("count"), int) and payload["count"] > len(races):
        raise ValueError("civicAPI search result was truncated; raise the request limit")
    offices = {office: [] for office in OFFICES.values()}
    for raw in races:
        office = OFFICES.get(raw.get("type"))
        # Legislative districts are typed "Local" by civicAPI, so filter on type and district, not scope.
        if office is None or raw.get("province") != "AZ":
            continue
        item = race(raw, office)
        if item:
            offices[office].append(item)
    for office, items in offices.items():
        # Chamber-control summaries (no district) first, then districts in numeric order.
        items.sort(key=lambda r: (r.district is not None, r.district or 0))
    if not any(offices.values()):
        raise ValueError("civicAPI response contains no Arizona midterm races")
    return {
        "election_date": ELECTION_DATE, "retrieved_at": retrieved_at, "offices": offices,
        "source_url": f"{SEARCH_URL}?startDate={ELECTION_DATE}&endDate={ELECTION_DATE}&country=US&province=AZ",
    }


STATEWIDE = ("governor", "attorney-general", "secretary-of-state")
CHAMBERS = {
    "state-senate": "https://civicapi.org/data/geojson/state_leg/AZ_sldu_2026.json",
    "state-house": "https://civicapi.org/data/geojson/state_leg/AZ_sldl_2026.json",
}
ROOT = Path(__file__).resolve().parents[2]
DIR = ROOT / "data/raw/2026/midterm"
MAX_SNAPSHOT_AGE = 3 * 3600  # the job runs every 30 minutes; fall back to a live fetch beyond this
KEEP_RAW = 200


def get(url, **kwargs):
    # At most two attempts, including bounded Retry-After on throttling. No request-path callers.
    for attempt in range(2):
        try:
            response = requests.get(url, timeout=TIMEOUT, allow_redirects=False, **kwargs)
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if attempt or (status is not None and status != 429 and status < 500):
                raise
            delay = 1
            try:
                delay = min(30, max(1, int(exc.response.headers.get("Retry-After", "1"))))
            except (AttributeError, ValueError):
                pass
            time.sleep(delay)


def county_results(race_id):
    return counties(get(f"https://civicapi.org/api/v2/race/{race_id}").json())


def fetch_counties(race_id):
    try:
        return county_results(race_id)
    except (requests.RequestException, ValueError, AttributeError):
        return []  # Live fallback: the statewide figures still display without the county map.


def search():
    return get(SEARCH_URL, params={
        "startDate": ELECTION_DATE, "endDate": ELECTION_DATE, "country": "US", "province": "AZ", "limit": 500,
    })


def fetch(response=None, prior=None):
    """Scheduled fetch; a failed county detail retains the entire previous race."""
    response = response or search()
    value = normalize(response.json(), datetime.now(timezone.utc).isoformat())
    # Completed races need only a two-hour check. A called race is not necessarily complete.
    from .live_results import COMPLETED_SECONDS
    skipped = set()
    for office, items in value["offices"].items():
        for index, item in enumerate(items):
            previous = (prior or {}).get(item.id)
            if not isinstance(previous, dict):
                continue
            stamp = previous.get("retrieved_at")
            recent = False
            if stamp:
                recent = (datetime.now(timezone.utc) - datetime.fromisoformat(stamp)).total_seconds() < COMPLETED_SECONDS
            if previous.get("status") == "certified" or (previous.get("percent_reporting") == 100 and recent):
                items[index] = Race(**previous)
                skipped.add(item.id)
    def complete(item):
        if item.id in skipped:
            return item
        try:
            fresh = county_results(item.id)
            if not fresh:
                if not (prior or {}).get(item.id) and item.results_state == "unreported":
                    return item
                raise ValueError("County results missing")
            item.counties = fresh
            return item
        except (requests.RequestException, ValueError, AttributeError) as exc:
            previous = (prior or {}).get(item.id)
            # Keep the entire previous race, never attach old counties to new statewide totals.
            error = f"{type(exc).__name__}: {exc}"
            if isinstance(previous, dict):
                return Race(**{**previous, "refresh_error": error})
            # A new race still publishes its statewide totals; the other races must not wait on it.
            item.refresh_error = error
            return item
    with ThreadPoolExecutor(max_workers=3) as executor:
        targets = [(office, item) for office in STATEWIDE for item in value["offices"][office]]
        results = list(executor.map(complete, [item for _, item in targets]))
        for office in STATEWIDE:
            value["offices"][office] = [result for (name, _), result in zip(targets, results) if name == office]
    return value


def decode_topology(topology):
    """Convert civicAPI's quantized TopoJSON district file to a GeoJSON FeatureCollection."""
    sx, sy = topology["transform"]["scale"]
    tx, ty = topology["transform"]["translate"]
    arcs = []
    for arc in topology["arcs"]:
        x = y = 0
        points = []
        for dx, dy in arc:
            x, y = x + dx, y + dy
            points.append([round(x * sx + tx, 6), round(y * sy + ty, 6)])
        arcs.append(points)

    def ring(indexes):
        points = []
        for index in indexes:
            part = arcs[~index][::-1] if index < 0 else arcs[index]
            points.extend(part if not points else part[1:])
        return points

    features = []
    for geometry in next(iter(topology["objects"].values()))["geometries"]:
        properties = geometry.get("properties") or {}
        if geometry["type"] == "Polygon":
            coordinates = [ring(r) for r in geometry["arcs"]]
        elif geometry["type"] == "MultiPolygon":
            coordinates = [[ring(r) for r in polygon] for polygon in geometry["arcs"]]
        else:
            continue
        district = int(properties["district"])
        features.append({
            "type": "Feature",
            "properties": {"district": district, "name": f"District {district}", "label": str(district)},
            "geometry": {"type": geometry["type"], "coordinates": coordinates},
        })
    features.sort(key=lambda f: f["properties"]["district"])
    return {"type": "FeatureCollection", "features": features}


def fetch_geography(chamber):
    return decode_topology(get(CHAMBERS[chamber]).json())


def to_json(value):
    """JSON-ready snapshot (pydantic races become plain dicts)."""
    return {**value, "offices": {k: [r.model_dump() if hasattr(r, "model_dump") else r for r in v] for k, v in value["offices"].items()}}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, separators=(",", ":")))
    os.replace(temporary, path)  # readers see the old or the new file, never a partial one


def refresh(directory=None):
    """Scheduled job: fetch everything, retain the raw search response, then publish atomically."""
    persistent = directory is None
    directory = Path(directory or DIR)
    response = search()
    previous = read_snapshot(directory, now=lambda: 0) or {}  # age does not matter for reuse
    if persistent:
        from . import live_results
        try:
            previous = live_results.read(ELECTION_DATE)
        except ValueError:
            pass
    prior = {race["id"]: race for races in previous.get("offices", {}).values() for race in races}
    value = fetch(response, prior)
    digest = hashlib.sha256(response.content).hexdigest()
    raw = directory / "raw" / f"search-{digest}.json"
    if not raw.exists():
        raw.parent.mkdir(parents=True, exist_ok=True)
        raw.write_bytes(response.content)
        for old in sorted(raw.parent.glob("search-*.json"), key=lambda p: p.stat().st_mtime)[:-KEEP_RAW]:
            old.unlink()
    value["raw_sha256"] = digest
    # The transaction is the publication boundary. The file is only an operator/raw compatibility
    # artifact; serving and SSE revision checks use SQLite.
    if persistent:
        live_results.publish(to_json(value))
    # Results first: district boundaries are fixed for 2026, so they are fetched only when missing and
    # an outage of that static path can never hold back new vote counts (the API fetches them itself).
    write_json(directory / "latest.json", to_json(value))
    for chamber in CHAMBERS:
        target = directory / f"geography-{chamber}.json"
        if not target.exists():
            try:
                write_json(target, fetch_geography(chamber))
            except (requests.RequestException, ValueError, KeyError, TypeError):
                pass
    return value


def read_snapshot(directory=None, now=time.time):
    path = Path(directory or DIR) / "latest.json"
    try:
        if now() - path.stat().st_mtime > MAX_SNAPSHOT_AGE:
            return None
        text = path.read_text()
        data = {**json.loads(text), "revision": hashlib.sha256(text.encode()).hexdigest()[:16]}
        # A truncated or outdated file must fall back to a live fetch, not break the endpoint.
        MidtermOut(**{**data, "stale": False, "refresh_error": None})
        return data
    except (OSError, ValueError, TypeError):
        return None


def snapshot_revision(directory=None):
    """The revision /api/midterm-2026 currently serves ("live" when it is not using a snapshot)."""
    if directory is None:
        from . import live_results
        try:
            return live_results.revision(ELECTION_DATE)
        except ValueError:
            return "unavailable"
    snapshot = read_snapshot(directory)
    return snapshot["revision"] if snapshot else "live"


def snapshot_stamp(directory=None):
    if directory is None:
        return snapshot_revision()
    try:
        return (Path(directory or DIR) / "latest.json").stat().st_mtime_ns
    except OSError:
        return None


def load():
    """Database only, including across process restarts and upstream outages."""
    from . import live_results
    return live_results.read(ELECTION_DATE)


geography_cache = {}


def chamber_geography(chamber):
    if chamber not in CHAMBERS:
        raise KeyError(chamber)
    path = DIR / f"geography-{chamber}.json"
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        raise ValueError("Scheduled district boundaries are unavailable")


class Cache:
    """Single-flight TTL cache that falls back to the last good response."""

    def __init__(self, loader=load, ttl=TTL_SECONDS, clock=time.monotonic, stamp=snapshot_stamp):
        self.loader, self.ttl, self.clock, self.stamp = loader, ttl, clock, stamp
        self.lock = threading.Lock()
        self.value = None
        self.loaded_at = None
        self.loaded_stamp = None
        self.error = None

    def output(self):
        return MidtermOut(**{**self.value, "stale": bool(self.error or self.value.get("stale")),
            "refresh_error": self.error or self.value.get("refresh_error")})

    def get(self):
        # With a value in hand, only one thread reloads; the others serve the last good value at once
        # instead of queueing on a slow civicAPI fetch. Only a cold start waits for the lock.
        if not self.lock.acquire(blocking=self.value is None):
            return self.output()
        try:
            # A newly published snapshot is served at once, so it always matches the revision
            # announced on the update stream.
            try:
                published = self.stamp()
            except Exception as exc:
                if self.value is None:
                    raise
                self.error = f"{type(exc).__name__}: {exc}"
                return self.output()
            if self.value is None or published != self.loaded_stamp or self.clock() - self.loaded_at >= self.ttl:
                self.loaded_stamp = published
                try:
                    self.value, self.error = self.loader(), None
                except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
                    self.error = f"{type(exc).__name__}: {exc}"
                    if self.value is None:
                        raise
                self.loaded_at = self.clock()
            return self.output()
        finally:
            self.lock.release()


cache = Cache()
