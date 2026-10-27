"""Re-extract regular House county cells from retained primary snapshots.

2016 sparse cells below were visually reviewed against signed PDF pages 11–12;
this explicit transcription preserves two one-vote glyphs absent in its text layer.
"""

import csv, io, json, re, zipfile, collections
import xml.etree.ElementTree as E
from pathlib import Path
from scripts.house_sources import COUNTY_IDS, indexed_candidates, name_tokens

ROOT = Path(__file__).resolve().parents[1]


def regular_records():
    p = ROOT / "data/raw/us-house"
    fields = [
        "district",
        "party",
        "name",
        "write_in",
        *COUNTY_IDS,
        "official_total",
        "source_id",
    ]
    source_paths = {
        2014: [p / "2014-c-indexed.txt", p / "2014-b-indexed.txt"],
        2018: [
            (ROOT / "data/raw/us-senate/2018-indexed-canvass.txt"),
            p / "2018-b-indexed.txt",
        ],
        2022: [
            (ROOT / "data/raw/us-senate/2022-indexed-canvass.txt"),
            p / "2022-b-indexed.txt",
        ],
        2024: [
            (ROOT / "data/raw/us-senate/2024-indexed-canvass.txt"),
            p / "2024-house-indexed.txt",
        ],
    }
    by_year = {
        y: [r for source in sources for r in indexed_candidates(source)]
        for y, sources in source_paths.items()
    }
    # These sparse cells were read directly from rendered official PDF pages 11 and 12.
    by_year[2016] = []

    def add(d, party, name, values, total, write=False):
        cells = ["NA"] * 15
        for index, value in values.items():
            cells[index] = value
        by_year[2016].append(
            {
                "district": d,
                "party": party,
                "name": name,
                "write_in": write,
                "cells": cells,
                "official_total": total,
            }
        )

    add(
        1,
        "DEM",
        "Tom O'Halleran",
        {
            0: 17906,
            2: 33918,
            3: 4350,
            4: 4315,
            5: 1454,
            7: 354,
            8: 199,
            9: 19160,
            10: 22421,
            11: 30493,
            13: 7649,
        },
        142219,
    )
    add(
        1,
        "GRN",
        "Ray Parrish",
        {
            0: 1644,
            2: 3972,
            3: 463,
            4: 729,
            5: 220,
            7: 34,
            8: 21,
            9: 2673,
            10: 2285,
            11: 3692,
            13: 1013,
        },
        16746,
    )
    add(
        1,
        "REP",
        "Paul Babeu",
        {
            0: 7573,
            2: 18962,
            3: 3097,
            4: 6715,
            5: 1497,
            7: 100,
            8: 71,
            9: 16926,
            10: 28311,
            11: 32117,
            13: 6376,
        },
        121745,
    )
    add(2, "DEM", "Matt Heinz", {1: 15718, 10: 120155}, 135873)
    add(2, "REP", "Martha McSally", {1: 33692, 10: 146114}, 179806)
    add(
        3,
        "DEM",
        "Raul Grijalva",
        {7: 46832, 10: 69048, 11: 117, 12: 12774, 14: 20202},
        148973,
    )
    add(3, "DEM", "Harvey Martin", {7: 70, 10: 155, 11: 0, 12: 15, 14: 43}, 283, True)
    add(
        3,
        "REP",
        "Bill Abatecola",
        {7: 305, 10: 622, 11: 0, 12: 294, 14: 82},
        1303,
        True,
    )
    add(3, "REP", "Jaime Vasquez", {7: 120, 10: 187, 11: 1, 12: 10, 14: 14}, 332, True)
    add(
        3,
        "IND",
        "Federico A. Sanchez",
        {7: 22, 10: 121, 11: 0, 12: 1, 14: 0},
        144,
        True,
    )
    add(
        4,
        "DEM",
        "Mikel Weisser",
        {3: 3379, 6: 1641, 7: 5443, 8: 18498, 11: 18923, 13: 27432, 14: 5980},
        81296,
    )
    add(
        4,
        "REP",
        "Paul Gosar",
        {3: 10522, 6: 3901, 7: 14232, 8: 56136, 11: 39374, 13: 64689, 14: 14633},
        203487,
    )
    add(5, "DEM", "Talia Fuentes", {7: 114940}, 114940)
    add(5, "REP", "Andy Biggs", {7: 205184}, 205184)
    add(6, "DEM", "W. John Williamson", {7: 122866}, 122866)
    add(6, "REP", "David Schweikert", {7: 201578}, 201578)
    add(7, "DEM", "Ruben Gallego", {7: 119465}, 119465)
    add(7, "GRN", "Neil B. Westbrooks", {7: 60}, 60, True)
    add(7, "REP", "Eve Nunez", {7: 39286}, 39286)
    add(8, "GRN", "Mark Salazar", {7: 93954}, 93954)
    add(8, "REP", "Trent Franks", {7: 204942}, 204942)
    add(8, "REP", "Hayden Keener III", {7: 75}, 75, True)
    add(9, "DEM", "Kyrsten Sinema", {7: 169055}, 169055)
    add(9, "GRN", "Cary Dolego", {7: 56}, 56, True)
    add(9, "REP", "Dave Giles", {7: 108350}, 108350)
    add(9, "IND", "Axel Bello", {7: 46}, 46, True)
    # Original official statewide XML provides the actual 2020 county records.
    counties = [
        "Apache",
        "Cochise",
        "Coconino",
        "Gila",
        "Graham",
        "Greenlee",
        "La Paz",
        "Maricopa",
        "Mohave",
        "Navajo",
        "Pima",
        "Pinal",
        "Santa Cruz",
        "Yavapai",
        "Yuma",
    ]
    with zipfile.ZipFile(
        ROOT / "data/raw/us-senate/az-2020-general-results-detail.xml.zip"
    ) as z:
        root = E.fromstring(z.read(z.namelist()[0]))
    by_year[2020] = []
    for contest in root.findall("contests/contest"):
        m = re.fullmatch(
            r"U.S. Representative in Congress - District No. (\d)",
            contest.get("contestLongName", ""),
        )
        if not m:
            continue
        d = int(m[1])
        participating = {
            u.attrib["name"]
            for u in contest.findall("participatingJurisdictions/jurisdiction")
        }
        for choice in contest.findall("choices/choice"):
            votes = {
                r.attrib["name"]: int(r.attrib["votes"])
                for r in choice.findall("jurisdictions/jurisdiction")
            }
            assert set(votes) == participating
            last, first = choice.attrib["choiceName"].split(", ", 1)
            name = first + " " + last
            row = {
                "district": d,
                "party": choice.attrib["party"].upper(),
                "name": name,
                "write_in": choice.attrib["isWriteIn"] == "true",
                "cells": [votes.get(n, "NA") for n in counties],
                "official_total": int(choice.attrib["totalVotes"]),
            }
            assert votes["State"] == row["official_total"]
            by_year[2020].append(row)
    # Keep original 2014 canvass values for audit, then apply only the court's two recounted candidates.
    original_2014 = json.loads(json.dumps(by_year[2014]))
    for row in by_year[2014]:
        if row["district"] == 2 and row["name"] in ["Ron Barber", "Martha McSally"]:
            a, b, total = (
                (14677, 94870, 109547)
                if row["name"] == "Ron Barber"
                else (21737, 87977, 109714)
            )
            row["cells"][1] = a
            row["cells"][10] = b
            row["official_total"] = total
            row["source_id"] = "house-2014-recount"
    # Correct the indexed D9 column reconstruction using actual county precinct records.
    county_2024 = collections.defaultdict(int)
    with zipfile.ZipFile(p / "2024-openelections.zip") as z:
        for member in z.namelist():
            for row in csv.DictReader(io.StringIO(z.read(member).decode("utf-8-sig"))):
                if row["office"] != "U.S. House":
                    continue
                match_district = re.search(r"\d+", row["district"])
                if not match_district:
                    assert row["candidate"] in [
                        "Write-In Totals",
                        "Total Votes",
                        "Overvotes",
                        "Undervotes",
                    ], row
                    continue
                district = int(match_district[0])
                name = " ".join(sorted(name_tokens(row["candidate"])))
                value = row["votes"].strip().replace(",", "")
                if not re.fullmatch(r"\d+", value):
                    raise ValueError(("Invalid source votes", member, row))
                county_2024[(district, row["county"], name)] += int(value)
    for row in by_year[2024]:
        if row["district"] != 9:
            continue
        original = list(row["cells"])
        key = " ".join(sorted(name_tokens(row["name"])))
        cells = [county_2024.get((9, n, key), "NA") for n in counties]
        assert sum(v for v in cells if isinstance(v, int)) == row["official_total"], (
            row["name"],
            cells,
        )
        row["cells"] = cells
        row["source_id"] = "house-2024-openelections"
    return by_year
