"""Latest unofficial civicAPI race snapshots, isolated from certified historical imports.

Each JSON payload contains the complete race (including its counties) and is replaced in one
transaction. Only the scheduled refresh writes here; HTTP requests never contact civicAPI.
"""
import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy import select
from .database import SessionLocal
from .models import LiveRaceSnapshot

ACTIVE_SECONDS = 5 * 60
COMPLETED_SECONDS = 2 * 60 * 60
# Per-run metadata lives in columns; keeping it out of the payload keeps the digest, and so the
# published revision, stable while the votes are unchanged.
RUN_FIELDS = ("retrieved_at", "status", "attempted_at", "refresh_error")


def revision(election_date, session_factory=None):
    session_factory = session_factory or SessionLocal
    with session_factory() as session:
        rows = session.execute(select(LiveRaceSnapshot.id, LiveRaceSnapshot.revision,
            LiveRaceSnapshot.refresh_error).where(LiveRaceSnapshot.election_date == election_date)
            .order_by(LiveRaceSnapshot.race_id)).all()
        return hashlib.sha256("|".join(f"{r.id}:{r.revision}:{r.refresh_error or ''}" for r in rows).encode()).hexdigest()[:16] if rows else "unavailable"


def publish(value, session_factory=None):
    session_factory = session_factory or SessionLocal
    with session_factory.begin() as session:
        for office, races in value["offices"].items():
            for race in races:
                payload = race.model_dump() if hasattr(race, "model_dump") else race
                key = f"{value['election_date']}:{payload['id']}"
                row = session.get(LiveRaceSnapshot, key)
                if row and row.certified:
                    continue
                # Rejected attempts have separate metadata; successful results stay intact.
                if not payload.get("candidates"):
                    if row:
                        row.attempted_at = value["retrieved_at"]
                        row.refresh_error = "Empty candidate snapshot retained"
                    continue
                if row:
                    row.attempted_at = value["retrieved_at"]
                    row.refresh_error = payload.get("refresh_error")
                fresh = {c["name"]: c.get("votes") for c in payload["candidates"]}
                # Only a known count turning missing is a regression; a candidate that is still null,
                # was withdrawn or was renamed must not freeze the race.
                known = [c for c in row.payload["candidates"] if c.get("votes") is not None] if row else []
                if known and (not any(c["name"] in fresh for c in known)
                              or any(fresh.get(c["name"], 0) is None for c in known)):
                    row.refresh_error = "Incomplete candidate snapshot retained"
                    continue
                refresh_error = payload.get("refresh_error")
                retrieved_at = payload.get("retrieved_at") or value["retrieved_at"]
                payload = {k: v for k, v in payload.items() if k not in RUN_FIELDS}
                digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
                if row is None:
                    row = LiveRaceSnapshot(id=key, election_date=value["election_date"],
                        race_id=payload["id"], office=office, certified=False)
                    session.add(row)
                if row.revision != digest:
                    row.payload, row.revision = payload, digest
                row.retrieved_at = retrieved_at
                row.source_url = payload["source_url"]
                row.raw_sha256 = value.get("raw_sha256")
                row.completed = payload.get("percent_reporting") == 100
                row.attempted_at = value["retrieved_at"]
                row.refresh_error = refresh_error


def read(election_date, office=None, session_factory=None):
    session_factory = session_factory or SessionLocal
    with session_factory() as session:
        query = select(LiveRaceSnapshot).where(LiveRaceSnapshot.election_date == election_date)
        if office:
            query = query.where(LiveRaceSnapshot.office == office)
        rows = session.scalars(query.order_by(LiveRaceSnapshot.race_id)).all()
        if not rows:
            raise ValueError("No scheduled midterm snapshot is available; run the refresh job")
        offices = {}
        now = datetime.now(timezone.utc)
        stale = False
        for row in rows:
            payload = dict(row.payload)
            payload["retrieved_at"] = row.retrieved_at
            payload["status"] = "certified" if row.certified else "unofficial"
            payload["attempted_at"] = row.attempted_at
            payload["refresh_error"] = row.refresh_error
            offices.setdefault(row.office, []).append(payload)
            age = (now - datetime.fromisoformat(row.retrieved_at)).total_seconds()
            stale |= not row.certified and (bool(row.refresh_error) or age > (COMPLETED_SECONDS if row.completed else ACTIVE_SECONDS) * 3)
        for races in offices.values():
            races.sort(key=lambda r: (r.get("district") is not None, r.get("district") or 0))
        version = revision(election_date, session_factory)
        return dict(election_date=election_date, source_url="https://civicapi.org/",
            retrieved_at=min(r.retrieved_at for r in rows), raw_sha256=None,
            revision=version, offices=offices, stale=stale,
            refresh_error="Scheduled results are overdue" if stale else None)
