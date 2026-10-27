"""Strict readers for retained House canvass tables and official Clerk statistics."""

import hashlib
import html
import json
import re
import unicodedata
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
COUNTY_IDS = [
    "04001",
    "04003",
    "04005",
    "04007",
    "04009",
    "04011",
    "04012",
    "04013",
    "04015",
    "04017",
    "04019",
    "04021",
    "04023",
    "04025",
    "04027",
]


def table_events(text):
    def row(match):
        cells = re.findall(r"<t[dh](?:\s[^>]*)?>(.*?)</t[dh]>", match[0], re.S | re.I)
        cells = [
            " ".join(html.unescape(re.sub(r"<[^>]+>", "", c)).split()) for c in cells
        ]
        return "\nROW_JSON:" + json.dumps(cells) + "\n"

    text = re.sub(r"<tr(?:\s[^>]*)?>.*?</tr>", row, text, flags=re.S | re.I)
    text = html.unescape(re.sub(r"<[^>]+>", "", text))
    for line in text.splitlines():
        line = line.strip().replace("**", "")
        if line.startswith("ROW_JSON:"):
            yield json.loads(line[9:])
        elif line.startswith("|"):
            yield [c.strip() for c in line.strip("|").split("|")]
        elif line:
            yield [line]


def indexed_candidates(path):
    district = None
    output = []
    for row in table_events(path.read_text()):
        if not row:
            continue
        label = row[0]
        match = re.search(
            r"U\.S\.\s*REPRESENTATIVE\s+IN\s+CONGRESS\s*[-–—]\s*DISTRICT\s+NO\.\s*(\d)",
            label,
            re.I,
        )
        if match:
            district = int(match[1])
            continue
        if re.match(
            r"(?:Governor|Secretary of State|Attorney General|State Senator|State Representative|State Treasurer|Superintendent|Corporation Commissioner)",
            label,
            re.I,
        ):
            district = None
        candidate = re.fullmatch(r"\(([^)]+)\)\s*(.+)", label)
        if district is None or not candidate:
            continue
        if len(row) != 17:
            raise ValueError(f"Ambiguous candidate row length in {path}: {row}")
        party, name = candidate.groups()
        write_in = bool(re.search(r"\(Write[-\s]?In\)", name, re.I))
        name = re.sub(r"\(Write[-\s]?In\)", "", name, flags=re.I).rstrip(" *").strip()
        values = []
        for cell in row[1:]:
            if re.fullmatch(r"[-–—]+", cell):
                values.append("NA")
            elif re.fullmatch(r"\d[\d,]*", cell):
                values.append(int(cell.replace(",", "")))
            elif not cell:
                values.append(None)
            else:
                raise ValueError(f"Ambiguous vote cell for {name}: {cell}")
        output.append(
            {
                "district": district,
                "party": party.upper(),
                "name": name,
                "write_in": write_in,
                "cells": values[:-1],
                "official_total": values[-1],
            }
        )
    if not output:
        raise ValueError(f"No House candidates found in {path}")
    return output


def clerk_candidates(path):
    active_state = False
    active_house = False
    district = None
    output = []
    for page in PdfReader(path).pages[:10]:
        for line in page.extract_text(extraction_mode="layout").splitlines():
            line = line.strip()
            if re.fullmatch(r"ARIZONA(?:[—–-]Continued)?", line, re.I):
                active_state = True
            elif line == "ARKANSAS" and active_state:
                return output
            if not active_state:
                continue
            if line.startswith("FOR UNITED STATES REPRESENTATIVE"):
                active_house = True
                continue
            if line.startswith("FOR UNITED STATES SENATOR") or line.startswith(
                "FOR PRESIDENTIAL ELECTORS"
            ):
                active_house = False
            if not active_house:
                continue
            number = re.match(r"^([1-9])\.\s+", line)
            if number:
                district = int(number[1])
            match = re.match(
                r"^(?:[1-9]\.\s+)?(.+?),\s+(Republican|Democrat(?:ic)?|Green|Libertarian|Independent|Americans Elect|José Peñalosa|Write-in(?:\s*\([^)]+\))?)\s*\.{2,}\s*([\d,]+)$",
                line,
            )
            if match and district:
                name, party, votes = match.groups()
                output.append(
                    {
                        "district": district,
                        "name": name,
                        "party_text": party,
                        "write_in": party.startswith("Write-in"),
                        "votes": int(votes.replace(",", "")),
                    }
                )
    if not output:
        raise ValueError(f"No Arizona House candidates found in Clerk PDF {path}")
    return output


def name_tokens(name):
    name = name.replace("’", "'")
    name = (
        unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    )
    tokens = set(re.findall(r"[a-z]+", name)) - {"jr", "sr", "ii", "iii", "iv"}
    # The official canvass uses Eli, while Clerk statistics use Elijah.
    return {"elijah" if token == "eli" else token for token in tokens}


def verify_snapshots(manifest):
    for source in manifest["snapshots"]:
        path = (ROOT / source["path"]).resolve()
        if not path.is_relative_to(ROOT / "data/raw"):
            raise ValueError("House source must be retained under data/raw")
        if hashlib.sha256(path.read_bytes()).hexdigest() != source["sha256"]:
            raise ValueError(f"House source checksum mismatch: {source['path']}")
