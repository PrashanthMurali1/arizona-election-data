"""Failure parsing uses synthetic output; never executes a production job."""
import json
from scripts.relay_diagnostics import extract, record_failure


def test_passed_tests_are_not_reported_as_failures():
    output = "  ok 1 e2e/catalog.spec.ts:111:3 passed\n  ok 2 e2e/explorer.spec.ts:5:1 passed"
    assert extract(output) == [{"kind": "command_failure"}]


def test_playwright_failure_prefers_assertion_line_and_ignores_passes():
    output = """
  ok 1 e2e/explorer.spec.ts:5:1 SECRET
  x 2 e2e/catalog.spec.ts:111:3 SECRET
  1) e2e/catalog.spec.ts:111:3 SECRET
    Error: expect(locator).toBeVisible() failed
    Received: https://private/?token=SECRET
      at C:\\private\\frontend\\e2e\\catalog.spec.ts:287:11
  1 failed
  1 passed
"""
    assert extract(output) == [{"kind": "assertion", "suite": "catalog.spec.ts",
                               "line": 287, "operator": "toBeVisible"}]


def test_each_failure_has_its_own_kind_and_operator():
    output = """1) e2e/catalog.spec.ts:20:1 first
Error: expect(locator).toHaveText(expected) failed
2) e2e/explorer.spec.ts:30:1 second
Error: expect(locator).toBeVisible() failed
3) e2e/house.spec.ts:40:1 third
TimeoutError: locator.click: Test timeout
"""
    assert extract(output) == [
        {"kind": "assertion", "suite": "catalog.spec.ts", "line": 20, "operator": "toHaveText"},
        {"kind": "assertion", "suite": "explorer.spec.ts", "line": 30, "operator": "toBeVisible"},
        {"kind": "timeout", "suite": "house.spec.ts", "line": 40},
    ]


def test_pytest_summary_only_reports_failed_reviewed_suites():
    output = """production/tests/test_logging.py .. [50%]
FAILED production/tests/test_deploy_worker.py::test_SECRET - AssertionError: SECRET
FAILED backend/tests/private_credentials.py::test_SECRET - SECRET
"""
    assert extract(output) == [{"kind": "test_failure", "suite": "test_deploy_worker.py"}]


def test_ansi_and_windows_paths_are_supported():
    output = "\x1b[31m1) e2e\\catalog.spec.ts:111:3 SECRET\x1b[0m\nAssertionError: SECRET"
    assert extract(output) == [{"kind": "assertion", "suite": "catalog.spec.ts", "line": 111}]


def test_diagnostics_are_bounded_and_duplicates_coalesce():
    block = "1) e2e/catalog.spec.ts:111:3 repeated\nError: expect(x).toBeVisible() failed\n"
    assert len(extract(block * 3)) == 1
    output = "".join(f"{i}) e2e/catalog.spec.ts:{i}:3 fail\nAssertionError\n" for i in range(1, 25))
    assert len(extract(output)) == 12


def test_record_is_sanitized_and_storage_failure_is_best_effort(tmp_path):
    output = "1) e2e/catalog.spec.ts:10:1 SECRET\nError: expect(x).toHaveText('SECRET') failed\nhttps://secret/?token=SECRET"
    record_failure(tmp_path, output, "test", 1, "a" * 40)
    raw = (tmp_path / "diagnostics/commands.jsonl").read_text(encoding="utf-8")
    value = json.loads(raw)
    assert "SECRET" not in raw and "https://" not in raw
    assert value["phase"] == "test" and value["commit_sha"] == "a" * 40
    blocker = tmp_path / "blocker"
    blocker.write_text("file", encoding="utf-8")
    record_failure(blocker, output, "test", 1)
