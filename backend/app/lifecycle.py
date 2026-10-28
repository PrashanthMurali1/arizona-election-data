"""Explicit, audited refreshes for the current general election; historical reads stay unchanged."""

import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlparse
from sqlalchemy import select, delete
from sqlalchemy.orm import Session
from .database import ROOT
from .models import (
    Office,
    ElectionEvent,
    Contest,
    Source,
    GeographicUnit,
    BoundaryVersion,
    ElectionPublication,
    PublicationSnapshot,
    CurrentSnapshot,
    MetricObservation,
    RefreshAttempt,
    Candidate,
    Party,
    Participation,
    VoteResult,
)
from .publication_input import SnapshotInput

EVENT = "az-2026-general"
CONTEST = "az-2026-governor"
AG_CONTEST = "az-2026-attorney-general"
RELEASE_AFTER = datetime(
    2026, 11, 4, 3, tzinfo=timezone.utc
)  # Nov 3, 8pm America/Phoenix
METRICS = {
    "registered_voters": "Active registered voters",
    "ballots_requested": "Ballots requested",
    "ballots_mailed": "Ballots mailed",
    "ballots_issued": "Ballots sent / issued",
    "ballots_verified_ready": "Verified, ready for turnover",
    "ballots_turned_over": "Turned over to Elections",
    "ballots_received": "Early returns in hand / received",
    "ballots_accepted": "Ballots accepted",
    "in_person_early": "In-person early participation",
}


def utcnow():
    return datetime.now(timezone.utc)


def instant(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def local_file(path, root=ROOT):
    result = (root / path).resolve()
    if not result.is_relative_to((root / "data/raw").resolve()) or not result.is_file():
        raise ValueError("Source files must exist inside data/raw")
    return result


def check_source(source, root=ROOT, provider=None):
    host = urlparse(source.url).hostname or ""
    provider_hosts = {
        "civicAPI": {"civicapi.org", "www.civicapi.org"},
        "Decision Labs": {"decisionlabs.ai", "www.decisionlabs.ai"},
    }
    if provider:
        if urlparse(source.url).scheme != "https" or host not in provider_hosts.get(provider, set()):
            raise ValueError("Provider report URL must belong to the selected provider")
        raw = local_file(source.raw_path, root).read_bytes()
        if hashlib.sha256(raw).hexdigest() != source.sha256:
            raise ValueError("Raw provider snapshot checksum does not match")
        return raw
    if urlparse(source.url).scheme != "https" or not (
        host.endswith(".gov")
        or host == "results.arizona.vote"
        or (host == "services.arcgis.com" and "/ykpntM6e3tHvzKRJ/" in source.url)
    ):
        raise ValueError(
            "Current-election inputs require an identified official public source"
        )
    raw = local_file(source.raw_path, root).read_bytes()
    if hashlib.sha256(raw).hexdigest() != source.sha256:
        raise ValueError("Raw source checksum does not match the reviewed input")
    return raw


def ensure_current(s):
    if not s.get(BoundaryVersion, "county-2022"):
        raise ValueError(
            "Run the documented migrations and historical bootstrap first to load county geography"
        )
    if not s.get(Contest, CONTEST):
        s.add(
            Source(
                id="2026-availability",
                title="Arizona Secretary of State — 2026 general election",
                url="https://azsos.gov/elections/election-information/2026-election-info",
                sha256="",
                notes="General election November 3, 2026. Candidate results are not released before election night.",
            )
        )
        s.merge(Office(id="governor", name="Governor"))
        s.add(ElectionEvent(id=EVENT, year=2026, date="2026-11-03", kind="general"))
        s.flush()
        s.add(
            Contest(
                id=CONTEST,
                event_id=EVENT,
                office_id="governor",
                jurisdiction_id="04",
                boundary_id="county-2022",
                source_id="2026-availability",
                status="pre_results",
                notes="Voting in progress — candidate results not yet released. Participation figures concern the general election, not governor votes.",
            )
        )
        s.flush()
    if not s.get(Contest, AG_CONTEST):
        s.merge(Office(id="attorney-general", name="Attorney General"))
        s.add(
            Contest(
                id=AG_CONTEST,
                event_id=EVENT,
                office_id="attorney-general",
                jurisdiction_id="04",
                boundary_id="county-2022",
                source_id="2026-availability",
                status="pre_results",
                notes="Voting in progress — candidate results not yet released. Participation figures concern the general election, not votes cast specifically for Attorney General.",
            )
        )
        s.flush()
    if not s.get(ElectionPublication, AG_CONTEST):
        s.add(
            ElectionPublication(
                contest_id=AG_CONTEST,
                stage="pre_results",
                completeness="unavailable",
                verification="source_checked",
                result_snapshot_id=None,
                notes="General-election participation and candidate results are separate.",
            )
        )
        s.flush()
    if not s.get(ElectionPublication, CONTEST):
        s.add(
            ElectionPublication(
                contest_id=CONTEST,
                stage="pre_results",
                completeness="unavailable",
                verification="source_checked",
                result_snapshot_id=None,
                notes="General-election participation and candidate results are separate.",
            )
        )
        s.flush()


def record_failure(s, stream, error, now=None):
    ensure_current(s)
    s.add(
        RefreshAttempt(
            event_id=EVENT,
            stream=stream,
            attempted_at=(now or utcnow()).isoformat(),
            success=False,
            error=str(error),
            snapshot_id=None,
        )
    )


def apply_snapshot(s: Session, data: SnapshotInput, *, root=ROOT, now=None):
    now = now or utcnow()
    provider = data.provider_report or data.provider_participation
    check_source(data.source, root, provider=provider.provider if provider else None)
    if instant(data.retrieved_at) > now + timedelta(minutes=5):
        raise ValueError("Retrieval time is in the future")
    if data.report_precision == "datetime" and instant(
        data.reported_at
    ) > now + timedelta(minutes=5):
        raise ValueError("Source reporting time is in the future")
    if (
        data.report_precision == "date"
        and data.reported_at
        > now.astimezone(__import__("zoneinfo").ZoneInfo("America/Phoenix"))
        .date()
        .isoformat()
    ):
        raise ValueError("Source publication date is in the future")
    ensure_current(s)
    target_contest = {
        "attorney-general": AG_CONTEST,
    }.get(data.office_id, CONTEST)
    units = set(
        s.scalars(select(GeographicUnit.id).where(GeographicUnit.kind == "county"))
    ) | {"04"}
    seen = set()
    for m in data.metrics:
        if m.geoid not in units or (m.geoid, m.key) in seen:
            raise ValueError("Unknown geographic identifier or duplicate metric")
        seen.add((m.geoid, m.key))
        if (m.value is None) != (m.completeness == "unavailable"):
            raise ValueError(
                "Missing metrics require unavailable status; a genuine zero remains a value"
            )
    if data.kind == "results":
        if not data.provider_report and now < RELEASE_AFTER:
            raise ValueError(
                "General-election candidate results have not reached the official release time"
            )
        if (
            not data.provider_report
            and data.report_precision == "datetime"
            and instant(data.reported_at) < RELEASE_AFTER
        ):
            raise ValueError("Result timestamp predates general-election release")
        if not data.candidates:
            raise ValueError(
                "A result release must identify the source candidate roster"
            )
        keys = {c.key for c in data.candidates}
        if len(keys) != len(data.candidates):
            raise ValueError("Duplicate candidate key")
        seen = set()
        for v in data.votes:
            if (
                v.geoid not in units
                or v.candidate not in keys
                or (v.geoid, v.candidate) in seen
            ):
                raise ValueError("Unknown unit/candidate or duplicate result cell")
            seen.add((v.geoid, v.candidate))
        if not set(data.complete_units) <= units:
            raise ValueError("Unknown complete reporting unit")
        for unit in data.complete_units:
            if any(
                not any(
                    v.geoid == unit and v.candidate == key and v.votes is not None
                    for v in data.votes
                )
                for key in keys
            ):
                raise ValueError("A complete unit must have every candidate value")
    payload = data.model_dump()
    identity = data.model_dump(exclude={"retrieved_at"})
    if data.provider_report is None:
        identity.pop("provider_report", None)
    if data.provider_participation is None:
        identity.pop("provider_participation", None)
    # Keep IDs stable for reviewed manifests created before office_id existed.
    if "office_id" not in data.model_fields_set:
        identity.pop("office_id", None)
    identity["source"].pop("raw_path")
    if identity.get("certification"):
        identity["certification"].pop("raw_path")
    sid = hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    cursor = s.get(CurrentSnapshot, (EVENT, data.stream))
    previous = s.get(PublicationSnapshot, cursor.snapshot_id) if cursor else None
    warnings = list(data.source_warnings)
    if (
        data.kind == "results"
        and not data.provider_report
        and data.roster_complete
        and units <= set(data.complete_units)
    ):
        cells = {(v.geoid, v.candidate): v.votes for v in data.votes}
        for candidate in data.candidates:
            county_sum = sum(cells[(unit, candidate.key)] for unit in units - {"04"})
            state_value = cells[("04", candidate.key)]
            if county_sum != state_value:
                warnings.append(
                    f"{candidate.name}: county sum {county_sum} differs from published statewide {state_value}; source figures retained without adjustment."
                )
    if previous and not data.provider_participation:
        if data.kind == "participation":
            old = {(m["geoid"], m["key"]): m for m in previous.payload["metrics"]}
            for m in data.metrics:
                prior = old.get((m.geoid, m.key))
                if (
                    prior
                    and prior["value"] is not None
                    and m.value is not None
                    and m.value < prior["value"]
                ):
                    warnings.append(
                        f"{m.geoid} {m.key} decreased from {prior['value']} to {m.value}; official correction retained for review."
                    )
                if prior and prior["definition"] != m.definition:
                    warnings.append(
                        f"{m.geoid} {m.key}: source definition changed; compare releases carefully."
                    )
        else:
            old = {
                (v["geoid"], v["candidate"]): v["votes"]
                for v in previous.payload["votes"]
            }
            for v in data.votes:
                prior = old.get((v.geoid, v.candidate))
                if prior is not None and v.votes is not None and v.votes < prior:
                    warnings.append(
                        f"{v.geoid} {v.candidate} corrected downward: {prior} to {v.votes}."
                    )
    publication = s.get(ElectionPublication, target_contest)
    if (
        data.kind == "results"
        and publication.stage == "certified"
        and data.stage != "certified"
    ):
        raise ValueError("An unofficial release cannot replace a certified result")
    reconciliation = None
    if data.stage == "certified":
        check_source(data.certification, root)
        if not data.roster_complete or set(data.complete_units) != units:
            raise ValueError(
                "Certification requires all 15 counties and statewide results"
            )
        from scripts.import_data import reconcile

        reference = local_file(data.reference_path, root)
        values = {(v.geoid, v.candidate): v.votes for v in data.votes}
        normalized = dict(
            year=2026,
            source_url=data.certification.url,
            candidates=[
                dict(
                    id=c.key,
                    name=c.name,
                    party=c.party,
                    write_in=c.write_in,
                    county_votes={u: values.get((u, c.key)) for u in units - {"04"}},
                    statewide=values.get(("04", c.key)),
                )
                for c in data.candidates
            ],
        )
        reconciliation = reconcile(normalized, reference_path=reference)
        if reconciliation["status"] != "verified":
            raise ValueError(
                "Certified release does not reconcile: " + json.dumps(reconciliation)
            )
    existing = s.get(PublicationSnapshot, sid)
    if not existing:
        source_id = "snapshot-" + sid
        s.add(Source(id=source_id, **data.source.model_dump(exclude={"raw_path"})))
        s.flush()
        s.add(
            PublicationSnapshot(
                id=sid,
                event_id=EVENT,
                contest_id=target_contest,
                stream=data.stream,
                kind=data.kind,
                stage=data.stage,
                completeness=data.completeness,
                verification=data.verification,
                source_id=source_id,
                reported_at=data.reported_at,
                report_precision=data.report_precision,
                retrieved_at=data.retrieved_at,
                release_id=data.release_id,
                vote_scope=data.vote_scope,
                payload=payload,
                warnings=warnings,
            )
        )
        s.flush()
        for m in data.metrics:
            s.add(
                MetricObservation(
                    snapshot_id=sid, unit_id=m.geoid, **m.model_dump(exclude={"geoid"})
                )
            )
    # Keep older releases for audit without moving the current pointer backward.
    advance = (
        not previous
        or not previous.reported_at
        or not data.reported_at
        or data.reported_at >= previous.reported_at
    )
    if provider:
        if previous and previous.reported_at and not data.reported_at:
            advance = False
        if data.stage == "pre_results" and publication.stage != "pre_results":
            advance = False
    if (
        previous
        and previous.reported_at == data.reported_at
        and instant(data.retrieved_at) < instant(cursor.checked_at)
    ):
        advance = False
    if advance:
        if not cursor:
            cursor = CurrentSnapshot(
                event_id=EVENT,
                stream=data.stream,
                snapshot_id=sid,
                checked_at=data.retrieved_at,
            )
            s.add(cursor)
        else:
            cursor.snapshot_id = sid
            cursor.checked_at = max(cursor.checked_at, data.retrieved_at)
        shared_participation = any(
            s.get(PublicationSnapshot, current.snapshot_id).payload.get("provider_participation")
            for current in s.scalars(select(CurrentSnapshot).where(CurrentSnapshot.event_id == EVENT))
        )
        if data.provider_report and data.stage == "pre_results" and not shared_participation:
            publication.completeness = data.completeness
            publication.verification = "provider_report"
            publication.notes = data.notes
            contest = s.get(Contest, target_contest)
            contest.source_id = "snapshot-" + sid
            contest.notes = data.notes
        if data.provider_participation:
            for contest_id in (CONTEST, AG_CONTEST):
                current_publication = s.get(ElectionPublication, contest_id)
                if current_publication.stage != "pre_results":
                    continue
                current_publication.completeness = "partial"
                current_publication.verification = "provider_report"
                current_publication.notes = "Early-voting participation reports from the selected provider, shared by Governor and Attorney General. Candidate results are unavailable."
                current_contest = s.get(Contest, contest_id)
                current_contest.source_id = "snapshot-" + sid
                current_contest.notes = current_publication.notes
        if data.kind == "results":
            old_ids = list(
                s.scalars(
                    select(Participation.id).where(
                        Participation.contest_id == target_contest
                    )
                )
            )
            s.execute(
                delete(VoteResult).where(VoteResult.participation_id.in_(old_ids))
            )
            s.execute(
                delete(Participation).where(Participation.contest_id == target_contest)
            )
            s.flush()
            vote_values = {(v.geoid, v.candidate): v.votes for v in data.votes}
            for c in data.candidates:
                prefix = {
                    "attorney-general": "2026-ag-",
                }.get(data.office_id, "2026-")
                cid = prefix + c.key
                if not s.get(Party, c.party):
                    s.add(Party(id=c.party, name=c.party_name))
                s.merge(Candidate(id=cid, name=c.name))
                s.flush()
                s.add(
                    Participation(
                        id=cid,
                        contest_id=target_contest,
                        candidate_id=cid,
                        party_id=c.party,
                        write_in=c.write_in,
                        category=c.category,
                    )
                )
                s.flush()
                for unit in sorted(units):
                    value = vote_values.get((unit, c.key))
                    valid = data.roster_complete and unit in data.complete_units
                    s.add(
                        VoteResult(
                            participation_id=cid,
                            unit_id=unit,
                            votes=value,
                            source_id="snapshot-" + sid,
                            status="unavailable"
                            if value is None
                            else (
                                "verified"
                                if data.stage == "certified"
                                else "source_checked"
                            )
                            if valid
                            else "unverified",
                        )
                    )
            publication.stage = data.stage
            publication.completeness = data.completeness
            publication.verification = data.verification
            publication.result_snapshot_id = sid
            publication.notes = data.notes
            contest = s.get(Contest, target_contest)
            contest.status = "verified" if data.stage == "certified" else "unofficial"
            contest.notes = data.notes
            contest.source_id = "snapshot-" + sid
            if reconciliation:
                from .models import ImportRun

                s.add(
                    ImportRun(
                        contest_id=target_contest,
                        created_at=now.isoformat(),
                        status="verified",
                        report=reconciliation,
                    )
                )
    else:
        warnings.append("Older source release archived; current values preserved.")
    s.add(
        RefreshAttempt(
            event_id=EVENT,
            stream=data.stream,
            attempted_at=now.isoformat(),
            success=True,
            error=None,
            snapshot_id=sid,
        )
    )
    s.flush()
    return dict(
        snapshot_id=sid, created=not bool(existing), advanced=advance, warnings=warnings
    )


def activity(s, contest_id, now=None):
    publication = s.get(ElectionPublication, contest_id)
    if not publication:
        return None
    now = now or utcnow()
    contest = s.get(Contest, contest_id)
    cursors = list(
        s.scalars(
            select(CurrentSnapshot).where(CurrentSnapshot.event_id == contest.event_id)
        )
    )
    shared = [
        snap for cursor in cursors
        if (snap := s.get(PublicationSnapshot, cursor.snapshot_id)).payload.get("provider_participation")
    ] if publication.stage == "pre_results" else []
    shared_provider = max(shared, key=lambda snap: snap.retrieved_at).payload["provider_participation"]["provider"] if shared else None
    shared = [snap for snap in shared if snap.payload["provider_participation"]["provider"] == shared_provider]
    shared_ids = {snap.id for snap in shared}
    participation_report = {
        "provider": shared_provider,
        "reports": [dict(**snap.payload["provider_participation"], source_id=snap.source_id, snapshot_id=snap.id) for snap in shared],
    } if shared else None
    selected_provider = next(
        (
            snap
            for cursor in cursors
            if (snap := s.get(PublicationSnapshot, cursor.snapshot_id)).contest_id == contest_id
            and snap.source_id == contest.source_id
            and snap.payload.get("provider_report")
        ),
        None,
    )
    if shared:
        selected_provider = None
    provider_report = selected_provider.payload["provider_report"] if selected_provider else None
    observations = {}
    sources = {}
    releases = []
    warnings = []
    for cursor in cursors:
        snap = s.get(PublicationSnapshot, cursor.snapshot_id)
        if shared and snap.id not in shared_ids:
            continue
        if not shared and selected_provider and snap.id != selected_provider.id:
            continue
        if not shared and snap.payload.get("provider_report") and snap.contest_id != contest_id:
            continue
        if snap.kind == "results" and snap.contest_id != contest_id:
            continue
        source = s.get(Source, snap.source_id)
        sources[source.id] = source
        failure = s.scalar(
            select(RefreshAttempt)
            .where(
                RefreshAttempt.event_id == contest.event_id,
                RefreshAttempt.stream == cursor.stream,
                RefreshAttempt.success == False,
                RefreshAttempt.attempted_at > cursor.checked_at,
            )
            .order_by(RefreshAttempt.id.desc())
        )
        stale = bool(failure) or now - instant(cursor.checked_at) > timedelta(hours=24)
        releases.append(
            dict(
                id=snap.id,
                stream=snap.stream,
                kind=snap.kind,
                stage=snap.stage,
                reported_at=snap.reported_at,
                report_precision=snap.report_precision,
                retrieved_at=cursor.checked_at,
                release_id=snap.release_id,
                vote_scope=snap.vote_scope,
                stale=stale,
                error=failure.error if failure else None,
                source_id=source.id,
            )
        )
        warnings.extend(snap.warnings)
        for m in s.scalars(
            select(MetricObservation).where(MetricObservation.snapshot_id == snap.id)
        ):
            observations[(m.unit_id, m.key)] = dict(
                key=m.key,
                label=m.label,
                definition=m.definition,
                value=m.value,
                completeness=m.completeness,
                coverage_note=m.coverage_note,
                source_id=source.id,
                snapshot_id=snap.id,
                reported_at=snap.reported_at,
                report_precision=snap.report_precision,
                retrieved_at=cursor.checked_at,
                stale=stale,
            )

    def metrics(unit):
        extra_keys = sorted({key for geoid, key in observations if geoid == unit and key not in METRICS})
        labels = [*METRICS.items(), *((key, key) for key in extra_keys)]
        return [
            observations.get(
                (unit, key),
                dict(
                    key=key,
                    label=label,
                    definition=(
                        "The selected provider has not supplied this metric."
                        if provider_report or participation_report
                        else "No verified official figure imported for this county/metric."
                    ),
                    value=None,
                    completeness="unavailable",
                    coverage_note="N/A does not mean zero.",
                    source_id=None,
                    snapshot_id=None,
                    reported_at=None,
                    report_precision="unknown",
                    retrieved_at=None,
                    stale=False,
                ),
            )
            for key, label in labels
        ]

    counties = [
        dict(geoid=u.id, name=u.name, metrics=metrics(u.id))
        for u in s.scalars(
            select(GeographicUnit)
            .where(GeographicUnit.kind == "county")
            .order_by(GeographicUnit.name)
        )
    ]
    coverage = {
        key: sum(
            1
            for c in counties
            for m in c["metrics"]
            if m["key"] == key and m["value"] is not None
        )
        for key in METRICS
    }
    leaders = {}
    if publication.stage == "unofficial" and publication.result_snapshot_id:
        from .services import results

        for unit in s.scalars(
            select(GeographicUnit).where(GeographicUnit.kind.in_(["county", "state"]))
        ):
            r = results(s, contest, unit)
            if (
                r.total_votes
                and r.candidates
                and (
                    len(r.candidates) == 1
                    or r.candidates[0].votes > r.candidates[1].votes
                )
            ):
                leaders[unit.id] = r.candidates[0].model_dump()
    failures = []
    for attempt in s.scalars(
        select(RefreshAttempt)
        .where(
            RefreshAttempt.event_id == contest.event_id, RefreshAttempt.success == False
        )
        .order_by(RefreshAttempt.id.desc())
    ):
        if shared and attempt.stream not in {snap.stream for snap in shared}:
            continue
        if selected_provider and attempt.stream != selected_provider.stream:
            continue
        valid_result_streams = {
            AG_CONTEST: {"results-attorney-general"},
            CONTEST: {"results", "results-governor"},
        }.get(contest_id, set())
        if (
            attempt.stream.startswith("results")
            and attempt.stream not in valid_result_streams
        ):
            continue
        cursor = next((c for c in cursors if c.stream == attempt.stream), None)
        if (cursor is None or attempt.attempted_at > cursor.checked_at) and not any(
            f["stream"] == attempt.stream for f in failures
        ):
            failures.append(
                dict(
                    stream=attempt.stream,
                    attempted_at=attempt.attempted_at,
                    error=attempt.error,
                )
            )
    return dict(
        stage=publication.stage,
        candidate_availability=(
            "published"
            if publication.stage != "pre_results"
            else provider_report["race_status"]
            if provider_report
            else "not_released"
            if now < RELEASE_AFTER
            else "not_imported"
        ),
        completeness=publication.completeness,
        verification=publication.verification,
        provider_report=provider_report,
        provider_participation=participation_report,
        notes=publication.notes,
        statewide=dict(geoid="04", name="Arizona", metrics=metrics("04")),
        counties=counties,
        coverage=coverage,
        releases=releases,
        warnings=warnings,
        stale=bool(failures) or any(r["stale"] for r in releases),
        failures=failures,
        sources=[
            dict(id=x.id, title=x.title, url=x.url, sha256=x.sha256, notes=x.notes)
            for x in sources.values()
        ],
        reported_leaders=leaders,
        refresh_mode="manual",
        statewide_policy=(
            "Statewide totals use the provider's statewide party buckets; county figures remain separate. Party categories describe participation, not candidate votes."
            if participation_report
            else "Only directly published statewide figures are shown. County releases have separate source dates and are never presented as a synchronized statewide report."
        ),
    )
