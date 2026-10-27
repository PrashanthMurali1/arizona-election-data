"""Convert Census 2022 1:500k cartographic county boundaries to Arizona GeoJSON."""

import json, zipfile, io, hashlib
from pathlib import Path
import shapefile

ROOT = Path(__file__).resolve().parents[1]
p = ROOT / "data/raw/counties.zip"
with zipfile.ZipFile(p) as z:

    def part(ext):
        return io.BytesIO(z.read(next(n for n in z.namelist() if n.endswith(ext))))

    reader = shapefile.Reader(
        shp=part(".shp"), shx=part(".shx"), dbf=part(".dbf"), encoding="utf-8"
    )
    features = []
    for r in reader.iterShapeRecords():
        props = r.record.as_dict()
        if props["STATEFP"] == "04":
            features.append(
                {
                    "type": "Feature",
                    "properties": {"geoid": props["GEOID"], "name": props["NAME"]},
                    "geometry": r.shape.__geo_interface__,
                }
            )
if len(features) != 15 or len({f["properties"]["geoid"] for f in features}) != 15:
    raise ValueError(
        "Census extraction must contain exactly 15 unique Arizona counties"
    )
(ROOT / "data/geography/az-counties-2022.geojson").write_text(
    json.dumps(
        {"type": "FeatureCollection", "features": features}, separators=(",", ":")
    )
)
(ROOT / "data/geography/source.json").write_text(
    json.dumps(
        {
            "url": "https://www2.census.gov/geo/tiger/GENZ2022/shp/cb_2022_us_county_500k.zip",
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
            "vintage": 2022,
            "notes": "Official Census cartographic boundary file, 1:500,000; Arizona subset, no hand-drawn geometry. Used as a common visualization vintage for historical county results.",
        },
        indent=2,
    )
    + "\n"
)
print("Converted all 15 Census Arizona counties")
