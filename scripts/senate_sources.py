"""Read retained official canvass extracts; no network or inferred vote cells."""

import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Tables(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.row = None
        self.cell = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = []
        elif tag in {"td", "th"} and self.row is not None:
            self.cell = ""

    def handle_data(self, data):
        if self.cell is not None:
            self.cell += data

    def handle_endtag(self, tag):
        if tag in {"td", "th"} and self.cell is not None:
            self.row.append(" ".join(self.cell.split()))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None


def table_rows(path):
    text = path.read_text()
    # Search output may append other sources; only the first official table is input.
    text = text.split("</table>", 1)[0]
    if "<tr>" in text:
        parser = Tables()
        parser.feed(text)
        return parser.rows
    # Indexed official PDFs may expose Markdown rather than HTML tables.
    return [
        [cell.strip().replace("**", "") for cell in line.strip().strip("|").split("|")]
        for line in text.splitlines()
        if line.strip().startswith("|")
        or line.strip().startswith("**U.S.")
    ]


def candidate_rows(path):
    rows = table_rows(path)
    active = False
    candidates = []
    for row in rows:
        label = row[0].replace("**", "").strip()
        if label.startswith("U.S. Senator"):
            active = True
            continue
        if active and label.startswith("U.S. Representative"):
            break
        match = re.fullmatch(r"\(([^)]+)\) (.+)", label)
        if not active or not match:
            continue
        if len(row) != 17:
            raise ValueError(f"Unexpected official candidate cell count: {row}")
        party, name = match.groups()
        write_in = "(Write-In)" in name
        name = name.replace("(Write-In)", "").rstrip(" *").strip()
        values = []
        for cell in row[1:]:
            if not re.fullmatch(r"[0-9][0-9,]*", cell):
                raise ValueError(f"Missing/ambiguous official vote cell: {row}")
            values.append(int(cell.replace(",", "")))
        candidates.append((party.upper(), name, write_in, values))
    if not candidates:
        raise ValueError(f"No Senate roster extracted from {path}")
    return candidates


def verify_provenance(path):
    provenance = json.loads(path.read_text())
    for snapshot in provenance["snapshots"]:
        file = (ROOT / snapshot["path"]).resolve()
        if not file.is_relative_to(ROOT / "data/raw"):
            raise ValueError("Senate source snapshot must be inside data/raw")
        digest = hashlib.sha256(file.read_bytes()).hexdigest()
        if digest != snapshot["sha256"]:
            raise ValueError(f"Senate source checksum mismatch: {snapshot['path']}")
    return provenance
