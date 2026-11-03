"""2026 midterm results from civicAPI's race search.

One search request returns every Arizona race. A scheduled job (production/midterm_refresh_job.py,
every 30 minutes under Relay) fetches it, retains the raw response and atomically publishes a
normalized snapshot plus the legislative district boundaries under data/raw/2026/midterm. The API only
reads that snapshot. If it is missing or older than three hours the API falls back to one shared live
fetch (cached for 20 seconds), so results never disappear. Nothing is written to the database: these
are unofficial, changing figures, not a retained import. A failed reload serves the last good response
with `stale` set.
"""

import hashlib
import json
import os
import re
import threading
import time
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
        return kind(value)
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
    response = requests.get(url, timeout=TIMEOUT, allow_redirects=False, **kwargs)
    response.raise_for_status()
    return response


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
    """Fetch and normalize every race.

    `prior` is None for the live fallback, where a failed county request just omits that race map.
    The scheduled job passes the previous snapshot counties by race id instead: a failed or empty
    county response keeps the previous counties, and a failure with nothing to keep fails the run,
    so a blank county map is never published as a good snapshot.
    """
    response = response or search()
    value = normalize(response.json(), datetime.now(timezone.utc).isoformat())
    for office in STATEWIDE:
        for item in value["offices"][office]:
            if prior is None:
                item.counties = fetch_counties(item.id)
                continue
            try:
                fresh = county_results(item.id)
            except (requests.RequestException, ValueError, AttributeError):
                if not prior.get(item.id):
                    raise
                fresh = []
            item.counties = fresh or [County(**c) for c in prior.get(item.id, [])]
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
    directory = Path(directory or DIR)
    response = search()
    previous = read_snapshot(directory, now=lambda: 0) or {}  # age does not matter for reuse
    prior = {race["id"]: race.get("counties") or [] for races in previous.get("offices", {}).values() for race in races}
    value = fetch(response, prior)
    digest = hashlib.sha256(response.content).hexdigest()
    raw = directory / "raw" / f"search-{digest}.json"
    if not raw.exists():
        raw.parent.mkdir(parents=True, exist_ok=True)
        raw.write_bytes(response.content)
        for old in sorted(raw.parent.glob("search-*.json"), key=lambda p: p.stat().st_mtime)[:-KEEP_RAW]:
            old.unlink()
    value["raw_sha256"] = digest
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
    snapshot = read_snapshot(directory)
    return snapshot["revision"] if snapshot else "live"


def snapshot_stamp(directory=None):
    try:
        return (Path(directory or DIR) / "latest.json").stat().st_mtime_ns
    except OSError:
        return None


def load():
    """Prefer the scheduled job's snapshot; fetch live only when it is missing or stale."""
    return read_snapshot() or {**fetch(), "revision": "live"}


geography_cache = {}


def chamber_geography(chamber):
    if chamber not in CHAMBERS:
        raise KeyError(chamber)
    path = DIR / f"geography-{chamber}.json"
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        if chamber not in geography_cache:  # boundaries are fixed for 2026; fetch once per process
            geography_cache[chamber] = fetch_geography(chamber)
        return geography_cache[chamber]


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
        return MidtermOut(**self.value, stale=self.error is not None, refresh_error=self.error)

    def get(self):
        # With a value in hand, only one thread reloads; the others serve the last good value at once
        # instead of queueing on a slow civicAPI fetch. Only a cold start waits for the lock.
        if not self.lock.acquire(blocking=self.value is None):
            return self.output()
        try:
            # A newly published snapshot is served at once, so it always matches the revision
            # announced on the update stream.
            published = self.stamp()
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
