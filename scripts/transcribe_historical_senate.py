"""Rebuild the reviewed 1986-2012 U.S. Senate transcriptions, turnout tables and provenance.

County cells are the printed Arizona Secretary of State canvass cells for every year
(county order as printed), except 1988, whose degraded scan keeps statewide totals and
turnout only. OpenElections (2000-2012) and the FEC (2004) are used as cross-checks.
Every candidate's county cells are checked against the printed statewide TOTAL.
"""

import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.normalize import COUNTIES

RAW = ROOT / "data/raw/us-senate"
GEOIDS = [g for g, _ in COUNTIES]
NAMES = [n for _, n in COUNTIES]
Z = None  # statewide-only sources publish no county cells

DATES = {1986: "1986-11-04", 1988: "1988-11-08", 1992: "1992-11-03", 1994: "1994-11-08", 1998: "1998-11-03", 2000: "2000-11-07", 2004: "2004-11-02", 2006: "2006-11-07", 2010: "2010-11-02", 2012: "2012-11-06"}

# (party, name, write_in, [15 county cells in printed order], printed statewide, category)
ROWS = {
    1994: [
        ("DEM", "Sam Coppersmith", False, [10819, 10352, 14962, 6231, 2771, 1258, 1339, 228021, 11314, 10107, 105127, 13815, 3712, 15216, 7466], 442510),
        ("REP", "Jon Kyl", False, [5321, 14216, 14571, 7748, 4607, 1473, 2061, 362348, 19005, 10891, 100970, 14538, 2601, 28374, 12275], 600999),
        ("LBT", "Scott Grainger", False, [710, 1746, 2355, 1104, 341, 124, 257, 45998, 2151, 1023, 11628, 2145, 317, 4552, 1042], 75493),
        ("NONE", "Mark Pope", True, [2, 0, 4, 1, 0, 0, 0, 35, 4, 2, 3, 5, 0, 2, 0], 58),
    ],
    1998: [
        ("DEM", "Ed Ranger", False, [6494, 7055, 9046, 4465, 2043, 916, 865, 147017, 7988, 6454, 54503, 9455, 2154, 10799, 5970], 275224),
        ("IND", "Bill Reilly", True, [7, 0, 38, 3, 1, 0, 0, 102, 3, 6, 13, 3, 0, 11, 0], 187),
        ("LBT", "John C. Zajac", False, [354, 497, 944, 397, 106, 35, 60, 13411, 762, 408, 3744, 503, 127, 1353, 303], 23004),
        ("RPA", "Bob Park", False, [249, 283, 524, 186, 71, 16, 52, 11620, 417, 274, 2386, 524, 89, 1133, 464], 18288),
        ("REP", "John McCain", False, [8340, 17351, 17267, 8748, 5215, 1805, 2330, 400901, 20086, 13131, 132439, 17848, 3427, 34926, 12763], 696577),
    ],
    2000: [
        ("GRN", "Vance Hansen", False, [1890, 2255, 6189, 819, 328, 93, 190, 49107, 1980, 1627, 35081, 2145, 707, 5334, 1181], 108926),
        ("IND", "William Toel", False, [2376, 2128, 3297, 1384, 585, 256, 342, 68387, 4309, 2070, 12687, 3716, 853, 4647, 2193], 109230),
        ("LBT", "Barry J. Hess, II", False, [2011, 1752, 2887, 941, 375, 143, 228, 36847, 1972, 1835, 15280, 2183, 563, 2541, 1166], 70724),
        ("REP", "Jon Kyl", False, [9857, 24766, 25512, 13549, 7520, 2135, 3484, 663756, 32686, 18671, 198266, 30134, 5753, 50815, 21292], 1108196),
    ],
    2006: [
        ("DEM", "Jim Pederson", False, [11402, 14849, 20610, 6643, 2194, 942, 1457, 364661, 16998, 11785, 144275, 24790, 4892, 26340, 12303], 664141),
        ("LBT", "Richard Mack", False, [831, 1302, 1448, 533, 516, 119, 173, 26733, 1981, 951, 7936, 1836, 197, 2849, 826], 48231),
        ("REP", "Jon Kyl", False, [6530, 20194, 16003, 9512, 5127, 1068, 2203, 491721, 26964, 13927, 128987, 30379, 3067, 43219, 15497], 814398),
        ("NONE", "Stephen Baker", True, [0, 0, 1, 0, 0, 0, 0, 2, 1, 0, 3, 0, 0, 0, 0], 7),
        ("NONE", "Ray Caplette", True, [0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 1, 0, 0, 0, 2], 5),
    ],
    2010: [
        ("DEM", "Rodney Glassman", False, [11785, 13119, 17164, 4858, 2194, 947, 1085, 319012, 12302, 10737, 134296, 24856, 5710, 21636, 12310], 592011),
        ("GRN", "Jerry Joslyn", False, [358, 645, 781, 246, 118, 22, 77, 12095, 960, 430, 5929, 1062, 154, 1324, 402], 24603),
        ("LBT", "David F. Nolan", False, [925, 2352, 1631, 1039, 493, 115, 295, 45596, 3638, 1672, 12538, 3714, 324, 4306, 1459], 80097),
        ("REP", "John McCain", False, [7371, 23445, 18995, 11500, 6223, 1321, 3003, 599068, 36367, 16157, 158879, 47850, 3693, 52093, 19650], 1005615),
        ("NONE", "Ray J. Caplette", True, [0, 0, 0, 0, 0, 0, 0, 5, 0, 0, 1, 1, 0, 0, 0], 7),
        ("NONE", "Santos Chavez", True, [4, 1, 2, 0, 0, 0, 0, 16, 0, 1, 6, 1, 0, 8, 0], 39),
        ("NONE", "Sydney Dudikoff", True, [1, 0, 1, 0, 0, 0, 0, 9, 0, 0, 2, 0, 0, 1, 0], 14),
        ("NONE", "Loyd Ellis", True, [3, 9, 2, 2, 0, 0, 0, 95, 9, 1, 22, 7, 0, 7, 3], 160),
        ("NONE", "Ian Gilyeat", True, [109, 44, 48, 55, 25, 13, 3, 4070, 53, 225, 72, 307, 13, 888, 13], 5938),
    ],
    2012: [
        ("DEM", "Richard Carmona", False, [16455, 19736, 28723, 8099, 3771, 1342, 1961, 602809, 20865, 16881, 207578, 45558, 9454, 34902, 18408], 1036542),
        ("IND", "Don Manspeaker", True, [0, 6, 2, 1, 0, 0, 0, 10, 0, 0, 5, 0, 0, 0, 0], 24),
        ("IND", "Steven Watts", True, [0, 5, 8, 4, 4, 0, 0, 201, 10, 3, 29, 8, 0, 17, 1], 290),
        ("LBT", "Marc Victor", False, [1097, 2266, 2580, 1135, 570, 205, 426, 62546, 4822, 1631, 12304, 5885, 437, 5114, 1091], 102109),
        ("REP", "Jeff Flake", False, [7680, 26208, 19334, 11954, 7352, 1365, 3120, 675500, 42410, 18228, 153846, 55008, 3617, 57838, 20997], 1104457),
    ],
    2004: [
        ("DEM", "Stuart Starky", False, [9588, 9555, 13520, 4291, 2000, 746, 965, 216124, 10423, 7434, 89483, 13595, 3583, 14852, 8348], 404507),
        ("LBT", "Ernest Hancock", False, [905, 1394, 1504, 632, 322, 68, 156, 29769, 1686, 1222, 7980, 1692, 252, 3160, 1056], 51798),
        ("REP", "John McCain", False, [12923, 32879, 35849, 15551, 8171, 2166, 3826, 917527, 44402, 23091, 258010, 48094, 7502, 67312, 28069], 1505372),
    ],
    1986: [
        ("DEM", "Richard Kimball", False, [6486, 9711, 10702, 6799, 2903, 1619, 1398, 168182, 7809, 6956, 85057, 11975, 2755, 11745, 6868], 340965),
        ("REP", "John McCain", False, [4682, 12199, 12774, 6960, 4002, 1348, 2049, 324826, 13431, 9520, 85652, 12396, 2389, 20042, 9580], 521850),
        ("NONE", "Paul Rodriguez", True, [21, 0, 2, 4, 4, 0, 0, 21, 2, 0, 1, 0, 5, 0, 0], 60),
        ("NONE", "Robert B. Winn", True, [12, 0, 1, 1, 0, 0, 0, 7, 2, 0, 0, 0, 5, 0, 0], 28),
        ("NONE", "David Zilly", True, [7, 0, 2, 0, 0, 0, 0, 6, 0, 0, 0, 0, 3, 0, 0], 18),
    ],
    # 1988: the Secretary of State scan is too degraded to read every county cell, so the county cells come from
    # RightDataUSA (see write()); each candidate's 15 cells sum exactly to the printed statewide total.
    1988: [
        ("DEM", "Dennis DeConcini", False, [10871, 19002, 21203, 9770, 5603, 2551, 2292, 340814, 15142, 12439, 163100, 19082, 4817, 21460, 12257], 660403),
        ("REP", "Keith DeGreen", False, [3318, 8604, 9644, 5327, 3084, 796, 2017, 319561, 12657, 7043, 64220, 9906, 1702, 20382, 9799], 478060),
        ("LBT", "Rick Tompkins", False, [307, 610, 1066, 315, 113, 32, 90, 11840, 576, 315, 3583, 507, 105, 1056, 334], 20849),
        ("NAP", "Ed Finkelstein", False, [106, 121, 184, 74, 31, 8, 14, 2641, 91, 80, 1481, 133, 42, 139, 50], 5195),
        ("NONE", "Unattributed write-ins", True, [0, 1, 1, 0, 0, 0, 0, 18, 3, 0, 9, 0, 0, 0, 0], 32, "aggregate_write_in"),
    ],
    1992: [
        ("DEM", "Claire Sargent", False, [8543, 10304, 14414, 6011, 2659, 1375, 1465, 234584, 12513, 7949, 95789, 12011, 2614, 17073, 9017], 436321),
        ("REP", "John McCain", False, [7564, 19166, 23766, 9007, 4766, 2086, 2641, 443607, 21190, 12601, 153015, 19095, 4591, 32053, 16247], 771395),
        ("LBT", "Kiana Delamare", False, [324, 399, 930, 260, 111, 50, 49, 13651, 600, 338, 3779, 417, 136, 1225, 344], 22613),
        ("NAP", "Ed Finkelstein", False, [166, 85, 210, 129, 31, 10, 14, 3998, 200, 104, 807, 186, 26, 241, 128], 6335),
        ("IND", "Evan Mecham", False, [1469, 2903, 2477, 2939, 2160, 436, 740, 94808, 5266, 3505, 13802, 4795, 402, 7933, 1726], 145361),
        ("IND", "Robert B. Winn", True, [15, 0, 0, 0, 0, 0, 1, 1, 2, 1, 2, 1, 1, 0, 2], 26),
    ],
}

# Official election-wide registration, ballots cast and turnout (canvass page 1), county order as printed.
TURNOUT = {
    2004: (
        [39789, 59531, 71935, 26768, 14782, 4519, 7235, 1552421, 95034, 57738, 448050, 91093, 20791, 99842, 53803, 2643331],
        [24335, 44852, 52541, 21158, 10779, 3114, 5105, 1211963, 58353, 32609, 369321, 65154, 11810, 88076, 38899, 2038069],
        [61.16, 75.34, 73.04, 79.04, 72.92, 68.91, 70.56, 78.07, 61.40, 56.48, 82.43, 71.52, 56.80, 88.22, 72.30, 77.10],
    ),
    # 1986 prints the percentage as a fraction (0.5133); stored as a percentage.
    1986: (
        [23653, 41830, 45624, 22521, 11683, 5523, 6765, 899405, 42206, 31334, 329257, 45102, 9672, 50236, 33123, 1597934],
        [12142, 22808, 24504, 14423, 7185, 3072, 3618, 506106, 22296, 17135, 175363, 25520, 5570, 32855, 17071, 889668],
        [51.33, 54.53, 53.71, 64.04, 61.50, 55.62, 53.48, 56.27, 52.83, 54.69, 53.26, 56.58, 57.59, 65.40, 51.54, 55.68],
    ),
    # 1988 percentages are not legible in the scan; they are computed below from the printed ballots and registration.
    1988: (
        [24330, 45168, 51915, 22408, 12833, 5047, 7367, 1016585, 46760, 33059, 374622, 48453, 10389, 61382, 37396, 1797714],
        [15419, 29193, 33278, 16109, 9213, 3529, 4597, 696398, 29497, 20681, 240653, 30525, 7056, 44761, 23266, 1204175],
        [],
    ),
    1992: (
        [28397, 44985, 54649, 24311, 12883, 5108, 6557, 1147672, 55009, 36431, 375942, 51143, 11268, 70202, 40392, 1964949],
        [18973, 34012, 43501, 19026, 10077, 4111, 5109, 890680, 41732, 25432, 287718, 38230, 8355, 60356, 28964, 1516276],
        [66.81, 75.61, 79.60, 78.26, 78.22, 80.48, 77.92, 77.61, 75.86, 69.81, 76.53, 74.75, 74.15, 85.97, 71.71, 77.17],
    ),
    2000: (
        [39103, 54500, 66731, 29368, 14902, 5143, 7136, 1226317, 75257, 50150, 371696, 73968, 16514, 93291, 49046, 2173122],
        [19634, 34548, 42320, 18612, 9767, 3083, 4688, 914952, 45558, 26625, 289193, 42665, 9445, 68682, 29748, 1559520],
        [50.21, 63.39, 63.42, 63.38, 65.54, 59.95, 65.70, 74.61, 60.54, 53.09, 77.80, 57.68, 57.19, 73.62, 60.65, 71.76],
    ),
    2012: (
        [45868, 80372, 69598, 32161, 17252, 4362, 9757, 1817832, 115510, 59547, 495647, 153056, 24062, 124156, 75532, 3124712],
        [26226, 49554, 52243, 21823, 11991, 3035, 5808, 1390836, 71203, 37804, 385725, 109470, 14072, 101268, 42521, 2323579],
        [57.18, 61.66, 75.06, 67.86, 69.50, 69.58, 59.53, 76.51, 61.64, 63.49, 77.82, 71.52, 58.48, 81.57, 56.30, 74.36],
    ),
}

TURNOUT[1988] = (*TURNOUT[1988][:2], [round(b / r * 100, 2) for r, b in zip(*TURNOUT[1988][:2])])

FEC_2004_SHA = "e0d1ca80bc88d1b3fb3167d0ac653d9428675f39ce51f08f1538e9428ef34530"

CANVASS = {
    2004: dict(url="https://apps.azsos.gov/election/2004/General/Canvass2004General.pdf", page=3, reported="2004-11-22T14:00:00-07:00", precision="datetime", pdf="Canvass2004General.pdf"),
    1986: dict(url="https://apps.azsos.gov/election/files/hist/canvass1986ge.pdf", page=1, reported="1986-11-24", precision="date", pdf="canvass1986ge.pdf"),
    1988: dict(url="https://apps.azsos.gov/election/files/hist/canvass1988ge.pdf", page=3, reported="1989-01-13", precision="date", pdf="canvass1988ge.pdf"),
    1992: dict(url="https://apps.azsos.gov/election/files/hist/canvass1992ge.pdf", page=3, reported="1992-11-23", precision="date", pdf="canvass1992ge.pdf"),
    1994: dict(url="https://apps.azsos.gov/election/files/hist/canvass1994ge.pdf", page=1, reported="1994-11-28", precision="date", pdf="canvass1994ge.pdf"),
    1998: dict(url="https://apps.azsos.gov/election/1998/General/Canvass1998GE.pdf", page=1, reported="1998-11-23T09:59:00-07:00", precision="datetime", pdf="Canvass1998GE.pdf"),
    2000: dict(url="https://apps.azsos.gov/election/2000/General/Canvass2000GE.pdf", page=3, reported="2000-11-27T11:13:00-07:00", precision="datetime", pdf="Canvass2000GE.pdf"),
    2006: dict(url="https://apps.azsos.gov/election/2006/General/Canvass2006GE.pdf", page=1, reported="2006-12-04T13:16:00-07:00", precision="datetime", pdf="Canvass2006GE.pdf"),
    2010: dict(url="https://apps.azsos.gov/election/2010/General/Canvass2010GE.pdf", page=1, reported="2010-11-29T11:00:00-07:00", precision="datetime", pdf="Canvass2010GE.pdf"),
    2012: dict(url="https://apps.azsos.gov/election/2012/General/Canvass2012GE.pdf", page=4, reported="2012-12-03T10:00:00-07:00", precision="datetime", pdf="Canvass2012GE.pdf"),
}
RDU_1988_URL = "https://www.rightdatausa.com/election_results?y=1988&t=S1&r=N&s=AZ&d=all&WhichMap=vs"
RDU_1988_PDF = "rightdatausa-1988-arizona-senate.pdf"
CLERK = {1986: "Corrected to May 29, 1987", 1988: "Corrected to April 20, 1989", 1992: "Corrected to May 31, 1993"}  # cross-check publication notes
OPENELECTIONS = "data/raw/us-senate/openelections-senate-2000-2012.csv"
OE_COMMIT = "bf14331521f62f74cb17848ab11ca3dfd27f4f82"
DEFINITION = "Official election-wide ballots cast, eligible registration and turnout percentage as printed on page 1 of the Secretary of State canvass."
PDF_NOTE = "The canvass PDF was supplied by the project maintainer from the Secretary of State and is retained under data/raw/us-senate/pdfs with its SHA-256 recorded in the snapshots."


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def oe_rows():
    with (ROOT / OPENELECTIONS).open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def rows_for(year):
    return ROWS[year]


def check(year, rows):
    for party, name, write_in, county, state, *rest in rows:
        if county is not None and (len(county) != 15 or sum(county) != state):
            raise ValueError(f"{year} {name}: county cells {sum(county)} differ from printed total {state}")
    if year in TURNOUT:
        reg, ballots, pct = TURNOUT[year]
        for label, values in (("registration", reg), ("ballots", ballots)):
            if sum(values[:15]) != values[15]:
                raise ValueError(f"{year} {label}: county sum differs from printed statewide total")
        for r, b, p in zip(reg, ballots, pct):
            if abs(round(b / r * 100, 2) - p) > 0.011:
                raise ValueError(f"{year} turnout percent {p} differs from ballots/registration")


def openelections_comparison():
    reference = {}
    for r in oe_rows():
        reference[(int(r["year"]), r["county"], r["candidate"])] = int(r["votes"])
    report = {}
    for year in (2000, 2004, 2006, 2010, 2012):
        compared = mismatches = 0
        for party, name, write_in, county, state, *rest in ROWS[year]:
            for county_name, value in zip(NAMES, county):
                other = reference.get((year, county_name, name))
                compared += 1
                if other != value:
                    mismatches += 1
                    report.setdefault(year, {}).setdefault("mismatches", []).append({"candidate": name, "county": county_name, "canvass": value, "openelections": other})
        report.setdefault(year, {}).update({"cells_compared": compared, "mismatch_count": mismatches})
    return report


def write(year):
    rows = rows_for(year)
    check(year, rows)
    csv_path = RAW / f"{year}-transcription.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["party", "name", "write_in", *GEOIDS, "official_statewide", "category"])
        for party, name, write_in, county, state, *rest in rows:
            w.writerow([party, name, str(write_in).lower(), *(county if county else [""] * 15), state, rest[0] if rest else "named_candidate"])
    snapshots = [{"path": csv_path.relative_to(ROOT).as_posix(), "sha256": sha(csv_path)}]
    contest_id = f"az-{year}-us-senate"
    prov = {"year": year, "election_date": DATES[year], "contest_id": contest_id, "contest_kind": "regular", "candidate_count": len(rows)}
    if year in CANVASS:
        c = CANVASS[year]
        prov.update(
            source_id=f"canvass-{year}-us-senate",
            source_title=f"Arizona Secretary of State — {year} official U.S. Senate canvass",
            source_url=c["url"], reported_at=c["reported"], report_time_precision=c["precision"],
            retrieved_on="2026-11-01", retrieval_precision="date", canvass_page=c["page"],
            source_notes=(
                f"{year} regular Arizona U.S. Senate election. "
                + f"County cells and statewide totals transcribed from page {c['page']} of the official canvass "
                "issued by the Arizona Secretary of State; every candidate's 15 county cells sum to the printed statewide TOTAL. "
                + ("Cells were read from the printed page images. " if year in (1986, 1988, 1992, 1994, 2012) else "Cells were read from the document's text layer and checked against the page images. ")
                + "Named write-ins are included. "
                + PDF_NOTE
            ),
        )
        snapshots.append({"path": f"data/raw/us-senate/pdfs/{c['pdf']}", "sha256": sha(RAW / "pdfs" / c["pdf"])})
        if year in CLERK:
            prov["additional_sources"] = [{
                "id": f"clerk-{year}-us-senate", "title": f"Clerk of the U.S. House — Statistics of the Congressional Election of {year} (Arizona U.S. Senate; cross-check)",
                "url": f"https://clerk.house.gov/member_info/electionInfo/{year}election.pdf",
                "notes": f"Statewide candidate totals ({CLERK[year]}) agree with the Secretary of State canvass; the Clerk publication carries no county breakdown.",
            }]
        if year == 1988:
            rdu_pdf = RAW / "pdfs" / RDU_1988_PDF
            prov.update(
                source_id="rightdatausa-1988-us-senate",
                source_title="RightDataUSA — 1988 Senatorial Election Results for Arizona (county results)",
                source_url=RDU_1988_URL,
                turnout_source_id="canvass-1988-us-senate",
                source_notes=(
                    "1988 regular Arizona U.S. Senate election. The Secretary of State canvass scan is too degraded to read every county cell, so county results come from RightDataUSA's compilation "
                    "(a secondary source, supplied as a saved copy of its page). Each candidate's 15 county cells sum exactly to the official statewide total printed on page 3 of the Secretary of State canvass, "
                    "and every legible scan cell agrees, so the contest is shown as verified; the county source is secondary and is named as such. "
                    "Election-wide registration and ballots cast are the official figures from page 1 of the canvass (they sum to the printed statewide totals); "
                    "county turnout percentages are computed from them because the printed percentages are illegible. The write-in total is one aggregate row."
                ),
            )
            prov["additional_sources"] = [
                {"id": "canvass-1988-us-senate", "title": "Arizona Secretary of State — 1988 official canvass (statewide totals and turnout)", "url": c["url"],
                 "sha256": sha(RAW / "pdfs" / c["pdf"]), "notes": "Official statewide candidate totals (page 3) and election-wide registration and ballots cast (page 1)."},
                *prov["additional_sources"],
            ]
            snapshots.append({"path": rdu_pdf.relative_to(ROOT).as_posix(), "sha256": sha(rdu_pdf)})
        if year in (2000, 2004, 2006, 2010, 2012):
            prov["additional_sources"] = [{
                "id": f"openelections-us-senate-2000-2012", "title": "OpenElections Arizona — U.S. Senate county results, 2000–2012 (comparison)",
                "url": f"https://github.com/openelections/openelections-data-az/tree/{OE_COMMIT}", "sha256": sha(ROOT / OPENELECTIONS),
                "notes": "Independent open-data county results compiled from the official canvass; used only to cross-check the transcribed cells. See data/processed/us-senate/validation/openelections-comparison.json.",
            }]
        if year == 2004:
            prov["additional_sources"].append({
                "id": "fec-federal-elections-2004", "title": "Federal Election Commission — Federal Elections 2004: Election Results for the U.S. President, the U.S. Senate and the U.S. House of Representatives",
                "url": "https://www.fec.gov/resources/cms-content/documents/federalelections2004.pdf", "sha256": FEC_2004_SHA,
                "notes": "Statewide U.S. Senate totals for Arizona (McCain 1,505,372; Starky 404,507; Hancock 51,798) agree with the Secretary of State canvass.",
            })
        if year in TURNOUT:
            reg, ballots, pct = TURNOUT[year]
            turnout_path = RAW / f"{year}-turnout-transcription.csv"
            with turnout_path.open("w", encoding="utf-8", newline="") as f:
                w = csv.writer(f, lineterminator="\n")
                w.writerow(["geoid", "ballots_cast", "registered_voters", "percent"])
                for i, geoid in enumerate(GEOIDS + ["04"]):
                    w.writerow([geoid, ballots[i], reg[i], f"{pct[i]:.2f}"])
            snapshots.append({"path": turnout_path.relative_to(ROOT).as_posix(), "sha256": sha(turnout_path)})
            prov.update(turnout_path=turnout_path.relative_to(ROOT).as_posix(), turnout_definition=DEFINITION)
        else:
            prov["source_notes"] += " Event turnout is shared with the Governor and Attorney General contests of the same election."
    prov.update(snapshots=snapshots)
    prov_path = RAW / f"{year}-provenance.json"
    prov_path.write_text(json.dumps(prov, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(year, "retained", len(rows), "candidates")


def main():
    for year in sorted(ROWS):
        write(year)
    out = ROOT / "data/processed/us-senate/validation/openelections-comparison.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(openelections_comparison(), indent=2) + "\n", encoding="utf-8")
    print("OpenElections comparison written")


if __name__ == "__main__":
    main()
