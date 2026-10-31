"""Extract text-based official canvasses; fail closed on unexpected layouts."""

import hashlib, json, re, sys
from pathlib import Path
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
COUNTIES = [
    ("04001", "Apache"),
    ("04003", "Cochise"),
    ("04005", "Coconino"),
    ("04007", "Gila"),
    ("04009", "Graham"),
    ("04011", "Greenlee"),
    ("04012", "La Paz"),
    ("04013", "Maricopa"),
    ("04015", "Mohave"),
    ("04017", "Navajo"),
    ("04019", "Pima"),
    ("04021", "Pinal"),
    ("04023", "Santa Cruz"),
    ("04025", "Yavapai"),
    ("04027", "Yuma"),
]
URLS = {
    1994: "https://apps.azsos.gov/election/files/hist/canvass1994ge.pdf",
    **{y: f"https://apps.azsos.gov/election/{y}/General/Canvass{y}GE.pdf" for y in (1998, 2002, 2006, 2010)},
    2022: "https://apps.azsos.gov/election/2022/General/canvass/2022dec05_general_election_canvass_web.pdf",
    2018: "https://apps.azsos.gov/election/2018/2018_1203_signed_official_statewide_canvass.pdf",
    2014: "https://apps.azsos.gov/election/2014/general/Canvass2014GE.pdf",
}


def extract(year):
    path = ROOT / f"data/raw/{year}.pdf"
    pages = [p.extract_text() for p in PdfReader(path).pages]
    (ROOT / f"data/raw/{year}.txt").write_text("\n\n".join(pages))
    # Only the known 2022 layout is automated; historical layouts require review.
    if year != 2022:
        raise ValueError(
            "Historical text extracted; candidate-table review required before ingestion"
        )
    page = next(p for p in pages if "\nGovernor\n" in p)
    block = page.split("\nGovernor\n", 1)[1].split("* Winner")[0]
    matches = list(
        re.finditer(
            r"\((REP|DEM|LBT|NON|IND|GRN)\)\s*(.*?)\s+((?:[\d,]+\s+){15}[\d,]+)",
            block,
            re.S,
        )
    )
    if len(matches) != 9:
        raise ValueError(f"Expected 9 candidates, found {len(matches)}")
    candidates = []
    for i, match in enumerate(matches):
        party, name, numbers = match.groups()
        name = " ".join(name.replace("\x02", "-").split()).replace(" *", "")
        values = [int(n.replace(",", "")) for n in numbers.split()]
        candidates.append(
            dict(
                id=f"{year}-{i}",
                name=name,
                party=party,
                write_in="Write" in name,
                category="named_candidate",
                county_votes=dict(zip([c[0] for c in COUNTIES], values[:15])),
                statewide=values[15],
            )
        )
    turnout = {}
    for label, key, percent in [
        ("Total Eligible Registration", "registered_voters", False),
        ("Total Ballots Cast", "ballots_cast", False),
        ("Voter Turnout Percent", "percent", True),
    ]:
        line = next(l for l in pages[0].splitlines() if l.startswith(label))
        values = re.findall(r"[\d,]+(?:\.\d+)?%?", line[len(label) :])
        if len(values) != 16:
            raise ValueError(f"Invalid turnout row: {line}")
        for (geoid, _), value in zip(COUNTIES + [("04", "Arizona")], values):
            turnout.setdefault(geoid, {})[key] = (
                float(value.rstrip("%")) if percent else int(value.replace(",", ""))
            )
    return dict(
        year=year,
        date="2022-11-08",
        source_url=URLS[year],
        source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        source_notes="Official statewide canvass, December 5, 2022; governor page 2, turnout page 1.",
        candidates=candidates,
        turnout=turnout,
    )


if __name__ == "__main__":
    failed = False
    for year in [2022, 2018, 2014]:
        try:
            data = extract(year)
            (ROOT / f"data/processed/{year}.json").write_text(
                json.dumps(data, indent=2) + "\n"
            )
            print(year, "normalized")
        except Exception as e:
            print(year, ":", e)
            failed = True
    if failed:
        raise SystemExit(
            "One or more PDF sources could not be normalized; use reviewed source snapshots or resolve the reported extraction errors."
        )
