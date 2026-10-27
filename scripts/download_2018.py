"""Reacquire the retained public 2018 inputs, validating their recorded checksums.

The official PDF can be manually saved under data/raw/2018 for further auditing;
normal imports use the retained sources and never depend on live PDF access.
"""

import argparse
import hashlib
import json
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "data/raw/2018"
DOWNLOADS = {
    "az_2018.zip": "https://election.lab.ufl.edu/data-downloads/resultsdata/2018/precinct/az_2018.zip",
    "openelections-county.csv": "https://raw.githubusercontent.com/openelections/openelections-data-az/5675ad1dbf77ce24fdd320127215f81b17e1a866/2018/20181106__az__general__county.csv",
    "vest-documentation.txt": "https://election.lab.ufl.edu/data-downloads/resultsdata/2018/precinct/documentation.txt",
    "yavapai-write-ins.pdf": "https://www.yavapaivotes.gov/files/assets/elections/v/1/documents/results/2018/november-6-2018-election-generalgeneral_2018_write-in_ballot_results.pdf",
}


def download():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--try-official",
        action="store_true",
        help="Also try the official PDF if not locally available",
    )
    args = parser.parse_args()
    SOURCE_DIR.mkdir(exist_ok=True)
    source = next(
        s
        for s in json.loads((ROOT / "data/raw/source-manifest.json").read_text())[
            "sources"
        ]
        if s["year"] == 2018
    )
    expected = {Path(s["path"]).name: s["sha256"] for s in source["snapshots"]}
    if args.try_official:
        pdfs = [
            p for p in SOURCE_DIR.glob("*.pdf") if p.name != "yavapai-write-ins.pdf"
        ]
        if pdfs:
            print("Local PDF available for auditing:", ", ".join(p.name for p in pdfs))
        else:
            try:
                r = requests.get(source["url"], timeout=30)
                r.raise_for_status()
                if not r.content.startswith(b"%PDF"):
                    raise ValueError("Official endpoint did not return a PDF")
                (SOURCE_DIR / "official-canvass.pdf").write_bytes(r.content)
                print(
                    "Official canvass downloaded; review before changing retained references."
                )
            except (requests.RequestException, ValueError) as e:
                print(
                    "Official PDF unavailable:",
                    e,
                    "\nUsing documented alternative inputs.",
                )
    for name, url in DOWNLOADS.items():
        path = SOURCE_DIR / name
        payload = path.read_bytes() if path.exists() else requests.get(url, timeout=45)
        if not isinstance(payload, bytes):
            payload.raise_for_status()
            payload = payload.content
        if hashlib.sha256(payload).hexdigest() != expected[name]:
            raise ValueError(
                f"Checksum differs for {name}; no source snapshot was overwritten. Investigate the release before updating provenance."
            )
        if not path.exists():
            path.write_bytes(payload)
        print(name, "checksum verified")


if __name__ == "__main__":
    download()
