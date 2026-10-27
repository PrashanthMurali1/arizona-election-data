"""Normalize reviewed Attorney General canvass transcriptions."""

import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.normalize import COUNTIES

DATES = {2014: "2014-11-04", 2018: "2018-11-06", 2022: "2022-11-08"}


def normalize(year: int) -> Path:
    raw = ROOT / "data/raw/attorney-general" / f"{year}-transcription.csv"
    provenance = json.loads(
        (ROOT / "data/raw/attorney-general" / f"{year}-provenance.json").read_text()
    )
    candidates = []
    with raw.open(encoding="utf-8", newline="") as f:
        for i, row in enumerate(csv.DictReader(f)):
            candidates.append(
                {
                    "id": f"ag-{year}-{i}",
                    "name": row["name"],
                    "party": row["party"],
                    "write_in": row["write_in"] == "true",
                    "category": "named_candidate",
                    "county_votes": {
                        geoid: int(row[geoid]) if row[geoid] else None
                        for geoid, _ in COUNTIES
                    },
                    "statewide": int(row["official_statewide"]),
                }
            )
    data = {
        "year": year,
        "date": DATES[year],
        "office_id": "attorney-general",
        "office": "Attorney General",
        "source_url": provenance["source_url"],
        "source_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
        "source_notes": (
            f"Reviewed transcription of the official {year} Arizona statewide "
            "canvass Attorney General rows. See data/raw/attorney-general/"
            f"{year}-provenance.json for report date, source URL, transcription "
            "method and checksum. No turnout duplicated; turnout belongs to event."
        ),
        "reference_path": str(raw.relative_to(ROOT)),
        "candidates": candidates,
        "turnout": {},
    }
    out = ROOT / "data/processed/attorney-general" / f"{year}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(year, "Attorney General normalized", len(candidates), "candidates")
    return out


if __name__ == "__main__":
    for year in (2014, 2018, 2022):
        normalize(year)
