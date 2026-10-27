"""Rebuild/import local data using versioned source snapshots; run from any directory."""

import subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for args in [
    ["-m", "alembic", "-c", "backend/alembic.ini", "upgrade", "head"],
    ["scripts/normalize_transcription.py"],
    ["scripts/geography.py"],
    ["scripts/import_data.py"],
    ["scripts/refresh_2026.py"],
]:
    subprocess.run([sys.executable, *args], cwd=ROOT, check=True)
