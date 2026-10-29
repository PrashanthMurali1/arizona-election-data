"""Load the runtime-only license key before the New Relic launcher starts Python."""

import os
from pathlib import Path
import sys


def main():
    key = Path('/run/secrets/newrelic_license_key').read_text(encoding='utf-8-sig').strip()
    if not key or any(character.isspace() for character in key):
        raise SystemExit('New Relic license key must contain one non-empty value.')
    if not sys.argv[1:]:
        raise SystemExit('A backend command is required.')
    os.environ['NEW_RELIC_LICENSE_KEY'] = key
    os.execvp('newrelic-admin', ['newrelic-admin', 'run-program', *sys.argv[1:]])


if __name__ == '__main__':
    main()
