"""Cron/foreground adapter: existing importer, bounded diagnostics and signals."""

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.observability import configure_logging, emit


def main():
    configure_logging('refresh')
    try:
        from scripts.refresh_2026 import main as refresh
        sys.argv = [sys.argv[0], '--early-voting']
        refresh()
    except Exception as exc:
        emit(logging.CRITICAL, 'refresh_runtime_failed', exc=exc, outcome='failed')
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
