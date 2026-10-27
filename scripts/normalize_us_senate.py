"""Normalize reviewed U.S. Senate county canvass transcriptions."""

import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.normalize import COUNTIES

RAW = ROOT / "data/raw/us-senate"
OUT = ROOT / "data/processed/us-senate"


def normalize(raw: Path) -> Path:
    provenance_path = raw.with_name(raw.stem.replace("-transcription", "-provenance") + ".json")
    provenance = json.loads(provenance_path.read_text())
    candidates = []
    with raw.open(encoding="utf-8", newline="") as source:
        for index, row in enumerate(csv.DictReader(source)):
            candidates.append(
                {
                    "id": f"senate-{provenance['contest_id']}-{index}",
                    "name": row["name"],
                    "party": row["party"],
                    "write_in": row["write_in"].strip().lower() == "true",
                    "category": row.get("category") or "named_candidate",
                    "county_votes": {
                        geoid: int(row[geoid]) if row.get(geoid, "").strip() else None
                        for geoid, _ in COUNTIES
                    },
                    "statewide": int(row["official_statewide"]),
                }
            )
    year = int(provenance["year"])
    data = {
        "year": year,
        "date": provenance["election_date"],
        "event_id": f"az-{year}-general",
        "contest_id": provenance["contest_id"],
        "office_id": "us-senate",
        "office": "U.S. Senate",
        "source_id": provenance["source_id"],
        "source_title": provenance["source_title"],
        "source_url": provenance["source_url"],
        "source_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
        "source_notes": provenance["source_notes"],
        "reference_path": str(raw.relative_to(ROOT)),
        "additional_sources": provenance.get("additional_sources", []),
        "candidates": candidates,
        "turnout": {},
    }
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"{provenance['contest_id']}.json"
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(provenance["contest_id"], "normalized", len(candidates), "candidates")
    return out


if __name__ == "__main__":
    for transcription in sorted(RAW.glob("*-transcription.csv")):
        normalize(transcription)
