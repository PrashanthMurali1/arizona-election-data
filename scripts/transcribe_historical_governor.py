"""Rebuild the 1966-1990 Governor transcriptions and provenance.

County cells are transcribed from saved copies of RightDataUSA's county results pages, a secondary
source: the official Secretary of State canvasses were not available to this project, so none of
these elections is marked verified. Each candidate's county cells are checked against the statewide
total printed on the page, the page's county TOTAL column where it is fully visible, and the
statewide totals Wikipedia lists (citing the official canvass). RightDataUSA's "Other" column is one
aggregate row; Wikipedia's itemized write-ins add up to it exactly where they are listed.
"""

import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.normalize import COUNTIES

RAW = ROOT / "data/raw/governor-historical"
GEOIDS_15 = [g for g, _ in COUNTIES]
# La Paz County was created in 1983; earlier elections report 14 counties (Yuma includes today's La Paz).
GEOIDS_14 = [g for g in GEOIDS_15 if g != "04012"]
FIRST_15_COUNTY_YEAR = 1986

DATES = {1966: "1966-11-08", 1970: "1970-11-03", 1974: "1974-11-05", 1978: "1978-11-07", 1982: "1982-11-02", 1986: "1986-11-04", 1990: "1990-11-06"}
OTHER = "Unattributed write-ins"

# (party, name, write_in, county cells in printed order, printed statewide total, category)
ROWS = {
    1966: [
        ("REP", "Jack Williams", False, [1458, 5820, 4465, 3532, 1955, 1020, 124183, 1881, 3841, 35901, 6087, 1088, 7116, 5091], 203438),
        ("DEM", "Sam Goddard", False, [1743, 7094, 3403, 5028, 2188, 2423, 87449, 1704, 3198, 41657, 7292, 1720, 4384, 5621], 174904),
    ],
    1970: [
        ("REP", "Jack Williams", False, [1745, 5712, 4305, 2951, 2078, 822, 133336, 2846, 4335, 32750, 5786, 824, 7052, 4814], 209356),
        ("DEM", "Raul Castro", False, [1684, 8138, 4471, 4907, 2343, 2239, 96525, 2797, 3330, 55245, 7861, 2123, 4093, 6297], 202053),
    ],
    1974: [
        ("DEM", "Raul Castro", False, [4482, 8779, 9601, 5056, 2379, 2262, 139222, 4623, 6440, 70919, 9405, 2238, 7148, 5821], 278375),
        ("REP", "Russell Williams", False, [2003, 7695, 6483, 4015, 2772, 1397, 171111, 4449, 4899, 43962, 7235, 1134, 9432, 7087], 273674),
        ("NONE", OTHER, True, [0, 2, 1, 1, 0, 0, 139, 7, 0, 0, 0, 0, 3, 0], 153, "aggregate_write_in"),
    ],
    1978: [
        ("DEM", "Bruce Babbitt", False, [4498, 8963, 10446, 5715, 2565, 2229, 141177, 6042, 6269, 67904, 9064, 2814, 8386, 6533], 282605),
        ("REP", "Evan Mecham", False, [1761, 6251, 4411, 3668, 3085, 917, 151079, 6133, 4518, 36197, 7151, 1229, 8978, 5715], 241093),
        ("LBT", "V. Gene Lewter", False, [196, 94, 388, 160, 63, 31, 6982, 277, 179, 1165, 284, 33, 408, 161], 10421),
        ("SWP", "Jessica Sampson", False, [169, 157, 176, 80, 63, 42, 2291, 74, 136, 785, 158, 45, 126, 135], 4437),
    ],
    1982: [
        ("DEM", "Bruce Babbitt", False, [6584, 13196, 14773, 7343, 4127, 2578, 228217, 10533, 8566, 113982, 14527, 3519, 14339, 11511], 453795),
        ("REP", "Leo Corbet", False, [2723, 6082, 4997, 3645, 2123, 580, 142938, 6617, 4611, 38235, 5882, 1098, 9930, 6416], 235877),
        ("LBT", "Sam Steiger", False, [546, 815, 1643, 769, 399, 125, 20457, 1033, 759, 5873, 1076, 161, 2127, 866], 36649),
        ("IND", "Frank Henry Beversdorf, Sr.", True, [0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0], 2),
        ("REP", "Dave Duncan", True, [0, 0, 4, 0, 0, 0, 18, 0, 5, 0, 0, 0, 1, 0], 28),
        ("NONE", "Sandy Greeneltch", True, [0, 0, 2, 0, 0, 0, 4, 0, 1, 2, 1, 0, 1, 2], 13),
    ],
    1986: [
        ("REP", "Evan Mecham", False, [2965, 8484, 6647, 4779, 3257, 991, 1352, 213049, 9333, 6250, 56598, 8244, 1490, 15000, 5474], 343913),
        ("DEM", "Carolyn Warner", False, [6936, 8368, 11492, 5775, 2381, 1218, 1201, 142540, 7969, 7527, 72366, 11127, 2349, 10288, 7449], 298986),
        ("IND", "Bill Schulz", False, [1279, 5174, 5565, 3319, 1272, 772, 915, 139231, 4300, 2769, 42700, 5347, 1464, 6688, 3290], 224085),
    ],
    1990: [
        ("REP", "Fife Symington", False, [3638, 11472, 11330, 6283, 3614, 1071, 1829, 330261, 14068, 7708, 87701, 11762, 2140, 22682, 8425], 523984),
        ("DEM", "Terry Goddard", False, [9485, 12685, 17050, 7893, 3699, 1836, 1622, 282409, 13131, 9867, 112572, 16562, 3801, 17567, 9512], 519691),
        ("SAB", "Max Hawkins", True, [91, 136, 123, 128, 141, 11, 33, 8156, 154, 204, 1028, 257, 10, 467, 44], 10983),
        ("IND", "Rick Lee Campbell", True, [8, 8, 5, 4, 0, 0, 1, 97, 18, 4, 10, 4, 2, 1, 1], 163),
        ("REP", "Patrick P. Castronovo", True, [0, 3, 0, 0, 0, 0, 0, 53, 8, 2, 6, 0, 0, 1, 2], 75),
        ("NONE", "Peter J. Cojanis", True, [0, 0, 0, 0, 0, 0, 0, 19, 10, 0, 24, 0, 0, 1, 0], 54),
        ("IND", "Allen Weinstein", True, [1, 1, 2, 4, 0, 0, 0, 22, 4, 0, 40, 1, 1, 0, 0], 76),
        ("NON", "Robert B. Winn", True, [5, 2, 1, 0, 0, 0, 1, 43, 1, 5, 3, 2, 0, 1, 0], 64),
        ("LBT", "Ed Yetman", True, [6, 13, 11, 5, 2, 0, 1, 139, 11, 9, 94, 9, 2, 11, 3], 316),
    ],
}

# RightDataUSA's printed county TOTAL column (only for years not covered by an official canvass); 1978's is cut off at the page edge in the saved copy.
COUNTY_TOTALS = {
    1966: [3201, 12914, 7868, 8560, 4143, 3443, 211632, 3585, 7039, 77558, 13379, 2808, 11500, 10712],
    1970: [3429, 13850, 8776, 7858, 4421, 3061, 229861, 5643, 7665, 87995, 13647, 2947, 11145, 11111],
    1974: [6485, 16476, 16085, 9072, 5151, 3659, 310472, 9079, 11339, 114881, 16640, 3372, 16583, 12908],
    1982: [9853, 20093, 21419, 11757, 6649, 3283, 391635, 18183, 13943, 158092, 21486, 4778, 26398, 18795],
    1986: [11180, 22026, 23704, 13873, 6910, 2981, 3468, 494820, 21602, 16546, 171664, 24718, 5303, 31976, 16213],
}
# (RightDataUSA's 1990 Goddard cell for Gila read 7,693; the official canvass prints 7,893, which closes its 200-vote gap.)
KNOWN_COUNTY_DIFFERENCES = {}

# Years checked against the official Secretary of State canvass (supplied by the project maintainer).
# page = printed page of the Governor contest. turnout = (registration, ballots cast, percent) per county in
# printed order, then statewide, from page 1; 1986's turnout is already imported with that year's Senate contest.
OFFICIAL = {
    1978: dict(page=1, reported="1978-11-27", url="https://apps.azsos.gov/election/files/hist/canvass1978ge.pdf", turnout=(
        [14365, 26001, 28457, 15849, 9253, 5096, 543282, 20981, 19673, 197335, 29444, 6728, 28948, 24018, 969430],
        [7142, 15931, 15789, 9889, 5962, 3334, 307537, 12879, 11420, 108305, 17433, 4324, 18263, 12961, 551169],
        [49.72, 61.27, 55.48, 62.40, 64.43, 65.42, 56.61, 61.38, 57.79, 54.88, 59.21, 64.27, 63.09, 53.96, 56.85])),
    1982: dict(page=2, reported="1982-11-22", url="https://apps.azsos.gov/election/files/hist/canvass1982ge.pdf", turnout=(
        [16905, 29192, 35466, 17746, 9794, 4753, 623521, 28063, 21764, 245930, 33181, 7270, 38501, 28763, 1140849],
        [10450, 20610, 21949, 12030, 6825, 3382, 399987, 18946, 14352, 161060, 22114, 4994, 26994, 19230, 742923],
        [61.82, 70.60, 61.89, 67.79, 69.69, 71.16, 64.15, 67.51, 65.94, 65.49, 66.65, 68.69, 70.11, 66.86, 65.12])),
    1986: dict(page=2, reported="1986-11-24", url="https://apps.azsos.gov/election/files/hist/canvass1986ge.pdf", turnout=None),
    1990: dict(page=2, reported="1990-11-26", url="https://apps.azsos.gov/election/files/hist/canvass1990ge.pdf", turnout=(
        [26353, 45076, 55325, 23012, 12968, 4819, 7004, 1062231, 51747, 33794, 371146, 50816, 10805, 66671, 38189, 1859956],
        [14284, 25409, 29668, 15230, 7975, 3071, 3641, 640847, 28894, 18864, 208368, 29880, 6460, 43180, 18964, 1094735],
        [54.20, 56.37, 53.62, 66.18, 61.50, 63.73, 51.98, 60.33, 55.84, 55.82, 56.14, 58.80, 59.79, 64.77, 49.66, 58.86])),
}
# The 1978 canvass prints Navajo turnout as 57.79%, but its own 11,420 ballots / 19,673 registered is 58.05%
# (both columns sum to the printed totals); the printed percentage is kept as published.
PRINTED_PERCENT_EXCEPTIONS = {(1978, 8)}
TURNOUT_DEFINITION = "Official election-wide ballots cast, eligible registration and turnout percentage as printed on page 1 of the Secretary of State canvass."
PRINTED_STATE_TOTAL = {1966: 378342, 1970: 411409, 1974: 552202, 1978: 538556, 1982: 726364, 1986: 866984, 1990: 1055406}

# Wikipedia's general-election results (it cites the official canvass held by the Arizona State Library).
WIKIPEDIA = {
    1966: dict(canvass="https://azmemory.azlibrary.gov/nodes/view/102661", candidates={"Jack Williams": 203438, "Sam Goddard": 174904}, write_ins={}, total=378342),
    1970: dict(canvass="https://azmemory.azlibrary.gov/nodes/view/102665", candidates={"Jack Williams": 209356, "Raul Castro": 202053}, write_ins={}, total=411409),
    1974: dict(canvass="https://azmemory.azlibrary.gov/nodes/view/102669", candidates={"Raul Castro": 278375, "Russell Williams": 273674}, write_ins={"Russell Shaw": 149, "Harold Bates": 4}, total=552202),
    1978: dict(canvass="https://azmemory.azlibrary.gov/nodes/view/102673", candidates={"Bruce Babbitt": 282605, "Evan Mecham": 241093, "V. Gene Lewter": 10421, "Jessica Sampson": 4437}, write_ins={}, total=538556, name_note="RightDataUSA printed the Libertarian as Gene Lewster; the official canvass and Wikipedia print V. Gene Lewter."),
    1982: dict(canvass="https://azmemory.azlibrary.gov/nodes/view/102678", candidates={"Bruce Babbitt": 453795, "Leo Corbet": 235877, "Sam Steiger": 36649}, write_ins={"Dave Duncan": 28, "Sandy Greeneltch": 13, "Frank Henry Beversdorf, Sr.": 2}, total=726364),
    1986: dict(canvass="https://azmemory.azlibrary.gov/nodes/view/102682", candidates={"Evan Mecham": 343913, "Carolyn Warner": 298986, "Bill Schulz": 224085}, write_ins={}, total=866984),
    1990: dict(canvass="https://azmemory.azlibrary.gov/nodes/view/102686", candidates={"Fife Symington": 523984, "Terry Goddard": 519691, "Max Hawkins": 10983}, write_ins={"Ed Yetman": 316, "Rick Lee Campbell": 163, "Allen Weinstein": 76, "Patrick P. Castronovo": 75, "Robert B. Winn": 64, "Peter J. Cojanis": 54}, total=1055406, hawkins_note="Wikipedia lists Max Hawkins (Stop Abortion) as a write-in."),
}

RDU_URL = "https://www.rightdatausa.com/election_results?y={year}&t=G&r=N&s=AZ&d=all&WhichMap=vs"
WIKI_URL = "https://en.wikipedia.org/wiki/{year}_Arizona_gubernatorial_election"
WIKI_FILE = "wikipedia/{year}-arizona-gubernatorial-election.wikitext"
RETRIEVED = "2026-11-01"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def geoids(year):
    return GEOIDS_15 if year >= FIRST_15_COUNTY_YEAR else GEOIDS_14


def check(year):
    rows, units = ROWS[year], geoids(year)
    for party, name, write_in, county, state, *rest in rows:
        allowed = KNOWN_COUNTY_DIFFERENCES.get(year, {}).get(name, 0)
        if len(county) != len(units) or sum(county) - state != allowed:
            raise ValueError(f"{year} {name}: county cells {sum(county)} differ from printed total {state}")
    if sum(r[4] for r in rows) != PRINTED_STATE_TOTAL[year]:
        raise ValueError(f"{year}: candidate totals differ from the printed statewide TOTAL")
    if year in COUNTY_TOTALS:
        for i, printed in enumerate(COUNTY_TOTALS[year]):
            if sum(r[3][i] for r in rows) != printed:
                raise ValueError(f"{year} county column {i}: cells differ from the printed county TOTAL")
    turnout = OFFICIAL.get(year, {}).get("turnout")
    if turnout:
        reg, ballots, pct = turnout
        for label, values in (("registration", reg), ("ballots", ballots)):
            if sum(values[:-1]) != values[-1]:
                raise ValueError(f"{year} {label}: county sum differs from printed statewide total")
        for i, (r, b, pc) in enumerate(zip(reg, ballots, pct)):
            if (year, i) in PRINTED_PERCENT_EXCEPTIONS:
                continue
            if abs(round(b / r * 100, 2) - pc) > 0.011:
                raise ValueError(f"{year} turnout percent {pc} differs from ballots/registration")
    wiki = WIKIPEDIA[year]
    if sum(wiki["candidates"].values()) + sum(wiki["write_ins"].values()) != wiki["total"]:
        raise ValueError(f"{year}: Wikipedia candidate totals do not add up")


def wikipedia_comparison(year):
    wiki, rows = WIKIPEDIA[year], ROWS[year]
    ours = {r[1]: r[4] for r in rows}
    named = {name: dict(rightdatausa=ours.get(name), wikipedia=votes, match=ours.get(name) == votes) for name, votes in wiki["candidates"].items()}
    other = ours.get(OTHER)
    itemized = {n: dict(ours=ours.get(n), wikipedia=v, match=ours.get(n) == v) for n, v in wiki["write_ins"].items()} if other is None else None
    result = dict(
        canvass_cited_by_wikipedia=wiki["canvass"],
        named_candidates=named,
        rightdatausa_total=PRINTED_STATE_TOTAL[year],
        wikipedia_total=wiki["total"],
        totals_match=PRINTED_STATE_TOTAL[year] == wiki["total"],
        all_named_match=all(c["match"] for c in named.values()),
    )
    if itemized:
        result["write_ins"] = dict(itemized=itemized, match=all(i["match"] for i in itemized.values()))
    elif wiki["write_ins"] or other is not None:
        result["write_ins"] = dict(
            rightdatausa_other=other,
            wikipedia_itemized=wiki["write_ins"],
            wikipedia_itemized_sum=sum(wiki["write_ins"].values()),
            match=other == sum(wiki["write_ins"].values()),
        )
    for key in ("name_note", "hawkins_note"):
        if key in wiki:
            result[key] = wiki[key]
    return result


def write(year):
    check(year)
    rows, units = ROWS[year], geoids(year)
    csv_path = RAW / f"{year}-transcription.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["party", "name", "write_in", *units, "official_statewide", "category"])
        for party, name, write_in, county, state, *rest in rows:
            w.writerow([party, name, str(write_in).lower(), *county, state, rest[0] if rest else "named_candidate"])
    pdf = RAW / "pdfs" / f"rightdatausa-{year}-arizona-governor.pdf"
    wiki_path = RAW / WIKI_FILE.format(year=year)
    wiki = WIKIPEDIA[year]
    notes = (
        f"{year} regular Arizona gubernatorial election. NOT verified against an official canvass: the Secretary of State canvass was not available. "
        "County and statewide cells are transcribed from RightDataUSA's county results page (a secondary source, supplied as a saved copy). "
        "Every candidate's county cells sum to the statewide total printed on the page, the page's county TOTAL column agrees where it is visible, "
        "and the statewide totals match Wikipedia's results table (" + WIKI_URL.format(year=year) + "), which cites the official canvass. "
        + ("La Paz County did not exist until 1983, so results are for the 14 counties then in existence and Yuma is the larger pre-1983 Yuma County. " if year < FIRST_15_COUNTY_YEAR else "")
        + ("RightDataUSA reports write-ins only as one 'Other' total; it is shown as a single aggregate row. " if any(len(r) > 5 for r in rows) else "")
        + (f"Wikipedia itemizes those write-ins ({', '.join(f'{n} {v:,}' for n, v in wiki['write_ins'].items())}); they add up to the same total. " if wiki["write_ins"] else "")
        + (wiki.get("name_note", "") + " " if "name_note" in wiki else "")
        + (wiki.get("hawkins_note", "") + " " if "hawkins_note" in wiki else "")
        + (
            "The page's county cells for Terry Goddard sum to 519,491, 200 fewer than his statewide total of 519,691 (which matches Wikipedia); every county column agrees with the page's own county TOTALs, so the shortfall is in the source page and the county cells are shown as printed. "
            if year == 1990
            else ""
        )
        + f"Wikipedia cites the official canvass at {wiki['canvass']}. Turnout is not shown: RightDataUSA's turnout percentages are its own derived figures, not an official count."
    )
    prov = dict(
        year=year,
        election_date=DATES[year],
        contest_id=f"az-{year}-governor",
        contest_kind="regular",
        candidate_count=len(rows),
        expected_units=units,
        status_ceiling="secondary",
        reviewed_county_differences=KNOWN_COUNTY_DIFFERENCES.get(year, {}),
        source_id=f"rightdatausa-{year}-governor",
        source_title=f"RightDataUSA — {year} Gubernatorial Election Results for Arizona (county results)",
        source_url=RDU_URL.format(year=year),
        retrieved_on=RETRIEVED,
        retrieval_precision="date",
        source_notes=notes,
        additional_sources=[
            dict(
                id=f"wikipedia-{year}-arizona-governor",
                title=f"Wikipedia — {year} Arizona gubernatorial election (statewide cross-check)",
                url=WIKI_URL.format(year=year),
                sha256=sha(wiki_path),
                notes=f"Secondary source used only to cross-check statewide totals and itemize write-ins. It cites the official canvass at {wiki['canvass']}. Retrieved {RETRIEVED}.",
            )
        ],
        snapshots=[
            dict(path=csv_path.relative_to(ROOT).as_posix(), sha256=sha(csv_path)),
            dict(path=pdf.relative_to(ROOT).as_posix(), sha256=sha(pdf)),
            dict(path=wiki_path.relative_to(ROOT).as_posix(), sha256=sha(wiki_path)),
        ],
    )
    official = OFFICIAL.get(year)
    if official:
        canvass = RAW / "pdfs" / f"canvass{year}ge.pdf"
        notes = (
            f"{year} regular Arizona gubernatorial election. County and statewide cells transcribed from page {official['page']} of the official canvass issued by the Arizona Secretary of State "
            f"({official['reported']}); every candidate's county cells sum to the printed statewide TOTAL, and the statewide totals also match Wikipedia's results table ({WIKI_URL.format(year=year)}). "
            "Every cell was first transcribed from RightDataUSA's county page and then checked against the canvass"
            + (", which corrected one cell (Terry Goddard, Gila: 7,693 to 7,893) and closed the 200-vote gap on that page. " if year == 1990 else " with no differences. ")
            + ("La Paz County did not exist until 1983, so results are for the 14 counties then in existence and Yuma is the larger pre-1983 Yuma County. " if year < FIRST_15_COUNTY_YEAR else "")
            + ("Named write-ins are itemized as the canvass prints them. " if any(r[2] for r in rows) else "")
            + (wiki.get("name_note", "") + " " if "name_note" in wiki else "")
            + ("The canvass notes a runoff election was to be held under Arizona Constitution Art. V, Sec. 1 because no candidate won a majority; the runoff is not part of this general-election contest. " if year == 1990 else "")
            + ("The canvass prints Navajo County turnout as 57.79%, though its own ballots and registration give 58.05%; the printed percentage is kept as published. " if year == 1978 else "")
            + ("Election-wide registration and turnout are the official figures already imported with the same election's Senate canvass. " if not official["turnout"] else "Election-wide registration, ballots cast and turnout are the official figures from page 1 of the canvass. ")
            + "The canvass PDF was supplied by the project maintainer and is retained with its SHA-256."
        )
        prov.pop("status_ceiling")
        prov.update(
            source_id=f"canvass-{year}-governor",
            source_title=f"Arizona Secretary of State — {year} official canvass",
            source_url=official["url"],
            reported_at=official["reported"],
            report_time_precision="date",
            canvass_page=official["page"],
            source_notes=notes,
        )
        prov["additional_sources"].append(dict(
            id=f"rightdatausa-{year}-governor",
            title=f"RightDataUSA — {year} Gubernatorial Election Results for Arizona (county results, comparison)",
            url=RDU_URL.format(year=year),
            sha256=sha(pdf),
            notes="Secondary compilation used for the first transcription and then checked cell by cell against the official canvass.",
        ))
        prov["snapshots"].insert(1, dict(path=canvass.relative_to(ROOT).as_posix(), sha256=sha(canvass)))
        if official["turnout"]:
            reg, ballots, pct = official["turnout"]
            tpath = RAW / f"{year}-turnout-transcription.csv"
            with tpath.open("w", encoding="utf-8", newline="") as f:
                w = csv.writer(f, lineterminator="\n")
                w.writerow(["geoid", "ballots_cast", "registered_voters", "percent"])
                for i, geoid in enumerate(units + ["04"]):
                    w.writerow([geoid, ballots[i], reg[i], f"{pct[i]:.2f}"])
            prov["snapshots"].append(dict(path=tpath.relative_to(ROOT).as_posix(), sha256=sha(tpath)))
            prov.update(turnout_path=tpath.relative_to(ROOT).as_posix(), turnout_definition=TURNOUT_DEFINITION)
    (RAW / f"{year}-provenance.json").write_text(json.dumps(prov, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(year, "retained", len(rows), "candidates,", len(units), "counties")


def main():
    for year in sorted(ROWS):
        write(year)
    out = ROOT / "data/processed/governor-historical/validation/wikipedia-comparison.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({y: wikipedia_comparison(y) for y in sorted(ROWS)}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print("Wikipedia comparison written")


if __name__ == "__main__":
    main()
