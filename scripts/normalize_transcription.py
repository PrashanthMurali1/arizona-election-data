"""Normalize reviewed source tables without requiring PDF access or OCR."""

import csv, json, hashlib, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.normalize import COUNTIES, URLS


def normalize(year):
    if year == 2018:
        from scripts.normalize_2018 import normalize_2018

        return normalize_2018()
    p = ROOT / f"data/raw/{year}-governor-transcription.csv"
    candidates = []
    for i, row in enumerate(csv.DictReader(p.open(encoding="utf-8", newline=""))):

        def number(value):
            return int(value) if value else None

        candidates.append(
            dict(
                id=f"{year}-{i}",
                name=row["name"],
                party=row["party"],
                write_in=row["write_in"] == "true",
                category="aggregate_write_in"
                if row["name"] == "Unattributed write-ins"
                else "named_candidate",
                county_votes={geoid: number(row.get(geoid)) for geoid, _ in COUNTIES},
                statewide=number(row["official_statewide"]),
            )
        )
    turnout = {}
    tp = ROOT / f"data/raw/{year}-turnout-transcription.csv"
    if tp.exists():
        for r in csv.DictReader(tp.open()):
            turnout[r["geoid"]] = {
                k: (float(v) if k == "percent" else int(v)) if v else None
                for k, v in r.items()
                if k != "geoid"
            }
    dates = {2022: "2022-11-08", 2018: "2018-11-06", 2014: "2014-11-04"}
    data = dict(
        year=year,
        date=dates[year],
        source_url=URLS[year],
        source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
        source_notes="Reviewed transcription of the official Arizona statewide canvass. Governor results: page 2; official turnout: page 1. All reported candidates, including named write-ins, are retained.",
        candidates=candidates,
        turnout=turnout,
    )
    (ROOT / f"data/processed/{year}.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    )
    print(year, "normalized", len(candidates), "candidates")


if __name__ == "__main__":
    for p in sorted((ROOT / "data/raw").glob("*-governor-transcription.csv")):
        normalize(int(p.name[:4]))
    for p in sorted((ROOT / "data/raw").glob("*-availability.json")):
        (ROOT / "data/processed" / f"{p.name[:4]}.json").write_text(p.read_text())
