"""Aggregate VEST ballot candidates; preserve certified named write-ins and turnout.

No precinct write-ins are allocated to people. VEST's aggregate field is retained
in a comparison report and excluded from certified candidate results.
"""

import csv
import hashlib
import io
import json
import sys
import zipfile
from collections import Counter
from pathlib import Path

import shapefile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.normalize import COUNTIES, URLS

VEST_URL = (
    "https://election.lab.ufl.edu/data-downloads/resultsdata/2018/precinct/az_2018.zip"
)
VEST_PAGE = (
    "https://election.lab.ufl.edu/dataset/az-2018-precinct-level-election-results/"
)
# Source county codes map explicitly to stable Census GEOIDs, never fuzzy names.
COUNTY_CODES = dict(
    zip(
        [
            "AP",
            "CH",
            "CN",
            "GI",
            "GM",
            "GN",
            "LP",
            "MC",
            "MO",
            "NA",
            "PM",
            "PN",
            "SC",
            "YA",
            "YU",
        ],
        [geoid for geoid, _ in COUNTIES],
    )
)
CANDIDATE_FIELDS = {
    "Doug Ducey": "G18GOVRDUC",
    "David Garcia": "G18GOVDGAR",
    "Angel Torres": "G18GOVGTOR",
}
FIELDS = [*CANDIDATE_FIELDS.values(), "G18GOVOWRI"]
TARGETS = {"Doug Ducey": 1330863, "David Garcia": 994341, "Angel Torres": 50962}
OPENELECTIONS_URL = "https://github.com/openelections/openelections-data-az/blob/5675ad1dbf77ce24fdd320127215f81b17e1a866/2018/20181106__az__general__county.csv"


def aggregate_vest(path):
    totals = {geoid: Counter() for geoid, _ in COUNTIES}
    precinct_counts = Counter()
    seen = set()
    with zipfile.ZipFile(path) as archive:
        dbf = [name for name in archive.namelist() if name.endswith(".dbf")]
        if len(dbf) != 1:
            raise ValueError("Expected one VEST DBF table")
        reader = shapefile.Reader(
            dbf=io.BytesIO(archive.read(dbf[0])), encoding="utf-8"
        )
        for record in reader.iterRecords():
            row = record.as_dict()
            code = row["CDE_COUNTY"]
            if code not in COUNTY_CODES:
                raise ValueError(f"Unknown VEST county code: {code}")
            geoid = COUNTY_CODES[code]
            precinct = (code, row["PCTNUM"])
            if precinct in seen:
                raise ValueError(f"Duplicate VEST precinct: {precinct}")
            seen.add(precinct)
            precinct_counts[geoid] += 1
            for field in FIELDS:
                value = row[field]
                # Never coerce null/blank records into a zero.
                if type(value) is not int or value < 0:
                    raise ValueError(
                        f"Invalid VEST votes at {precinct}: {field}={value!r}"
                    )
                totals[geoid][field] += value
    if set(precinct_counts) != set(totals):
        raise ValueError("VEST must represent all 15 counties")
    return totals, precinct_counts


def normalize_2018():
    archive = ROOT / "data/raw/2018/az_2018.zip"
    reference_path = ROOT / "data/raw/2018-governor-transcription.csv"
    turnout_path = ROOT / "data/raw/2018-turnout-transcription.csv"
    named_path = ROOT / "data/raw/2018/openelections-county.csv"
    # Check retained inputs against recorded provenance before deriving results.
    manifest = json.loads((ROOT / "data/raw/source-manifest.json").read_text())
    source = next(s for s in manifest["sources"] if s["year"] == 2018)
    for snapshot in source["snapshots"]:
        if (
            hashlib.sha256((ROOT / snapshot["path"]).read_bytes()).hexdigest()
            != snapshot["sha256"]
        ):
            raise ValueError(f"2018 source checksum mismatch: {snapshot['path']}")
    totals, precinct_counts = aggregate_vest(archive)
    with reference_path.open(encoding="utf-8", newline="") as f:
        reference = list(csv.DictReader(f))
    # OpenElections' county export puts the county label in its `precinct`
    # column. Interpret that source format here, then use Census IDs throughout.
    county_names = {name: geoid for geoid, name in COUNTIES}
    named_records = {}
    with named_path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if row["office"] != "Governor":
                continue
            if row["county"] != "Arizona":
                raise ValueError("Unexpected OpenElections jurisdiction")
            unit = (
                "04"
                if row["precinct"] == "TOTAL"
                else county_names.get(row["precinct"])
            )
            if unit is None or not row["votes"].isdigit():
                raise ValueError(
                    "Unknown OpenElections county or missing/invalid votes"
                )
            key = (row["candidate"], unit)
            if key in named_records:
                raise ValueError(f"Duplicate OpenElections candidate/unit: {key}")
            named_records[key] = int(row["votes"])
    expected = {
        (r["name"].replace(" (Write-In)", ""), unit)
        for r in reference
        for unit in ["04", *county_names.values()]
    }
    if set(named_records) != expected:
        raise ValueError(
            "OpenElections must contain exactly eight candidates and all 16 reporting units"
        )
    if len(reference) != 8 or sum(r["write_in"] == "true" for r in reference) != 5:
        raise ValueError(
            "Official 2018 reference must retain all eight candidates, including five named write-ins"
        )
    candidates = []
    comparison_rows = []
    for i, row in enumerate(reference):
        field = CANDIDATE_FIELDS.get(row["name"])
        official = int(row["official_statewide"])
        candidate_name = row["name"].replace(" (Write-In)", "")
        if named_records[(candidate_name, "04")] != official:
            raise ValueError(
                f"OpenElections statewide reference mismatch for {candidate_name}"
            )
        county_votes = {}
        for geoid, _ in COUNTIES:
            # Empty source cells remain null; the strict importer will reject
            # the incomplete set rather than manufacture an allocation.
            county_votes[geoid] = (
                totals[geoid][field]
                if field
                else named_records[(candidate_name, geoid)]
            )
            if county_votes[geoid] != int(row[geoid]) or named_records[
                (candidate_name, geoid)
            ] != int(row[geoid]):
                raise ValueError(
                    f"2018 source disagreement for {candidate_name} in {geoid}"
                )
            if field:
                comparison_rows.append(
                    dict(
                        geoid=geoid,
                        field=field,
                        candidate=row["name"],
                        vest_votes=totals[geoid][field],
                        official_votes=int(row[geoid]),
                        difference=totals[geoid][field] - int(row[geoid]),
                    )
                )
        candidates.append(
            dict(
                id=f"2018-{i}",
                name=row["name"],
                party=row["party"],
                write_in=row["write_in"] == "true",
                category="named_candidate",
                county_votes=county_votes,
                statewide=official,
                county_source_id="vest-2018" if field else "openelections-2018",
            )
        )
    write_in_rows = []
    for geoid, name in COUNTIES:
        official = sum(int(r[geoid]) for r in reference if r["write_in"] == "true")
        observed = totals[geoid]["G18GOVOWRI"]
        write_in_rows.append(
            dict(
                geoid=geoid,
                county=name,
                vest_aggregate_write_ins=observed,
                official_named_write_ins=official,
                difference=observed - official,
            )
        )
    turnout = {}
    with turnout_path.open(newline="") as f:
        for row in csv.DictReader(f):
            if row["geoid"] in turnout:
                raise ValueError("Duplicate official turnout unit")
            turnout[row["geoid"]] = {
                k: (float(v) if k == "percent" else int(v)) if v else None
                for k, v in row.items()
                if k != "geoid"
            }
    if set(turnout) != {"04", *[g for g, _ in COUNTIES]}:
        raise ValueError("Official 2018 turnout must contain state and all 15 counties")
    for key in ["registered_voters", "ballots_cast"]:
        if sum(turnout[g][key] for g, _ in COUNTIES) != turnout["04"][key]:
            raise ValueError(
                f"Official turnout county totals fail reconciliation: {key}"
            )
    write_in_total = sum(r["official_named_write_ins"] for r in write_in_rows)
    vest_write_in_total = sum(r["vest_aggregate_write_ins"] for r in write_in_rows)
    checks = dict(
        ballot_candidate_cells_match=all(r["difference"] == 0 for r in comparison_rows),
        ballot_candidate_statewide_match=all(
            sum(totals[g][field] for g, _ in COUNTIES) == TARGETS[name]
            for name, field in CANDIDATE_FIELDS.items()
        ),
        named_write_in_total_match=write_in_total == 275,
        certified_contest_total_match=sum(c["statewide"] for c in candidates)
        == 2376441,
        official_candidate_count=len(candidates),
        county_count=len(totals),
    )
    validation = dict(
        checks=checks,
        precinct_count=sum(precinct_counts.values()),
        precinct_counts=dict(precinct_counts),
        ballot_candidates=comparison_rows,
        vest_write_in_comparison=dict(
            status="excluded_noncomparable_aggregate",
            vest_total=vest_write_in_total,
            official_named_total=write_in_total,
            difference=vest_write_in_total - write_in_total,
            counties=write_in_rows,
            explanation="VEST reports a broader aggregate write-in field, not the five named certified candidates. Maricopa final official county summary reports the same 1,935 aggregate write-ins as VEST, versus 178 across the named candidates in the statewide canvass. The aggregate is retained unchanged for audit and is not imported or allocated to candidates.",
            investigation_source="https://elections.maricopa.gov/asset/jcr%3A097c22c0-1af9-4570-8257-1af35576f9e5/11-06-2018%20Canvass%20BOS%20SUMMARY%20NOV%202018.pdf",
        ),
    )
    outdir = ROOT / "data/processed/2018"
    outdir.mkdir(exist_ok=True)
    (outdir / "vest-comparison.json").write_text(
        json.dumps(validation, indent=2) + "\n"
    )
    if not all(
        checks[k]
        for k in [
            "ballot_candidate_cells_match",
            "ballot_candidate_statewide_match",
            "named_write_in_total_match",
            "certified_contest_total_match",
        ]
    ):
        raise ValueError(
            "2018 input validation failed; inspect data/processed/2018/vest-comparison.json. No normalized election was replaced."
        )
    notes = "All eight certified candidates reconcile with the official statewide canvass. Three ballot candidates use VEST precinct sums; five named write-ins use retained OpenElections county records. Official turnout is from canvass page 1. VEST’s broader write-in aggregate is excluded: 3,203 versus 275 certified named write-ins."
    data = dict(
        year=2018,
        date="2018-11-06",
        source_url=URLS[2018],
        source_sha256=hashlib.sha256(reference_path.read_bytes()).hexdigest(),
        source_notes=notes,
        candidates=candidates,
        turnout=turnout,
        additional_sources=[
            dict(
                id="vest-2018",
                title="VEST / UF Election Lab — 2018 Arizona precinct results",
                url=VEST_PAGE,
                sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                notes="Retained public az_2018.zip. G18GOVRDUC, G18GOVDGAR and G18GOVGTOR match the official canvass in all 15 counties. G18GOVOWRI is a broader aggregate (3,203), excluded from certified candidate results (275 named write-ins).",
            ),
            dict(
                id="openelections-2018",
                title="OpenElections — 2018 Arizona county results",
                url=OPENELECTIONS_URL,
                sha256=hashlib.sha256(named_path.read_bytes()).hexdigest(),
                notes="Pinned revision 5675ad1. Retains all five named write-in candidates and their actual county values; their statewide totals match the official canvass. Dolego: Navajo 0 and Pinal 1, confirmed from this source after a conflicting indexed-table extraction.",
            ),
        ],
        input_validation=validation,
    )
    (ROOT / "data/processed/2018.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    )
    print(
        f"2018 normalized: 15 counties, 8 candidates, {sum(precinct_counts.values())} VEST precincts; excluded aggregate difference +{vest_write_in_total - write_in_total}"
    )
    return data


if __name__ == "__main__":
    normalize_2018()
