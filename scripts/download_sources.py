"""Downloads are optional when the checked-in source snapshots are present."""

import sys
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.normalize import URLS

URLS = {
    **{str(k) + ".pdf": v for k, v in URLS.items()},
    "counties.zip": "https://www2.census.gov/geo/tiger/GENZ2022/shp/cb_2022_us_county_500k.zip",
}
failed = []
for name, url in URLS.items():
    p = ROOT / "data/raw" / name
    if p.exists():
        print(name, "already present")
        continue
    try:
        r = requests.get(url, timeout=45)
        r.raise_for_status()
        p.write_bytes(r.content)
        print(name, len(r.content), "bytes")
    except requests.RequestException as e:
        failed.append(name)
        print(name, "FAILED:", e)
if failed:
    sys.exit(1)
