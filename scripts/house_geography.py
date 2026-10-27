"""Retain the correct Census congressional plan, native CRS and all nine districts."""

import hashlib
import io
import json
import math
import zipfile
from pathlib import Path

import shapefile

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/us-house"
OUT = ROOT / "data/geography"


def normalize():
    acquired = {
        Path(r["path"]).name: r
        for r in json.loads((RAW / "acquisition.json").read_text())
        if "path" in r
    }
    for plan, vintage, congress in [(2012, 2014, 114), (2022, 2022, 118)]:
        raw = RAW / f"districts-{plan}-plan.zip"
        digest = hashlib.sha256(raw.read_bytes()).hexdigest()
        if digest != acquired[raw.name]["sha256"]:
            raise ValueError("Congressional source archive checksum mismatch")
        with zipfile.ZipFile(raw) as archive:

            def part(ext):
                return io.BytesIO(
                    archive.read(next(n for n in archive.namelist() if n.endswith(ext)))
                )

            crs = part(".prj").read().decode()
            if "North_American_1983" not in crs:
                raise ValueError(
                    "Unexpected Census district coordinate reference system"
                )
            reader = shapefile.Reader(
                shp=part(".shp"), shx=part(".shx"), dbf=part(".dbf")
            )
            features = []
            for record in reader.iterShapeRecords():
                props = record.record.as_dict()
                if props["STATEFP"] != "04":
                    continue
                district = int(props[f"CD{congress}FP"])
                geometry = record.shape.__geo_interface__
                if geometry["type"] not in {"Polygon", "MultiPolygon"}:
                    raise ValueError(
                        "Congressional districts require actual polygon geometry"
                    )
                for x, y in record.shape.points:
                    if (
                        not math.isfinite(x + y)
                        or not -115 < x < -108
                        or not 30 < y < 38
                    ):
                        raise ValueError("Invalid Arizona district longitude/latitude")
                features.append(
                    {
                        "type": "Feature",
                        "properties": {
                            "geoid": f"az-cd-{plan}-{district:02}",
                            "census_geoid": props["GEOID"],
                            "name": f"District {district}",
                            "label": str(district),
                            "district": district,
                            "plan": plan,
                        },
                        "geometry": geometry,
                    }
                )
        if {f["properties"]["district"] for f in features} != set(range(1, 10)) or len(
            features
        ) != 9:
            raise ValueError("Expected exactly nine Arizona congressional districts")
        features.sort(key=lambda f: f["properties"]["district"])
        collection = {
            "type": "FeatureCollection",
            "crs": {
                "type": "name",
                "properties": {"name": "urn:ogc:def:crs:EPSG::4269"},
            },
            "features": features,
        }
        (OUT / f"az-congressional-{plan}.geojson").write_text(
            json.dumps(collection, separators=(",", ":")) + "\n"
        )
        source = {
            "id": f"census-cd-{plan}",
            "title": f"U.S. Census Bureau — {congress}th Congress district boundaries",
            "url": acquired[raw.name]["url"],
            "sha256": digest,
            "notes": f"Arizona subset of Census {vintage} 1:500,000 cartographic congressional boundaries for Congress {congress}, representing the plan first used in {plan}. Nine original Polygon/MultiPolygon geometries; no county approximation or added simplification. Native geographic NAD83 (EPSG:4269) longitude/latitude coordinates retained, with CRS identified explicitly. District IDs include the plan year.",
            "vintage": vintage,
            "plan": plan,
            "coordinate_reference_system": crs,
            "raw_path": str(raw.relative_to(ROOT)),
            "geojson_sha256": hashlib.sha256(
                (OUT / f"az-congressional-{plan}.geojson").read_bytes()
            ).hexdigest(),
            "retrieved_at": acquired[raw.name]["retrieved_at"],
        }
        (OUT / f"az-congressional-{plan}-source.json").write_text(
            json.dumps(source, indent=2) + "\n"
        )
        print(
            plan, "plan:", len(features), "districts, native NAD83 longitude/latitude"
        )


if __name__ == "__main__":
    normalize()
