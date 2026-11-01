"""Build the 14-county boundary used for Arizona results before La Paz County existed.

La Paz County was created in 1983 from the northern part of Yuma County, so results for
1966-1982 report the old, larger Yuma County. This derives that boundary by dissolving today's
Yuma and La Paz polygons from the retained 2022 Census file into one Yuma feature; every other
county is copied unchanged. Requires shapely (a one-off build tool, not a runtime dependency).
The output and its checksum are committed, so the importer never needs shapely.
"""

import hashlib
import json
from pathlib import Path

from shapely.geometry import mapping, shape
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
GEO = ROOT / "data/geography"
SOURCE = GEO / "az-counties-2022.geojson"
OUTPUT = GEO / "az-counties-1966-1982.geojson"
SOURCE_INFO = GEO / "az-counties-1966-1982-source.json"


def build():
    counties = json.loads(SOURCE.read_text(encoding="utf-8"))
    by_id = {f["properties"]["geoid"]: f for f in counties["features"]}
    yuma, la_paz = shape(by_id["04027"]["geometry"]), shape(by_id["04012"]["geometry"])
    if not yuma.touches(la_paz):
        raise ValueError("Yuma and La Paz must share a border to be dissolved")
    merged = unary_union([yuma, la_paz])
    if merged.geom_type != "Polygon" or not merged.is_valid:
        raise ValueError("Dissolving Yuma and La Paz must give one valid polygon")
    features = []
    for geoid, feature in sorted(by_id.items()):
        if geoid == "04012":
            continue
        if geoid == "04027":
            feature = {
                "type": "Feature",
                "properties": {"geoid": "04027", "name": "Yuma"},
                "geometry": mapping(merged),
            }
        features.append(feature)
    OUTPUT.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":")) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    census = json.loads((GEO / "source.json").read_text(encoding="utf-8"))
    SOURCE_INFO.write_text(
        json.dumps(
            {
                "url": census["url"],
                "sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
                "vintage": 1966,
                "notes": (
                    "Derived from the official Census 2022 cartographic county boundaries retained in "
                    "az-counties-2022.geojson. La Paz County was created in 1983 from northern Yuma County, "
                    "so for 1966-1982 the Yuma feature is the dissolved union of today's Yuma and La Paz "
                    "polygons. Other counties are unchanged. This is an approximation: later minor boundary "
                    "adjustments are not modelled, and no geometry is hand-drawn."
                ),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print("wrote", OUTPUT.name, len(features), "counties")


if __name__ == "__main__":
    build()
