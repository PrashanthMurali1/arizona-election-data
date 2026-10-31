import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tools.privacy_scan import (
    identity_findings, load_approvals, private_artifact, scan_content, scan_repository,
)


class PrivacyChecks(unittest.TestCase):
    def test_personal_paths_and_examples(self):
        windows = "C:" + chr(92) + "Users" + chr(92) + "private-test-user" + chr(92) + "project"
        for text in (windows, "/" + "Users/private-test-user/project", "/" + "home/private-test-user/project"):
            self.assertEqual(scan_content("README.md", text.encode(), {})[0].category, "personal_home_path")
        self.assertEqual(scan_content("README.md", b"$HOME/project and /home/example/project", {}), [])

    def test_email_is_masked_and_reserved_examples_are_allowed(self):
        email = "123+example" + "@" + "users.noreply.github.com"
        findings = scan_content("notes.txt", email.encode(), {})
        self.assertEqual(findings[0].category, "email_address")
        self.assertNotIn(email, json.dumps([v.__dict__ for v in findings]))
        self.assertEqual(scan_content("notes.txt", ("person" + "@" + "example.invalid").encode(), {}), [])

    def test_secret_formats_and_private_key_are_never_allowlisted(self):
        value = ("NRAK-" + "A" * 28).encode()
        approval = {"content": [{"path": "example.txt", "sha256": hashlib.sha256(value).hexdigest(), "categories": ["known_secret_format"]}]}
        self.assertEqual(scan_content("example.txt", value, approval)[0].category, "known_secret_format")
        key = ("-----BEGIN " + "PRIVATE KEY-----").encode()
        self.assertEqual(scan_content("example.txt", key, {})[0].category, "private_key")

    def test_environment_examples_still_get_secret_checks(self):
        self.assertFalse(private_artifact(".env.example"))
        self.assertTrue(private_artifact(".env.production"))
        self.assertTrue(private_artifact("production.env"))
        value = ("NRAK-" + "B" * 28).encode()
        self.assertEqual(scan_content(".env.example", value, {})[0].category, "known_secret_format")

    def test_artifact_names_and_sqlite_sidecars_are_blocked(self):
        for name in ("secrets/key", "backups/anything", "state.sqlite3-wal", "output.db-shm", ".claude/settings.local.json", "app.log", "events.jsonl"):
            self.assertTrue(private_artifact(name), name)

    def test_reviewed_public_attribution_requires_exact_file_hash(self):
        value = ("Published contact: " + "public-example" + "@" + "agency.gov").encode()
        approval = {"content": [{"path": "data/source.txt", "sha256": hashlib.sha256(value).hexdigest(), "categories": ["email_address"]}]}
        self.assertEqual(scan_content("data/source.txt", value, approval), [])
        self.assertTrue(scan_content("data/source.txt", value + b" changed", approval))
        self.assertTrue(scan_content("other.txt", value, approval))

    def test_binary_changes_require_review(self):
        data = b"\x00\xfflicensed binary"
        approval = {"binary": [{"path": "font.ttf", "sha256": hashlib.sha256(data).hexdigest()}]}
        self.assertEqual(scan_content("font.ttf", data, approval), [])
        self.assertEqual(scan_content("font.ttf", data + b"changed", approval)[0].category, "binary_review_required")

    def test_text_approvals_work_across_windows_and_linux_line_endings(self):
        value = ("Public contact: " + "public-example" + "@" + "agency.gov\n").encode()
        approval = {"content": [{"path": "source.txt", "sha256": hashlib.sha256(value).hexdigest(), "categories": ["email_address"]}]}
        self.assertEqual(scan_content("source.txt", value.replace(b"\n", b"\r\n"), approval), [])

    def test_desktop_layout_words_are_not_machine_names(self):
        self.assertEqual(scan_content("guide.md", b"Desktop-first and desktop-only layout", {}), [])
        self.assertEqual(scan_content("guide.md", b"DESKTOP-" + b"EXAMPLE1", {})[0].category, "identifying_host")

    def test_unsafe_approval_categories_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "approvals.json"
            path.write_text(json.dumps({"version": 1, "content": [{"path": "file", "sha256": "a" * 64, "categories": ["private_key"], "reason": "invalid"}]}), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_approvals(path)

    def test_staged_scan_uses_index_and_does_not_read_ignored_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True, capture_output=True)
            (root / ".gitignore").write_text("secrets/\n", encoding="utf-8")
            (root / "secrets").mkdir()
            (root / "secrets/private").write_bytes(("NRAK-" + "C" * 28).encode())
            path = root / "tracked.txt"
            path.write_bytes(("NRAK-" + "D" * 28).encode())
            subprocess.run(["git", "-C", str(root), "add", "tracked.txt", ".gitignore"], check=True, capture_output=True)
            path.write_text("safe working copy", encoding="utf-8")
            findings, _ = scan_repository(root, {}, staged=True)
            self.assertEqual([v.category for v in findings], ["known_secret_format"])
            self.assertEqual(scan_repository(root, {}, include_untracked=True)[0], [])

    def test_git_identities_are_reported_without_addresses(self):
        fake = ("Example <" + "test" + "@" + "example.invalid> 0 +0000").encode()
        with patch("tools.privacy_scan.git", return_value=fake):
            findings = identity_findings(Path("."))
        self.assertEqual(len(findings), 2)
        self.assertNotIn("@", json.dumps([v.__dict__ for v in findings]))


if __name__ == "__main__":
    unittest.main()
