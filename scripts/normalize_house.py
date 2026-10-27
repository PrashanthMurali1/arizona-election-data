"""Validate reviewed House records and normalize independent district contests offline."""

import csv
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.house_sources import (
    COUNTY_IDS,
    clerk_candidates,
    indexed_candidates,
    name_tokens,
    verify_snapshots,
)

RAW = ROOT / "data/raw/us-house"
OUT = ROOT / "data/processed/us-house"


def read_reference(path):
    rows = []
    for row in csv.DictReader(path.open(encoding="utf-8", newline="")):
        if row["write_in"] not in {"true", "false"}:
            raise ValueError("House write-in classification must be explicit")
        cells = {}
        inactive = []
        for unit in COUNTY_IDS:
            value = row[unit]
            if value == "NA":
                inactive.append(unit)
            elif value == "":
                cells[unit] = None
            elif re.fullmatch(r"\d+", value):
                cells[unit] = int(value)
            else:
                raise ValueError(
                    "House votes must be integers, blank missing cells or explicit NA"
                )
        rows.append(
            {
                "district": int(row["district"]),
                "party": row["party"],
                "name": row["name"],
                "write_in": row["write_in"] == "true",
                "category": row.get("category") or "named_candidate",
                "county_votes": cells,
                "not_applicable_counties": inactive,
                "official_total": int(row.get("reported_total") or row.get("official_total") or 0) or None,
                "source_id": row["source_id"],
            }
        )
    return rows


def validate_event(event, rows, original_rows=None):
    expected = set(event["districts"])
    if {r["district"] for r in rows} != expected:
        raise ValueError("House district coverage differs from the actual election")
    if len({(r["district"], r["name"]) for r in rows}) != len(rows):
        raise ValueError("Duplicate House candidate in a district")
    if original_rows is not None:
        if len(original_rows) != len(rows):
            raise ValueError("House roster differs from original county records")
        for row in rows:
            originals = [
                r
                for r in original_rows
                if r["district"] == row["district"] and r["name"] == row["name"]
            ]
            if len(originals) != 1:
                raise ValueError(
                    "House candidate not found uniquely in original county records"
                )
            original = originals[0]
            cells = [
                (
                    "NA"
                    if c in row["not_applicable_counties"]
                    else row["county_votes"].get(c)
                )
                for c in COUNTY_IDS
            ]
            if cells != original["cells"] or any(
                row[k] != original[k] for k in ("party", "write_in", "official_total")
            ):
                raise ValueError(
                    f"House candidate differs from original source cells: {row['name']}"
                )
            if row["category"] != original.get("category", "named_candidate"):
                raise ValueError("House write-in category differs from original source")
    if event.get("clerk_path"):
        clerk = clerk_candidates(ROOT / event["clerk_path"])
        if len(clerk) != len(rows):
            raise ValueError("House roster differs from official Clerk statistics")
        matched = set()
        for row in rows:
            target = row["official_total"]
            # The court's final recount supersedes these two original Clerk totals.
            if event["year"] == 2014 and row["source_id"] == "house-2014-recount":
                target -= {"Ron Barber": 4, "Martha McSally": 10}[row["name"]]
            candidates = [
                (i, c)
                for i, c in enumerate(clerk)
                if c["district"] == row["district"]
                and c["votes"] == target
                and c["write_in"] == row["write_in"]
                and len(name_tokens(c["name"]) & name_tokens(row["name"])) >= 2
            ]
            if len(candidates) != 1 or candidates[0][0] in matched:
                raise ValueError(f"Unreconciled House Clerk candidate: {row['name']}")
            matched.add(candidates[0][0])
    for row in rows:
        if event.get("source_scope") == "civicapi_district":
            if row["official_total"] is None or row["write_in"]:
                raise ValueError("civicAPI special records require named candidate totals")
            continue
        if not row["county_votes"] or any(
            v is None for v in row["county_votes"].values()
        ):
            if not (event["kind"] == "special" and event.get("verification_blockers")):
                raise ValueError(
                    f"House candidate has missing reporting records: {row['name']}"
                )
        if row["official_total"] is None:
            if not (event["kind"] == "special" and event.get("verification_blockers")):
                raise ValueError("Missing official district reference")
        elif (
            sum(v for v in row["county_votes"].values() if v is not None)
            != row["official_total"]
        ):
            raise ValueError(
                f"House candidate county sum differs from official district total: {row['name']}"
            )


def normalize():
    manifest = json.loads((RAW / "manifest.json").read_text())
    verify_snapshots(manifest)
    from scripts.house_records import regular_records

    originals = regular_records()
    from scripts.house_special import RACES, special_records

    specials = special_records()
    elections = []
    for event in manifest["events"]:
        reference = ROOT / event["reference_path"]
        rows = read_reference(reference)
        validate_event(
            event,
            rows,
            (
                originals[event["year"]]
                if event["kind"] == "general"
                else specials[event["date"]]
            ),
        )
        status = "incomplete" if event.get("verification_blockers") else "verified"
        source_report = None
        if event.get("source_scope") == "civicapi_district":
            snapshot_name, _ = RACES[event["date"]]
            snapshot = json.loads((RAW / "civicapi" / snapshot_name).read_text())
            source_report = {
                "kind": "provider_results",
                "provider": "civicAPI",
                "percent_reporting": snapshot.get("percent_reporting"),
                "last_updated": snapshot.get("last_updated"),
                "candidates": [
                    {
                        "candidate": c["name"],
                        "votes": c["votes"],
                        "percent": c.get("percent"),
                        "winner": c.get("winner", False),
                    }
                    for c in snapshot["candidates"]
                ],
            }
        contests = []
        for district in event["districts"]:
            unit = f"az-cd-{event['plan']}-{district:02}"
            cid = f"az-{event['date']}-us-house-{district:02}"
            candidates = []
            reports = []
            selected = [r for r in rows if r["district"] == district]
            for index, row in enumerate(selected):
                missing = [u for u, v in row["county_votes"].items() if v is None]
                known_sum = sum(
                    v for v in row["county_votes"].values() if v is not None
                )
                county_sum = None if missing else known_sum
                candidates.append(
                    {
                        "id": f"house-{event['date']}-{district:02}-{index}",
                        "name": row["name"],
                        "party": row["party"],
                        "write_in": row["write_in"],
                        "category": row["category"],
                        "county_votes": (
                            {}
                            if event.get("source_scope") == "civicapi_district"
                            else row["county_votes"]
                        ),
                        "votes": (
                            row["official_total"]
                            if row["official_total"] is not None
                            else county_sum
                        ),
                        "county_source_id": row["source_id"],
                        "district_source_id": (
                            row["source_id"]
                            if row["source_id"] == "house-2014-recount"
                            else event["source"]["id"]
                        ),
                    }
                )
                if event.get("source_scope") != "civicapi_district":
                    reports.append(
                        {
                        "candidate": row["name"],
                        "county_sum": county_sum,
                        "known_county_sum": known_sum,
                        "official_district": row["official_total"],
                        "difference": (
                            county_sum - row["official_total"]
                            if county_sum is not None
                            and row["official_total"] is not None
                            else None
                        ),
                        "missing_counties": missing,
                        "reported_counties": [
                            u for u, v in row["county_votes"].items() if v is not None
                        ],
                        "not_applicable_counties": row["not_applicable_counties"],
                        }
                    )
            report = {
                "status": "civicapi_report" if source_report else status,
                "district": district,
                "candidate_count": len(candidates),
                "county_count": (
                    0
                    if source_report
                    else len(set().union(*(r["county_votes"] for r in selected)))
                ),
                "candidates": (
                    source_report["candidates"] if source_report else reports
                ),
                "kind": (
                    "provider_results" if source_report else "county_reconciliation"
                ),
                "provider": source_report,
                "reference_path": event["reference_path"],
                "reference_sha256": hashlib.sha256(reference.read_bytes()).hexdigest(),
                "clerk_comparison": (
                    "Court-certified 2014 CD2 recount supersedes two pre-recount Clerk totals"
                    if event["year"] == 2014 and district == 2
                    else (
                        "All candidate totals agree"
                        if event.get("clerk_path")
                        else event["validation_method"]
                    )
                ),
                "verification_blockers": event.get("verification_blockers", []),
                "source_checksums_validated": True,
                "source_cells_validated": True,
                "additional_source_ids": [
                    s["id"] for s in event.get("additional_sources", [])
                ],
            }
            contests.append(
                {
                    "id": cid,
                    "district": district,
                    "unit_id": unit,
                    "status": status,
                    "candidates": candidates,
                    "reconciliation": report,
                }
            )
        elections.append({**event, "contests": contests})
        print(
            event["overview_id"],
            len(contests),
            "district contests;",
            len(rows),
            "reported entries;",
            "civicAPI report" if source_report else status,
        )
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "elections.json").write_text(
        json.dumps(
            {
                "elections": elections,
                "input_manifest_sha256": hashlib.sha256(
                    (RAW / "manifest.json").read_bytes()
                ).hexdigest(),
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )
    return elections


if __name__ == "__main__":
    normalize()
