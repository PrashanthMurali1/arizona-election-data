"""Import shared 2026 early-voting participation from provider tracker feeds.

This adapter never requests candidate races. Counts are extracted from the
early-vote response's `votes` fields, which represent ballots in party buckets.
No state/county corroboration or arithmetic reconciliation is performed.
"""

import hashlib
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/2026"
CATEGORIES = {
    "requested": ("ballots_requested", "Requested"),
    "returned": ("ballots_received", "Returned"),
    "inperson": ("in_person_early", "In-Person"),
}


def retain(response):
    digest = hashlib.sha256(response.content).hexdigest()
    suffix = "json" if "json" in response.headers.get("content-type", "") else "html"
    path = RAW / "snapshots" / f"{digest}.{suffix}"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(response.content)
    return {
        "url": response.url, "http_status": response.status_code,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "raw_path": str(path.relative_to(ROOT)), "sha256": digest,
    }


def ballot_counts(block):
    """Preserve missing values and zero; aggregate a single provider block only."""
    if not isinstance(block, dict) or not block:
        return None, {}
    counts = {}
    for name, cell in block.items():
        value = cell.get("votes") if isinstance(cell, dict) else None
        if value is not None and (type(value) is not int or value < 0):
            raise ValueError("Early-vote participation counts must be integers or null")
        counts[name] = value
    aggregate = next((name for name in counts if name.lower() in {"total", "all"}), None)
    if aggregate:
        return counts[aggregate], {name: value for name, value in counts.items() if name != aggregate}
    total = None if any(value is None for value in counts.values()) else sum(counts.values())
    return total, counts


def early_vote_input(feed, acquisition, category):
    if feed.get("state") != "AZ" or feed.get("category") != category:
        raise ValueError("Response does not match the requested Arizona early-vote category")
    reported = date.fromisoformat(feed["snapshot_date"])
    if reported.year != 2026 or feed.get("test_data") is True:
        raise ValueError("Only the current 2026 non-test early-vote feed is eligible")
    from scripts.normalize import COUNTIES

    counties = {name.lower(): geoid for geoid, name in COUNTIES}
    key, label = CATEGORIES[category]
    metrics, breakdowns = [], {}

    def add_unit(geoid, block):
        total, buckets = ballot_counts(block)
        breakdowns[geoid] = buckets
        definition = (
            f"civicAPI {label} early-voting participation. The endpoint's votes field counts ballots, not candidate votes. "
            "The total uses this unit's supplied total, or sums its supplied party buckets when no aggregate is supplied. "
            "Statewide figures use only the statewide_total block; county totals are never added into a statewide figure."
        )
        metrics.append({
            "geoid": geoid, "key": key, "label": label, "definition": definition,
            "value": total, "completeness": "unavailable" if total is None else "complete",
            "coverage_note": f"Provider category: {category}; snapshot date: {reported.isoformat()}.",
        })
        for party, value in buckets.items():
            slug = re.sub(r"[^a-z0-9]+", "_", party.lower()).strip("_")[:64]
            if not slug:
                slug = hashlib.sha256(party.encode()).hexdigest()[:16]
            metrics.append({
                "geoid": geoid, "key": f"{key}__{slug}", "label": f"{label} · {party}",
                "definition": f"{label} ballots in civicAPI's {party} participation category. This is a provider party breakdown, not votes or support for any candidate.",
                "value": value, "completeness": "unavailable" if value is None else "complete",
                "coverage_note": f"Party label preserved as reported by civicAPI; snapshot date: {reported.isoformat()}.",
            })

    if "statewide_total" in feed:
        add_unit("04", feed["statewide_total"])
    for name, block in (feed.get("regions") or {}).items():
        geoid = counties.get(name.strip().lower().removesuffix(" county"))
        if geoid is None:
            raise ValueError(f"Cannot attach unknown provider region to an Arizona county: {name}")
        add_unit(geoid, block)
    notes = (
        f"Early-voting participation report from civicAPI: {label}, as of {reported.isoformat()}. "
        "Shared event-level figures for the 2026 Governor and Attorney General pages; no candidate results are imported. "
        "Party categories describe the provider's ballot breakdowns and do not indicate candidate support."
    )
    return {
        "election_date": "2026-11-03", "election_kind": "general", "office_id": "governor",
        "stream": f"early-vote-{category}", "kind": "participation", "stage": "pre_results",
        "completeness": "partial", "verification": "provider_report",
        "provider_participation": {"provider": "civicAPI", "category": category, "label": label, "breakdowns": breakdowns},
        "source": {
            "title": f"civicAPI — {feed.get('election_name') or 'Arizona ' + label + ' early ballots'}",
            "url": acquisition["url"], "raw_path": acquisition["raw_path"], "sha256": acquisition["sha256"],
            "notes": f"{notes} Retained response: {acquisition['raw_path']}. SHA-256 covers that exact response file: {acquisition['sha256']}. Retrieval time is recorded separately on the snapshot.",
        },
        "reported_at": reported.isoformat(), "report_precision": "date", "retrieved_at": acquisition["retrieved_at"],
        "release_id": f"civicapi-early-vote-AZ-{category}-{acquisition['sha256']}",
        "vote_scope": "participation", "metrics": metrics, "notes": notes,
    }


def fetch_provider_inputs():
    acquisitions, payloads, failures, unavailable = [], [], [], []

    def get(url):
        response = requests.get(url, timeout=(5, 25), allow_redirects=False)
        metadata = retain(response)
        acquisitions.append(metadata)
        return response, metadata

    # Scheduled refreshes request only these civicAPI participation feeds.
    for category in CATEGORIES:
        stream = f"early-vote-{category}"
        try:
            response, metadata = get(f"https://civicapi.org/api/v2/early-vote/AZ/{category}")
            if response.status_code == 404:
                unavailable.append({"category": category, "url": metadata["url"], "reason": response.json().get("error", "Not provided")})
                if category != "inperson":
                    failures.append((stream, "Early-vote feed unavailable (HTTP 404); previous data preserved"))
                continue
            response.raise_for_status()
            payload = early_vote_input(response.json(), metadata, category)
            if not any(metric["value"] is not None for metric in payload["metrics"]):
                raise ValueError("Response contains no participation counts; previous data preserved")
            payloads.append(payload)
        except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
            failures.append((stream, str(exc)))
    index = RAW / "providers" / f"early-vote-acquisition-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}.json"
    index.parent.mkdir(parents=True, exist_ok=True)
    index.write_text(json.dumps({"acquisitions": acquisitions, "unavailable": unavailable, "failures": failures}, indent=2) + "\n")
    print("Early-vote acquisition index:", index.relative_to(ROOT))
    return payloads, failures
