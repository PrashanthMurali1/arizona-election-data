"""Normalize reviewed Senate canvasses; verify retained source hashes offline."""

import csv
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.normalize import COUNTIES
from scripts.senate_sources import candidate_rows, verify_provenance

RAW = ROOT / "data/raw/us-senate"
OUT = ROOT / "data/processed/us-senate"
DATES = {1986: "1986-11-04", 1988: "1988-11-08", 1992: "1992-11-03", 1994: "1994-11-08", 1998: "1998-11-03", 2000: "2000-11-07", 2004: "2004-11-02", 2006: "2006-11-07", 2010: "2010-11-02", 2012: "2012-11-06", 2016: "2016-11-08", 2018: "2018-11-06", 2020: "2020-11-03", 2022: "2022-11-08", 2024: "2024-11-05"}


def xml_candidates(path, reference):
    with ZipFile(path) as archive:
        if archive.namelist() != ["Results.Detail_2020General.xml"]:
            raise ValueError("Unexpected official 2020 XML archive members")
        root = ET.fromstring(archive.read(archive.namelist()[0]))
    if root.findtext("electionInformation/electionDate") != DATES[2020]:
        raise ValueError("Wrong election in 2020 XML")
    contests = [c for c in root.findall("contests/contest") if c.get("contestLongName") == "U.S. Senator (Term Expires Jan. 2023)"]
    if len(contests) != 1 or contests[0].get("termYears") != "2":
        raise ValueError("Expected the two-year special Senate contest")
    expected = {c["name"]: c for c in reference}
    found = {}
    for choice in contests[0].findall("choices/choice"):
        last, first = choice.attrib["choiceName"].split(", ", 1)
        name = f"{first} {last}"
        # The XML spells Mathew with one t; the printed final canvass says Matthew.
        if name == "Mathew Haupt":
            name = "Matthew Haupt"
        if name not in expected or name in found:
            raise ValueError(f"Unexpected or duplicate XML candidate: {name}")
        ref = expected[name]
        cells = choice.findall("jurisdictions/jurisdiction")
        votes = {cell.attrib["name"]: int(cell.attrib["votes"]) for cell in cells}
        if len(cells) != 16 or set(votes) != {"State", *[n for g, n in COUNTIES]}:
            raise ValueError(f"Incomplete/duplicate XML jurisdictions for {name}")
        county_votes = {g: votes[n] for g, n in COUNTIES}
        if county_votes != ref["county_votes"] or votes["State"] != ref["statewide"] or int(choice.attrib["totalVotes"]) != ref["statewide"]:
            raise ValueError(f"2020 XML differs from the final canvass for {name}")
        if choice.attrib["party"].upper() != ref["party"] or (choice.attrib["isWriteIn"] == "true") != ref["write_in"]:
            raise ValueError(f"2020 XML candidate metadata differs for {name}")
        found[name] = county_votes
    if set(found) != set(expected):
        raise ValueError("2020 XML roster differs from final canvass")
    return found


def normalize(raw: Path) -> Path:
    provenance_path = raw.with_name(raw.stem.replace("-transcription", "-provenance") + ".json")
    provenance = verify_provenance(provenance_path)
    year = provenance["year"]
    if year not in DATES or provenance["election_date"] != DATES[year]:
        raise ValueError("Unsupported Arizona Senate election identity")
    expected_id = f"az-{year}-us-senate" + ("-special" if year == 2020 else "")
    if provenance["contest_id"] != expected_id:
        raise ValueError("Incorrect Senate contest identity")
    candidates = []
    with raw.open(encoding="utf-8", newline="") as source:
        for index, row in enumerate(csv.DictReader(source)):
            if row["write_in"] not in {"true", "false"}:
                raise ValueError("Write-in flag must be explicit")
            candidates.append({
                "id": f"senate-{year}-{index}",
                "name": row["name"],
                "party": row["party"],
                "write_in": row["write_in"] == "true",
                "category": row.get("category") or "named_candidate",
                "county_votes": {g: int(row[g]) if row.get(g, "").strip() else None for g, n in COUNTIES},
                "statewide": int(row["official_statewide"]),
            })
    if len(candidates) != provenance["candidate_count"] or len({c["name"] for c in candidates}) != len(candidates):
        raise ValueError("Incomplete or duplicate Senate candidate roster")
    if provenance.get("canvass_extract_path"):
        extracted = candidate_rows(ROOT / provenance["canvass_extract_path"])
        actual = [(c["party"], c["name"], c["write_in"], [c["county_votes"][g] for g, n in COUNTIES] + [c["statewide"]]) for c in candidates]
        if extracted != actual:
            raise ValueError("Reviewed CSV differs from retained official canvass extraction")
    if year == 2020:
        primary = xml_candidates(ROOT / provenance["xml_path"], candidates)
        for c in candidates:
            c["county_votes"] = primary[c["name"]]
            c["county_source_id"] = "us-senate-2020-official-xml"
    turnout = {}
    if provenance.get("turnout_path"):
        for row in csv.DictReader((ROOT / provenance["turnout_path"]).open()):
            if row["geoid"] in turnout:
                raise ValueError("Duplicate Senate event turnout unit")
            turnout[row["geoid"]] = {k: float(row[k]) if k == "percent" else int(row[k]) for k in ["ballots_cast", "registered_voters", "percent"]}
            turnout[row["geoid"]]["definition"] = provenance["turnout_definition"]
            turnout[row["geoid"]]["source_id"] = provenance.get("turnout_source_id", provenance["source_id"])
        if set(turnout) != {"04", *[g for g, n in COUNTIES]}:
            raise ValueError("Turnout must cover all counties and the state")
        for key in ["ballots_cast", "registered_voters"]:
            if sum(v[key] for g, v in turnout.items() if g != "04") != turnout["04"][key]:
                raise ValueError(f"Official turnout county sum does not reconcile: {key}")
    data = {
        "year": year,
        "date": provenance["election_date"],
        "event_id": f"az-{year}-general",
        "contest_id": expected_id,
        "contest_kind": "special" if year == 2020 else "regular",
        "office_id": "us-senate",
        "office": "U.S. Senate",
        "source_id": provenance["source_id"],
        "source_title": provenance["source_title"],
        "source_url": provenance["source_url"],
        "source_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
        "source_notes": provenance["source_notes"],
        "reference_path": raw.relative_to(ROOT).as_posix(),
        "provenance_path": provenance_path.relative_to(ROOT).as_posix(),
        "additional_sources": provenance.get("additional_sources", []),
        "input_validation": {"source_checksums_validated": True, "canvass_candidate_count": len(candidates), "county_count": 15, "xml_matches_final_canvass": True if year == 2020 else None},
        "candidates": candidates,
        "turnout": turnout,
    }
    if all(v is None for c in candidates for v in c["county_votes"].values()):
        data["coverage"] = "statewide_only"
    if provenance.get("status_ceiling"):
        data["status_ceiling"] = provenance["status_ceiling"]
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"{expected_id}.json"
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(expected_id, "normalized", len(candidates), "candidates")
    return out


if __name__ == "__main__":
    for transcription in sorted(RAW.glob("*-transcription.csv")):
        if "-turnout-" not in transcription.name:
            normalize(transcription)
