"""Release ledger safety against disposable SQLite; never production or Docker."""
from contextlib import contextmanager
import importlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
COMMIT = 'a' * 40
FINGERPRINT = 'b' * 64


def test_data_release_runner_is_available():
    assert (ROOT / 'production/apply_data_release.py').is_file()


@pytest.fixture
def runner(tmp_path, monkeypatch):
    module = importlib.import_module('production.apply_data_release')
    db = tmp_path / 'elections.db'
    with sqlite3.connect(db) as connection:
        connection.execute('CREATE TABLE contests(id TEXT PRIMARY KEY)')
        connection.execute("INSERT INTO contests VALUES ('existing')")
    monkeypatch.setattr(module.manage_db, 'DB', db)
    events = []

    @contextmanager
    def locked(path):
        events.append('lock')
        try:
            yield
        finally:
            events.append('unlock')

    def backup(label):
        assert label == 'before-data-release'
        events.append('backup')
        return tmp_path / 'backup.db'

    monkeypatch.setattr(module, 'refresh_lock', locked)
    monkeypatch.setattr(module.manage_db, 'backup', backup)
    monkeypatch.setattr(module, 'run_import', lambda office: events.append(office))
    return module, db, events


def apply(module, **values):
    args = dict(version=1, commit=COMMIT, fingerprint=FINGERPRINT,
                summary='Reviewed public election data', offices=['governor'])
    args.update(values)
    return module.apply_release(**args)


def test_read_state_does_not_create_ledger(runner):
    module, db, _ = runner
    assert module.read_release_state() == {'version': 0, 'release': None, 'pending': None}
    with sqlite3.connect(db) as connection:
        assert [r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")] == ['contests']


def test_import_is_backed_up_and_ledger_commits_with_version(runner):
    module, db, events = runner
    result = apply(module, offices=['governor', 'us-senate'])
    state = module.read_release_state()
    assert result['status'] == 'applied'
    assert events == ['lock', 'backup', 'governor', 'us-senate', 'unlock']
    assert state['version'] == 1 and state['pending'] is None
    assert state['release']['commit'] == COMMIT
    assert state['release']['fingerprint'] == FINGERPRINT
    assert state['release']['offices'] == ['governor', 'us-senate']


def test_failed_import_retains_anchor_and_refuses_different_content(runner, monkeypatch):
    module, db, events = runner

    def fail_after_commit(office):
        with sqlite3.connect(db) as connection:
            connection.execute("INSERT INTO contests VALUES ('imported')")
        raise RuntimeError('private exception must not escape CLI')

    monkeypatch.setattr(module, 'run_import', fail_after_commit)
    with pytest.raises(module.ReleaseError):
        apply(module)
    state = module.read_release_state()
    assert state['version'] == 0 and state['release'] is None
    assert state['pending']['fingerprint'] == FINGERPRINT
    with pytest.raises(module.ReleaseError):
        apply(module, fingerprint='c' * 64)
    with pytest.raises(module.ReleaseError):
        apply(module, version=2)
    monkeypatch.setattr(module, 'run_import', lambda office: events.append(office))
    apply(module, commit='d' * 40)
    assert module.read_release_state()['version'] == 1


def test_repeated_version_checks_fingerprint_without_reimport(runner):
    module, _, events = runner
    apply(module)
    events.clear()
    assert apply(module, commit='d' * 40)['status'] == 'already_applied'
    assert events == ['lock', 'unlock']
    with pytest.raises(module.ReleaseError):
        apply(module, fingerprint='c' * 64)
    assert module.read_release_state()['release']['commit'] == COMMIT


def test_unanchored_existing_version_and_downgrade_are_rejected(runner):
    module, db, events = runner
    with sqlite3.connect(db) as connection:
        connection.execute('PRAGMA user_version=1')
    with pytest.raises(module.ReleaseError):
        apply(module)
    with pytest.raises(module.ReleaseError):
        apply(module, version=0)
    assert 'backup' not in events


def test_contest_loss_leaves_version_unadvanced(runner, monkeypatch):
    module, db, _ = runner

    def remove_contests(office):
        with sqlite3.connect(db) as connection:
            connection.execute('DELETE FROM contests')

    monkeypatch.setattr(module, 'run_import', remove_contests)
    with pytest.raises(module.ReleaseError):
        apply(module)
    assert module.read_release_state()['version'] == 0
    assert module.read_release_state()['pending']['version'] == 1


def test_backup_failure_prevents_pending_and_import(runner, monkeypatch):
    module, _, events = runner
    monkeypatch.setattr(module.manage_db, 'backup', lambda label: (_ for _ in ()).throw(OSError('private')))
    with pytest.raises(module.ReleaseError):
        apply(module)
    assert module.read_release_state()['pending'] is None
    assert events == ['lock', 'unlock']


def test_failed_retry_cannot_accept_a_previous_attempts_contest_loss(runner, monkeypatch):
    module, db, _ = runner
    with sqlite3.connect(db) as connection:
        connection.executemany('INSERT INTO contests VALUES (?)', [('second',), ('third',)])

    def remove_then_fail(office):
        with sqlite3.connect(db) as connection:
            connection.execute("DELETE FROM contests WHERE id='third'")
        raise RuntimeError('import failed after its database commit')

    monkeypatch.setattr(module, 'run_import', remove_then_fail)
    with pytest.raises(module.ReleaseError):
        apply(module)
    monkeypatch.setattr(module, 'run_import', lambda office: None)
    with pytest.raises(module.ReleaseError):
        apply(module)
    state = module.read_release_state()
    assert state['version'] == 0 and state['release'] is None
    assert state['pending']['baseline_count'] == 3


def test_pending_without_original_contest_count_fails_closed(runner):
    module, db, events = runner
    with sqlite3.connect(db) as connection:
        connection.execute('CREATE TABLE data_release_pending(id INTEGER PRIMARY KEY,version INTEGER,commit_sha TEXT,fingerprint TEXT,scopes_json TEXT,started_at TEXT)')
        connection.execute('INSERT INTO data_release_pending VALUES(1,?,?,?,?,?)',
                           (1, COMMIT, FINGERPRINT, json.dumps(['governor']), 'earlier'))
    with pytest.raises(module.ReleaseError):
        apply(module)
    assert events == ['lock', 'unlock']
    assert module.read_release_state()['version'] == 0


def test_import_process_output_is_discarded_and_failure_is_static(monkeypatch):
    module = importlib.import_module('production.apply_data_release')
    seen = []

    def run(argv, **kwargs):
        seen.append((argv, kwargs))
        raise subprocess.CalledProcessError(1, argv)

    monkeypatch.setattr(module.subprocess, 'run', run)
    with pytest.raises(module.ReleaseError) as failure:
        module.run_import('governor')
    assert str(failure.value) == 'data_import_failed'
    argv, options = seen[0]
    assert argv[-2:] == ['--office', 'governor']
    assert options['stdout'] == subprocess.DEVNULL
    assert options['stderr'] == subprocess.STDOUT
    assert options['check'] is True and options['timeout'] > 0


def test_backup_output_is_not_logged(runner, monkeypatch, capsys):
    module, _, _ = runner
    monkeypatch.setattr(module.manage_db, 'backup', lambda label: print('private backup path'))
    apply(module)
    assert capsys.readouterr().out == ''


def test_failure_after_version_stamp_rolls_back_ledger_and_version(runner, monkeypatch):
    module, db, _ = runner

    def prevent_pending_clear(office):
        with sqlite3.connect(db) as connection:
            connection.execute("CREATE TRIGGER refuse_clear BEFORE DELETE ON data_release_pending BEGIN SELECT RAISE(ABORT,'test'); END")

    monkeypatch.setattr(module, 'run_import', prevent_pending_clear)
    with pytest.raises(module.ReleaseError):
        apply(module)
    state = module.read_release_state()
    assert state['version'] == 0 and state['release'] is None
    assert state['pending']['fingerprint'] == FINGERPRINT
    with sqlite3.connect(db) as connection:
        assert connection.execute('SELECT count(*) FROM data_release_history').fetchone()[0] == 0


def test_cli_does_not_print_private_exceptions(runner, monkeypatch, capsys):
    module, _, _ = runner
    called = []

    def fail(*args, **kwargs):
        called.append(True)
        raise RuntimeError('private secret path')

    monkeypatch.setattr(module, 'apply_release', fail)
    assert module.main(['--version', '1', '--commit', COMMIT, '--fingerprint', FINGERPRINT,
                        '--summary', 'Public', '--offices', 'governor']) == 1
    captured = capsys.readouterr()
    assert json.loads(captured.out) == {'status': 'failed', 'reason': 'data_release_failed'}
    assert captured.err == '' and 'private' not in captured.out
    assert called == [True]


@pytest.mark.parametrize('values', [dict(version=True), dict(version=-1), dict(version=2147483648),
                                    dict(commit='bad'), dict(fingerprint='bad'), dict(offices=[]),
                                    dict(offices=['unknown']), dict(summary=''), dict(summary=' '),
                                    dict(summary='x' * 201), dict(summary='line\u2028separator'),
                                    dict(summary='line\rbreak')])
def test_invalid_metadata_fails_before_backup(runner, values):
    module, _, events = runner
    with pytest.raises(module.ReleaseError):
        apply(module, **values)
    assert events == []
