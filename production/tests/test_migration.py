"""Standard-library migration checks; runnable before Docker/dependency setup."""

import hashlib
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts import prepare_production
from production import manage_db


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / 'Mac export with spaces'
        self.source.mkdir()
        with closing(sqlite3.connect(self.source / 'elections.db')) as db:
            db.execute('CREATE TABLE contests (id TEXT)')
            db.execute("INSERT INTO contests VALUES ('retained-contest')")
            db.commit()
        (self.source / 'raw').mkdir()
        (self.source / 'raw/source.json').write_text('{"retained": true}\n')
        (self.source / 'raw/manifest.json').write_text('{"nested_source_manifest": true}\n')
        (self.source / 'audit/logs').mkdir(parents=True)
        (self.source / 'audit/logs/job.log').write_text('retained log\n')
        self.manifest = {
            p.relative_to(self.source).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in self.source.rglob('*') if p.is_file()
        }
        self.save_manifest()
        self.target = self.root / 'Windows checkout/.production'
        self.target.parent.mkdir()
        self.patch = patch.object(prepare_production, 'TARGET', self.target)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def save_manifest(self):
        (self.source / 'manifest.json').write_text(json.dumps(self.manifest))

    def test_import_retains_database_raw_and_job_audit_and_refuses_replacement(self):
        prepare_production.prepare_export(self.source)
        manage_db.check(self.target / 'seed/elections.db')
        self.assertEqual((self.target / 'raw/source.json').read_bytes(), (self.source / 'raw/source.json').read_bytes())
        self.assertEqual((self.target / 'seed/audit/logs/job.log').read_text(), 'retained log\n')
        with self.assertRaises(SystemExit):
            prepare_production.prepare_export(self.source)

    def test_corrupt_or_missing_files_do_not_create_production_directory(self):
        (self.source / 'raw/source.json').write_text('corrupted')
        with self.assertRaisesRegex(RuntimeError, 'checksum'):
            prepare_production.prepare_export(self.source)
        self.assertFalse(self.target.exists())
        (self.source / 'raw/source.json').unlink()
        with self.assertRaisesRegex(RuntimeError, 'Incomplete'):
            prepare_production.prepare_export(self.source)
        self.assertFalse(self.target.exists())

    def test_manifest_cannot_read_outside_export(self):
        self.manifest['../outside'] = 'bad'
        self.save_manifest()
        with self.assertRaises(RuntimeError):
            prepare_production.prepare_export(self.source)
        self.assertFalse(self.target.exists())

    def test_online_backup_preserves_committed_wal_without_sidecars(self):
        source = self.root / 'live.db'
        destination = self.root / 'standalone.db'
        with closing(sqlite3.connect(source)) as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('CREATE TABLE contests (id TEXT)')
            db.execute("INSERT INTO contests VALUES ('committed-in-wal')")
            db.commit()
            prepare_production.backup(source, destination)
            manage_db.check(destination)
            with closing(sqlite3.connect(destination)) as copy:
                self.assertEqual(copy.execute('SELECT id FROM contests').fetchone()[0], 'committed-in-wal')
        self.assertFalse(Path(str(destination) + '-wal').exists())

    @unittest.skipIf(os.name == 'nt', 'Export runs in the Linux backend container')
    def test_live_export_roundtrip_preserves_sources_and_audit(self):
        app = self.root / 'running-app'
        state = app / 'backend/local'
        state.mkdir(parents=True)
        shutil.copy2(self.source / 'elections.db', state / 'elections.db')
        shutil.copytree(self.source / 'raw', app / 'data/raw')
        shutil.copytree(self.source / 'audit/logs', state / 'logs')
        (state / 'early-voting-refresh-status.json').write_text('{"status": "success"}\n')
        with patch.multiple(manage_db, ROOT=app, STATE=state, DB=state / 'elections.db', BACKUPS=self.root / 'backups'):
            exported = manage_db.export_migration()
        prepare_production.prepare_export(exported)
        self.assertEqual((self.target / 'seed/audit/early-voting-refresh-status.json').read_text(), '{"status": "success"}\n')
        self.assertEqual((self.target / 'raw/manifest.json').read_bytes(), (self.source / 'raw/manifest.json').read_bytes())


if __name__ == '__main__':
    unittest.main()
