"""Load Arizona House special-election totals from retained civicAPI reports."""

import json
from pathlib import Path

RAW = Path(__file__).resolve().parents[1] / "data/raw/us-house/civicapi"

RACES = {
    "2018-04-24": ("race-29426.json", 8),
    "2025-09-23": ("race-6240.json", 7),
}
PARTIES = {
    "Democratic": "DEM",
    "Republican": "REP",
    "Green": "GRN",
    "No Labels": "NOL",
}


def special_records():
    """Return district-level candidate totals exactly as retained from civicAPI.

    These endpoints do not provide a compatible district result broken down by
    all Arizona counties. County values are therefore intentionally absent.
    """
    result = {}
    for date, (filename, district) in RACES.items():
        race = json.loads((RAW / filename).read_text())
        expected_district = f"AZ-{district:02}"
        if race["district"] != expected_district or not race["candidates"]:
            raise ValueError(f"Unexpected civicAPI race snapshot for {date}")
        rows = []
        for candidate in race["candidates"]:
            party = PARTIES.get(candidate["party"])
            if party is None or not isinstance(candidate.get("votes"), int):
                raise ValueError(f"Unsupported civicAPI candidate record: {candidate}")
            rows.append(
                {
                    "district": district,
                    "party": party,
                    "name": candidate["name"],
                    "write_in": False,
                    "category": "named_candidate",
                    "cells": [None] * 15,
                    "official_total": candidate["votes"],
                    "provider_percent": candidate.get("percent"),
                    "provider_winner": candidate.get("winner", False),
                }
            )
        result[date] = rows
    return result
