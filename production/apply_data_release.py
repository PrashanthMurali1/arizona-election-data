"""Apply reviewed data with an immutable SQLite release ledger and refresh lock.

Run using the deployed backend image, candidate scripts, and a writable data copy.
Importer output is discarded: only fixed structural JSON reaches deployment logs.
"""
from contextlib import contextmanager, closing, redirect_stdout, redirect_stderr
from datetime import datetime, timezone
import argparse
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from production import manage_db

OFFICES = {'governor', 'attorney-general', 'us-senate', 'us-house'}

# This stdlib-only program can also run in the current backend before the helper
# has been deployed. Reading an existing database never creates ledger tables.
READ_STATE_CODE = '''import json,sqlite3
from contextlib import closing
from pathlib import Path
with closing(sqlite3.connect(Path('/app/backend/local/elections.db').as_uri()+'?mode=ro',uri=True,timeout=30)) as c:
 c.row_factory=sqlite3.Row
 version=c.execute('PRAGMA user_version').fetchone()[0]
 tables={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
 release=dict(c.execute('SELECT * FROM data_release_history WHERE version=?',(version,)).fetchone() or {}) if 'data_release_history' in tables else {}
 pending=dict(c.execute('SELECT * FROM data_release_pending WHERE id=1').fetchone() or {}) if 'data_release_pending' in tables else {}
 for item in (release,pending):
  if item:
   item['commit']=item.pop('commit_sha');item['offices']=json.loads(item.pop('scopes_json'));item.pop('id',None)
 print(json.dumps({'version':version,'release':release or None,'pending':pending or None}))
'''


class ReleaseError(Exception):
    """A fixed public failure code; underlying exception text must not be logged."""


def read_release_state(path=None):
    path = Path(path or manage_db.DB).resolve()
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=30)) as connection:
        connection.row_factory = sqlite3.Row
        version = connection.execute('PRAGMA user_version').fetchone()[0]
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        release = (connection.execute('SELECT * FROM data_release_history WHERE version=?', (version,)).fetchone()
                   if 'data_release_history' in tables else None)
        pending = (connection.execute('SELECT * FROM data_release_pending WHERE id=1').fetchone()
                   if 'data_release_pending' in tables else None)

        def public(row):
            if row is None:
                return None
            value = dict(row)
            value['commit'] = value.pop('commit_sha')
            value['offices'] = json.loads(value.pop('scopes_json'))
            value.pop('id', None)
            return value

        return {'version': version, 'release': public(release), 'pending': public(pending)}


@contextmanager
def refresh_lock(path):
    import fcntl

    with Path(path).open('a+') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise ReleaseError('refresh_busy') from None
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def run_import(office):
    try:
        # No raw importer text, traceback, arbitrary source metadata, or paths
        # reach logs or an unbounded in-memory capture buffer.
        subprocess.run([sys.executable, str(ROOT / 'scripts/import_data.py'), '--office', office],
                       cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
                       check=True, timeout=900)
    except Exception:
        raise ReleaseError('data_import_failed') from None


def _validate(version, commit, fingerprint, summary, offices):
    if (type(version) is not int or not 1 <= version <= 2147483647
            or not isinstance(commit, str) or re.fullmatch('[0-9a-f]{40}', commit) is None
            or not isinstance(fingerprint, str) or re.fullmatch('[0-9a-f]{64}', fingerprint) is None
            or not isinstance(summary, str) or not summary.strip() or len(summary) > 200
            or any(c in summary for c in '\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029')
            or not isinstance(offices, (list, tuple)) or not offices
            or any(not isinstance(office, str) or office not in OFFICES for office in offices)
            or len(set(offices)) != len(offices)):
        raise ReleaseError('invalid_release_metadata')


def _check(connection):
    if connection.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
        raise ReleaseError('database_check_failed')
    if connection.execute('PRAGMA foreign_key_check').fetchone() is not None:
        raise ReleaseError('database_check_failed')
    return connection.execute('SELECT count(*) FROM contests').fetchone()[0]


def apply_release(version, commit, fingerprint, summary, offices):
    _validate(version, commit, fingerprint, summary, offices)
    offices = list(offices)
    try:
        with refresh_lock(manage_db.DB.parent / 'early-voting-refresh.lock'):
            state = read_release_state()
            current = state['version']
            previous = state['release']
            pending = state['pending']
            if version < current or (current and previous is None):
                raise ReleaseError('release_version_conflict')
            if pending and (pending['version'] != version or pending['fingerprint'] != fingerprint
                            or pending['offices'] != offices):
                raise ReleaseError('pending_release_conflict')
            if pending and (type(pending.get('baseline_count')) is not int or pending['baseline_count'] <= 0):
                raise ReleaseError('pending_release_baseline_missing')
            if version == current:
                if previous is None or previous['fingerprint'] != fingerprint or pending is not None:
                    raise ReleaseError('release_version_conflict')
                return {'status': 'already_applied', 'version': version}
            with closing(sqlite3.connect(manage_db.DB, timeout=30)) as connection:
                before = _check(connection)
            if before == 0:
                raise ReleaseError('database_check_failed')
            baseline_count = pending['baseline_count'] if pending else before
            with open(os.devnull, 'w') as discarded, redirect_stdout(discarded), redirect_stderr(discarded):
                manage_db.backup('before-data-release')
            at = datetime.now(timezone.utc).isoformat()
            with closing(sqlite3.connect(manage_db.DB, timeout=30)) as connection:
                with connection:
                    connection.execute('''CREATE TABLE IF NOT EXISTS data_release_history(
                        version INTEGER PRIMARY KEY, commit_sha TEXT NOT NULL,
                        fingerprint TEXT NOT NULL, summary TEXT NOT NULL,
                        scopes_json TEXT NOT NULL, applied_at TEXT NOT NULL)''')
                    connection.execute('''CREATE TABLE IF NOT EXISTS data_release_pending(
                        id INTEGER PRIMARY KEY CHECK(id=1), version INTEGER NOT NULL,
                        commit_sha TEXT NOT NULL, fingerprint TEXT NOT NULL,
                        scopes_json TEXT NOT NULL, started_at TEXT NOT NULL,
                        baseline_count INTEGER NOT NULL)''')
                    if pending is None:
                        columns = {row[1] for row in connection.execute('PRAGMA table_info(data_release_pending)')}
                        if 'baseline_count' not in columns:
                            # An empty legacy table is safe to extend; an existing
                            # pending row without its original baseline was denied above.
                            connection.execute('ALTER TABLE data_release_pending ADD COLUMN baseline_count INTEGER')
                        connection.execute('''INSERT INTO data_release_pending
                            (id,version,commit_sha,fingerprint,scopes_json,started_at,baseline_count)
                            VALUES(1,?,?,?,?,?,?)''',
                            (version, commit, fingerprint, json.dumps(offices), at, baseline_count))
            # The pending anchor is durable before the importer can commit. A
            # failed later office must never let another release reuse its version.
            for office in offices:
                run_import(office)
            with closing(sqlite3.connect(manage_db.DB, timeout=30)) as connection:
                with connection:
                    connection.execute('BEGIN IMMEDIATE')
                    if _check(connection) < baseline_count:
                        raise ReleaseError('contest_count_decreased')
                    if connection.execute('PRAGMA user_version').fetchone()[0] != current:
                        raise ReleaseError('release_version_conflict')
                    connection.execute('INSERT INTO data_release_history VALUES(?,?,?,?,?,?)',
                                       (version, commit, fingerprint, summary, json.dumps(offices), at))
                    connection.execute(f'PRAGMA user_version={version}')
                    connection.execute('DELETE FROM data_release_pending WHERE id=1')
            return {'status': 'applied', 'version': version}
    except ReleaseError:
        raise
    except Exception:
        raise ReleaseError('data_release_failed') from None


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ReleaseError('invalid_release_metadata')


def main(argv=None):
    try:
        parser = _Parser(description=__doc__)
        parser.add_argument('--read-state', action='store_true')
        parser.add_argument('--version', type=int)
        parser.add_argument('--commit')
        parser.add_argument('--fingerprint')
        parser.add_argument('--summary')
        parser.add_argument('--offices', nargs='+')
        args = parser.parse_args(argv)
        if args.read_state:
            result = read_release_state()
        else:
            result = apply_release(args.version, args.commit, args.fingerprint, args.summary, args.offices)
    except Exception:
        print(json.dumps({'status': 'failed', 'reason': 'data_release_failed'}))
        return 1
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
