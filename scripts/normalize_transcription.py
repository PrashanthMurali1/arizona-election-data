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
    dates = {1994:"1994-11-08",1998:"1998-11-03",2002:"2002-11-05",2006:"2006-11-07",2010:"2010-11-02",2022: "2022-11-08", 2018: "2018-11-06", 2014: "2014-11-04"}
    data = dict(
        year=year,
        date=dates[year],
        source_url=URLS[year],
        source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
        source_notes="Reviewed transcription of the official Arizona statewide canvass. Governor results: page 2; official turnout: page 1. All reported candidates, including named write-ins, are retained.",
        candidates=candidates,
        turnout=turnout,
    )
    if year < 2014:
        provenance = ROOT / f"data/raw/historical-statewide/{year}-governor-provenance.json"
        data["source_title"] = f"{year} Arizona General Election — Official Canvass"
        data["source_notes"] = 'Official general-election canvass: statewide and county candidate results, plus election-wide registration, ballots cast and turnout. All reported candidates and named write-ins are included.'
        if year == 1994:
            data["source_notes"] = 'Arizona Secretary of State official general-election canvass, November 28, 1994 (page 2: Governor; page 1: election-wide registration, ballots cast and turnout). The canvass PDF supplied by the project maintainer is retained with its SHA-256 and every cell, including all named write-ins, was checked against it. All reported candidates and named write-ins are included.'
    output = ROOT / f"data/processed/{year}.json"
    output.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(year, "normalized", len(candidates), "candidates")


if __name__ == "__main__":
    for p in sorted((ROOT / "data/raw").glob("*-governor-transcription.csv")):
        normalize(int(p.name[:4]))
    for p in sorted((ROOT / "data/raw").glob("*-availability.json")):
        (ROOT / "data/processed" / f"{p.name[:4]}.json").write_text(p.read_text())
    from scripts.normalize_attorney_general import normalize as normalize_ag

    for raw in sorted((ROOT / "data/raw/attorney-general").glob("*-transcription.csv")):
        normalize_ag(int(raw.name[:4]))
    from scripts.normalize_us_senate import normalize as normalize_senate

    for raw in sorted((ROOT / "data/raw/us-senate").glob("*-transcription.csv")):
        if "-turnout-" not in raw.name:
            normalize_senate(raw)
    from scripts.normalize_governor_historical import normalize as normalize_governor_historical

    for raw in sorted((ROOT / "data/raw/governor-historical").glob("*-transcription.csv")):
        if "-turnout-" not in raw.name:
            normalize_governor_historical(raw)
    from scripts.normalize_house import normalize as normalize_house

    normalize_house()
