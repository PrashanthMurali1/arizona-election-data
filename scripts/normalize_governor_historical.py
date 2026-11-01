"""Normalize the reviewed 1966-1990 Governor transcriptions; verify retained source hashes offline."""

import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.normalize import COUNTIES
from scripts.senate_sources import verify_provenance

RAW = ROOT / "data/raw/governor-historical"
OUT = ROOT / "data/processed/governor-historical"
# Counties that existed for each election; La Paz County was created in 1983.
PRE_1983_BOUNDARY = "county-1966-1982"


def normalize(raw: Path) -> Path:
    provenance_path = raw.with_name(raw.stem.replace("-transcription", "-provenance") + ".json")
    provenance = verify_provenance(provenance_path)
    year = provenance["year"]
    if provenance["contest_id"] != f"az-{year}-governor":
        raise ValueError("Incorrect Governor contest identity")
    units = provenance["expected_units"]
    if units != [g for g, _ in COUNTIES if year >= 1983 or g != "04012"]:
        raise ValueError("Expected counties do not match the counties that existed that year")
    candidates = []
    with raw.open(encoding="utf-8", newline="") as source:
        for index, row in enumerate(csv.DictReader(source)):
            if row["write_in"] not in {"true", "false"}:
                raise ValueError("Write-in flag must be explicit")
            candidates.append({
                "id": f"governor-{year}-{index}",
                "name": row["name"],
                "party": row["party"],
                "write_in": row["write_in"] == "true",
                "category": row.get("category") or "named_candidate",
                "county_votes": {g: int(row[g]) for g in units},
                "statewide": int(row["official_statewide"]),
            })
    if len(candidates) != provenance["candidate_count"] or len({c["name"] for c in candidates}) != len(candidates):
        raise ValueError("Incomplete or duplicate Governor candidate roster")
    data = {
        "year": year,
        "date": provenance["election_date"],
        "event_id": f"az-{year}-general",
        "contest_id": provenance["contest_id"],
        "contest_kind": provenance["contest_kind"],
        "office_id": "governor",
        "office": "Governor",
        "boundary_id": PRE_1983_BOUNDARY if year < 1983 else "county-2022",
        "expected_units": units,
        "source_id": provenance["source_id"],
        "source_title": provenance["source_title"],
        "source_url": provenance["source_url"],
        "source_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
        "source_notes": provenance["source_notes"],
        "reference_path": raw.relative_to(ROOT).as_posix(),
        "provenance_path": provenance_path.relative_to(ROOT).as_posix(),
        "additional_sources": provenance["additional_sources"],
        "status_ceiling": provenance["status_ceiling"],
        "reviewed_county_differences": provenance["reviewed_county_differences"],
        "input_validation": {"source_checksums_validated": True, "candidate_count": len(candidates), "county_count": len(units)},
        "candidates": candidates,
        "turnout": {},
    }
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"az-{year}-governor.json"
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(data["contest_id"], "normalized", len(candidates), "candidates")
    return out


if __name__ == "__main__":
    for transcription in sorted(RAW.glob("*-transcription.csv")):
        normalize(transcription)
