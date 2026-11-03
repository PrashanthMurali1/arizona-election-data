"""Immutable historical runtime sources, selected by the committed data ledger."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import re
import shutil
import sqlite3
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DIRECTORIES = ('early-canvasses', 'historical-canvasses')


def bundle_path(database, fingerprint):
    if not isinstance(fingerprint, str) or not re.fullmatch('[0-9a-f]{64}', fingerprint):
        raise ValueError('Invalid historical source fingerprint')
    return Path(database).resolve().parent / 'historical-data' / 'releases' / fingerprint


def historical_fingerprint(database):
    """Later unrelated releases retain the last applied historical bundle."""
    with closing(sqlite3.connect(Path(database).resolve().as_uri() + '?mode=ro', uri=True)) as connection:
        if not connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='data_release_history'").fetchone():
            return None
        for fingerprint, scopes in connection.execute('SELECT fingerprint, scopes_json FROM data_release_history ORDER BY version DESC'):
            if 'historical' in json.loads(scopes):
                return fingerprint
    return None


def _files(root):
    files = {}
    for directory in DIRECTORIES:
        path = root / 'raw' / directory
        if not path.is_dir() or path.is_symlink():
            raise ValueError('Historical source directory missing or linked')
        for file in sorted(path.rglob('*')):
            if file.is_symlink():
                raise ValueError('Historical source links are not allowed')
            if file.is_file():
                files[file.relative_to(root).as_posix()] = hashlib.sha256(file.read_bytes()).hexdigest()
    if not files:
        raise ValueError('Historical sources are empty')
    return files


def stage_assets(data_root, database, fingerprint):
    """Copy a complete bundle before the release ledger makes it visible."""
    data_root = Path(data_root).resolve()
    destination = bundle_path(database, fingerprint)
    expected = _files(data_root)
    if destination.exists():
        if _files(destination / 'data') != expected:
            raise ValueError('Historical source bundle differs from its release')
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix='.staging-', dir=destination.parent))
    try:
        for directory in DIRECTORIES:
            shutil.copytree(data_root / 'raw' / directory, temporary / 'data/raw' / directory)
        if _files(temporary / 'data') != expected:
            raise ValueError('Historical source copy failed verification')
        (temporary / 'manifest.json').write_text(json.dumps(expected, sort_keys=True), encoding='utf-8')
        temporary.rename(destination)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return destination


def stage_from_ledger(data_root, database):
    fingerprint = historical_fingerprint(database)
    return stage_assets(data_root, database, fingerprint) if fingerprint else None


def runtime_root(session, fallback=ROOT):
    database = session.get_bind().url.database
    if session.get_bind().dialect.name != 'sqlite' or not database or database == ':memory:':
        return Path(fallback)
    fingerprint = historical_fingerprint(database)
    if not fingerprint:
        return Path(fallback)
    root = bundle_path(database, fingerprint)
    if not (root / 'manifest.json').is_file():
        # An applied release must never silently fall back to stale source files.
        raise RuntimeError('Applied historical source bundle is missing')
    return root
