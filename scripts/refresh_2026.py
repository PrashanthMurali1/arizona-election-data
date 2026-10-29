"""Explicit 2026 source refreshes; archived inputs support offline replay."""

import argparse
import csv
import hashlib
import io
import json
import logging
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

import requests
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.database import SessionLocal
from backend.app.publication_input import SnapshotInput
from backend.app.lifecycle import apply_snapshot, record_failure
from backend.app.observability import emit, failure_level

LAYER = "https://services.arcgis.com/ykpntM6e3tHvzKRJ/arcgis/rest/services/Maricopa_County_Early_Voting_Returns_In_Hand/FeatureServer/0"
PIMA = "https://recorder.pima.gov/BallotProcessingReports"
RAW = ROOT / "data/raw/2026"


def raw_file(payload, suffix):
    digest = hashlib.sha256(payload).hexdigest()
    path = RAW / "snapshots" / f"{digest}.{suffix}"
    path.parent.mkdir(exist_ok=True, parents=True)
    if not path.exists():
        path.write_bytes(payload)
    return str(path.relative_to(ROOT)), digest


def base(
    stream, title, url, payload, suffix, reported_at, precision, release_id, notes
):
    path, digest = raw_file(payload, suffix)
    return dict(
        election_date="2026-11-03",
        election_kind="general",
        stream=stream,
        kind="participation",
        stage="pre_results",
        completeness="partial",
        verification="source_checked",
        source=dict(title=title, url=url, raw_path=path, sha256=digest, notes=notes),
        reported_at=reported_at,
        report_precision=precision,
        retrieved_at=datetime.now(timezone.utc).isoformat(),
        release_id=release_id,
        vote_scope="participation",
        metrics=[],
        notes=notes,
    )


def metric(geoid, key, label, value, definition, coverage="", complete=True):
    return dict(
        geoid=geoid,
        key=key,
        label=label,
        value=value,
        definition=definition,
        coverage_note=coverage,
        completeness="unavailable"
        if value is None
        else "complete"
        if complete
        else "partial",
    )


def registration():
    path = RAW / "registration-reviewed.csv"
    provenance = json.loads((RAW / "registration-provenance.json").read_text())
    rows = list(csv.DictReader(path.open()))
    if (
        len(rows) != 16
        or sum(int(r["active_registered_voters"]) for r in rows if r["geoid"] != "04")
        != provenance["statewide_reference"]
    ):
        raise ValueError(
            "Registration county totals fail official statewide reconciliation"
        )
    data = base(
        "registration",
        "Arizona Secretary of State — 2026 active registration",
        provenance["source_url"],
        path.read_bytes(),
        "csv",
        provenance["published_date"],
        "date",
        "2026-general-active-registration",
        provenance["method"],
    )
    data["retrieved_at"] = provenance["retrieved_at"]
    data["completeness"] = "complete"
    data["metrics"] = [
        metric(
            r["geoid"],
            "registered_voters",
            "Active registered voters",
            int(r["active_registered_voters"]),
            "Active registered voters, GE 2026 total column (all parties). Registration is not a ballot-return count, governor contest votes, or a turnout denominator for this display.",
            "Official county and statewide figures; source publication date October 20, no clock time.",
        )
        for r in rows
    ]
    return data


def maricopa_from_bundle(bundle):
    if bundle["publisher"]["owner"] != "MaricopaElectionsGIS":
        raise ValueError("Unexpected ArcGIS publisher")
    attrs = [x["attributes"] for x in bundle["aggregate"]["features"]]
    valid = [
        a
        for a in attrs
        if (a.get("ElectionDescription") or "").strip() == "NOV 3 2026 GENERAL ELECTION"
    ]
    unknown = [a for a in attrs if a not in valid]
    if len(valid) != 1 or any(
        (a.get("ElectionDescription") or "").strip() for a in unknown
    ):
        raise ValueError(
            "Aggregate layer is not exclusively the 2026 general election; primary results are forbidden"
        )
    row = valid[0]
    count = row["records"]
    missing = sum(a["records"] for a in unknown)
    complete = (
        not missing
        and row["request_records"] == count
        and row["return_records"] == count
    )
    for field, coverage_field in [
        ("requests", "request_records"),
        ("returns", "return_records"),
    ]:
        if (
            row[coverage_field] != count
            or type(row[field]) not in (int, float)
            or row[field] < 0
            or int(row[field]) != row[field]
        ):
            raise ValueError(
                "Maricopa aggregate contains missing or invalid active-election counts"
            )
    stamp = datetime.fromtimestamp(
        bundle["layer"]["editingInfo"]["dataLastEditDate"] / 1000, timezone.utc
    ).isoformat()
    payload = json.dumps(bundle, sort_keys=True).encode()
    note = f"Sum of the official layer’s {count} non-null general-election precinct records. {missing} layer records have no election label/counts and are excluded, not treated as zero. Returns include all signature-review dispositions; they are not accepted ballots or candidate votes."
    data = base(
        "maricopa",
        "Maricopa County Elections — early returns in hand",
        LAYER,
        payload,
        "json",
        stamp,
        "datetime",
        "maricopa-general-" + stamp,
        note,
    )
    coverage = (
        f"{count} general-election records; {missing} null/unattributed layer records excluded. Partial source coverage."
        if missing
        else f"All {count} general-election records."
    )
    data["metrics"] = [
        metric(
            "04013",
            "ballots_requested",
            "Ballots requested (source Requests)",
            int(row["requests"]),
            "Official aggregate Requests field; requests are distinct from ballots mailed, issued, received or accepted.",
            coverage,
            complete,
        ),
        metric(
            "04013",
            "ballots_received",
            "Early voting returns in hand",
            int(row["returns"]),
            "Official aggregate Returns field: all early voting returns in hand, regardless of disposition in signature review. Not an accepted-ballot count.",
            coverage,
            complete,
        ),
    ]
    return data


def fetch_maricopa():
    def get(url, **kwargs):
        r = requests.get(url, timeout=30, **kwargs)
        r.raise_for_status()
        d = r.json()
        if "error" in d:
            raise ValueError(json.dumps(d["error"]))
        return d

    publisher = get(
        "https://www.arcgis.com/sharing/rest/content/items/4f442e13c5514ce7b719844c90a5efe5",
        params={"f": "json"},
    )
    before = get(LAYER, params={"f": "json"})
    stats = [
        dict(statisticType=k, onStatisticField=f, outStatisticFieldName=n)
        for k, f, n in [
            ("sum", "Requests", "requests"),
            ("sum", "Returns", "returns"),
            ("count", "OBJECTID", "records"),
            ("count", "Requests", "request_records"),
            ("count", "Returns", "return_records"),
        ]
    ]
    aggregate = get(
        LAYER + "/query",
        params={
            "where": "1=1",
            "groupByFieldsForStatistics": "ElectionTitle,ElectionDescription",
            "outStatistics": json.dumps(stats),
            "returnGeometry": "false",
            "f": "json",
        },
    )
    after = get(LAYER, params={"f": "json"})
    if before["editingInfo"] != after["editingInfo"]:
        raise ValueError(
            "County layer changed during retrieval; retry for a consistent source snapshot"
        )
    return maricopa_from_bundle(
        dict(
            publisher={
                k: publisher[k] for k in ["id", "owner", "title", "url", "description"]
            },
            layer=before,
            aggregate=aggregate,
        )
    )


class HiddenFields(HTMLParser):
    def __init__(self):
        super().__init__()
        self.fields = {}

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "input" and d.get("type") == "hidden" and "name" in d:
            self.fields[d["name"]] = d.get("value", "")


def pima_from_pdf(payload):
    pages = [p.extract_text() or "" for p in PdfReader(io.BytesIO(payload)).pages]
    matching = [
        p
        for p in pages
        if "Early Ballot Status Report" in p
        and "2026 GENERAL ELECTION" in p
        and "Status as of end of day:" in p
    ]
    if len(matching) != 1:
        raise ValueError(
            "Expected exactly one 2026 general-election status page; do not use primary canvasses from this PDF"
        )
    text = re.sub(r"\s+", " ", matching[0])
    date_match = re.search(
        r"Status as of end of day:\s*([A-Za-z]+, [A-Za-z]+ \d{1,2}, 2026)", text
    )
    if not date_match:
        raise ValueError("Pima source report date could not be established")
    day = datetime.strptime(date_match[1], "%A, %B %d, %Y").date().isoformat()

    def number(label):
        match = re.search(re.escape(label) + r"\s+([\d,]+)", text)
        if not match:
            raise ValueError("Missing source field: " + label)
        return int(match[1].replace(",", ""))

    notes = "Official daily general-election status, as of end of source day. When multiple ballots are sent to a voter, only the last ballot issued is included in these status totals. Returns include ballots awaiting verification or follow-up; they are not votes counted."
    data = base(
        "pima",
        "Pima County Recorder — early ballot status",
        PIMA,
        payload,
        "pdf",
        day,
        "date",
        "pima-general-" + day,
        notes,
    )
    data["metrics"] = [
        metric(
            "04019",
            "ballots_issued",
            "Ballots Sent (latest issue)",
            number("Ballots Sent"),
            notes,
        ),
        metric(
            "04019",
            "ballots_received",
            "Number of Early Ballots Returned",
            number("Number of Early Ballots Returned"),
            notes,
        ),
        metric(
            "04019",
            "ballots_verified_ready",
            "Ballots Verified and Ready to be Turned Over",
            number("Ballots Verified and Ready to be Turned Over"),
            "Source category for verified ballots awaiting turnover; excludes ballots already turned over. Do not treat as all accepted ballots.",
        ),
        metric(
            "04019",
            "ballots_turned_over",
            "Ballots Turned Over to the Elections Department",
            number("Ballots Turned Over to the Elections Department"),
            "Recorder-to-Elections transfer count; turnover is not tabulation or candidate votes.",
        ),
    ]
    # Preserve a reported arithmetic discrepancy; never force it to balance.
    sent = number("Ballots Sent")
    returned = number("Number of Early Ballots Returned")
    outstanding = number("Early Ballots Not Yet Returned")
    if returned + outstanding != sent:
        data["source_warnings"] = [
            f"Pima source figures: returned {returned} + not yet returned {outstanding} = {returned + outstanding}, versus Ballots Sent {sent} (difference {returned + outstanding - sent:+d}). Source values retained without adjustment; processing categories must not be treated as a synchronized accounting identity."
        ]
    return data


def fetch_pima():
    session = requests.Session()
    r = session.get(PIMA, timeout=30)
    r.raise_for_status()
    parser = HiddenFields()
    parser.feed(r.text)
    parser.fields.update(
        __EVENTTARGET="ctl00$ContentPlaceHolder1$LinkButton1", __EVENTARGUMENT=""
    )
    r = session.post(PIMA, data=parser.fields, timeout=45)
    r.raise_for_status()
    if not r.content.startswith(b"%PDF"):
        raise ValueError("Pima public report download did not return a PDF")
    return pima_from_pdf(r.content)


def save_manifest(data):
    parsed = SnapshotInput.model_validate(data)
    # Persist every reviewed acquisition, but preserve existing immutable files.
    path = (
        RAW
        / "manifests"
        / f"{parsed.stream}-{hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()}.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return parsed


def refresh_early_voting():
    from scripts.provider_2026 import fetch_provider_inputs

    try:
        payloads, failures = fetch_provider_inputs()
    except Exception as exc:
        emit(failure_level(exc), 'participation_acquisition_failed', exc=exc, outcome='failed')
        payloads = []
        failures = [(f"early-vote-{category}", str(exc)) for category in ("requested", "returned")]
    for payload in payloads:
        try:
            data = save_manifest(payload)
            with SessionLocal.begin() as s:
                apply_snapshot(s, data)
        except Exception as exc:
            emit(failure_level(exc), 'participation_import_failed', exc=exc, outcome='failed')
            failures.append((payload["stream"], str(exc)))
    for stream, error in failures:
        with SessionLocal.begin() as s:
            record_failure(s, stream, error)
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--providers", "--early-voting", action="store_true",
        help="Refresh shared 2026 early-voting participation only; never fetch candidate races",
    )
    group.add_argument(
        "--fetch",
        choices=["maricopa", "pima", "all"],
        help="Explicit network refresh; previous values survive source failures",
    )
    group.add_argument(
        "--manifest",
        type=Path,
        help="Import one reviewed aggregate/result release from data/raw",
    )
    args = parser.parse_args()
    if args.providers:
        from scripts.early_vote_runtime import run_refresh

        raise SystemExit(run_refresh(refresh_early_voting))
    elif args.fetch:
        streams = ["maricopa", "pima"] if args.fetch == "all" else [args.fetch]
        failures = []
        for stream in streams:
            try:
                data = save_manifest(
                    fetch_maricopa() if stream == "maricopa" else fetch_pima()
                )
                with SessionLocal.begin() as s:
                    print(stream, json.dumps(apply_snapshot(s, data)))
            except Exception as e:
                with SessionLocal.begin() as s:
                    record_failure(s, stream, e)
                failures.append(f"{stream}: {e}")
                print(stream, "FAILED; last successful values preserved:", e)
        if failures:
            raise SystemExit(1)
    else:
        paths = (
            [args.manifest]
            if args.manifest
            else sorted((RAW / "manifests").glob("*.json"))
        )
        if not paths:
            raise SystemExit(
                "No retained manifests; acquire or review official sources first"
            )
        # Replay in reporting/retrieval order; imports are idempotent and an older
        # report never replaces a newer report for the same stream.
        parsed = sorted(
            [SnapshotInput.model_validate_json(p.read_text()) for p in paths],
            key=lambda p: (p.reported_at or "", p.retrieved_at),
        )
        for data in parsed:
            try:
                with SessionLocal.begin() as s:
                    print(data.stream, json.dumps(apply_snapshot(s, data)))
            except Exception as e:
                with SessionLocal.begin() as s:
                    record_failure(s, data.stream, e)
                raise


if __name__ == "__main__":
    main()
