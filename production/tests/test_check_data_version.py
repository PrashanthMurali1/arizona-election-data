"""Exercise the pre-merge guard using isolated local Git repositories."""
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="Git CLI required; guard runs on host/CI")


SOURCE = Path(__file__).resolve().parents[2] / "scripts/check_data_version.py"


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def write(repo, path, text):
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def descriptor(repo, version=1, summary="Test release"):
    write(repo, "data/data-release.json", json.dumps({"version": version, "summary": summary}))


def commit(repo):
    git(repo, "add", "--all")
    git(repo, "commit", "--quiet", "-m", "fixture")
    return git(repo, "rev-parse", "HEAD")


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "--quiet")
    git(root, "config", "user.email", "fixture@example.test")
    git(root, "config", "user.name", "Fixture")
    git(root, "config", "commit.gpgsign", "false")
    if SOURCE.exists():
        (root / "scripts").mkdir()
        shutil.copyfile(SOURCE, root / "scripts/check_data_version.py")
    descriptor(root)
    write(root, "data/raw/results.json", "baseline\n")
    commit(root)
    git(root, "update-ref", "refs/remotes/origin/main", "HEAD")
    return root


def check(repo, *args, cwd=None):
    return subprocess.run(
        [sys.executable, str(repo / "scripts/check_data_version.py"), *args],
        cwd=cwd or repo, capture_output=True, text=True,
    )


def assert_rejected(result, message):
    assert result.returncode == 1, result.stdout + result.stderr
    assert message in result.stderr.lower(), result.stderr
    assert "Traceback" not in result.stderr


def test_unchanged_valid_release_passes_from_unrelated_cwd(repo, tmp_path):
    result = check(repo, cwd=tmp_path)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("path", [
    "data/raw/results.json", "data/raw/source-manifest.json", "data/geography/counties.geojson",
    "data/processed/2026/results.json", "data/raw/private provenance.txt",
])
def test_importable_change_requires_strictly_higher_version(repo, path):
    write(repo, path, "changed\n")
    assert_rejected(check(repo), "strictly greater")


def test_staged_importable_change_requires_bump(repo):
    write(repo, "data/raw/results.json", "changed\n")
    git(repo, "add", "data/raw/results.json")
    result = check(repo)
    assert_rejected(result, "strictly greater")


def test_importable_deletion_requires_bump(repo):
    (repo / "data/raw/results.json").unlink()
    assert_rejected(check(repo), "strictly greater")


def test_rename_out_of_data_requires_bump(repo):
    git(repo, "mv", "data/raw/results.json", "results.json")
    assert_rejected(check(repo), "strictly greater")


@pytest.mark.parametrize("path", [
    "data/processed/reconciliation.json", "data/processed/us-house/reconciliation.json",
    "data/processed/us-house/elections.json", "data/processed/2018/vest-comparison.json",
])
def test_only_declared_derived_outputs_do_not_require_bump(repo, path):
    write(repo, path, "derived\n")
    result = check(repo)
    assert result.returncode == 0, result.stderr


def test_similarly_named_nested_file_is_substantive(repo):
    write(repo, "data/raw/reconciliation.json", "raw\n")
    assert_rejected(check(repo), "strictly greater")


def test_version_bump_allows_data_change(repo):
    write(repo, "data/raw/results.json", "changed\n")
    descriptor(repo, 2)
    result = check(repo)
    assert result.returncode == 0, result.stderr


def test_decreasing_version_fails_without_data_change(repo):
    descriptor(repo, 3)
    commit(repo)
    git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    descriptor(repo, 2)
    assert_rejected(check(repo), "decreased")


@pytest.mark.parametrize("version", [True, False, 0, -1, 2147483648, 1.0, "2", None])
def test_invalid_candidate_version_is_rejected(repo, version):
    descriptor(repo, version)
    assert_rejected(check(repo), "version")


@pytest.mark.parametrize("summary", ["", "   ", "a\nb", "a\rb", "a\u2028b", "a\u2028", "a\v", "x" * 201, None, 1])
def test_invalid_summary_is_rejected(repo, summary):
    descriptor(repo, summary=summary)
    assert_rejected(check(repo), "summary")


@pytest.mark.parametrize("version,summary", [(2147483647, "x" * 200), (2, "Valid release")])
def test_valid_descriptor_boundaries_pass(repo, version, summary):
    descriptor(repo, version, summary)
    result = check(repo)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("content", ["{", "[]", "{}", '{"summary":"release"}'])
def test_malformed_or_incomplete_descriptor_fails_without_echoing_contents(repo, content):
    write(repo, "data/data-release.json", content)
    result = check(repo)
    assert_rejected(result, "descriptor")


def test_missing_candidate_descriptor_fails(repo):
    (repo / "data/data-release.json").unlink()
    assert_rejected(check(repo), "descriptor")


def test_initial_rollout_accepts_missing_baseline_descriptor_as_zero(repo):
    (repo / "data/data-release.json").unlink()
    commit(repo)
    git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    descriptor(repo, 1)
    write(repo, "data/raw/results.json", "changed\n")
    result = check(repo)
    assert result.returncode == 0, result.stderr


def test_invalid_baseline_descriptor_is_not_treated_as_zero(repo):
    descriptor(repo, True)
    commit(repo)
    git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    descriptor(repo, 2)
    assert_rejected(check(repo), "baseline")


def test_explicit_head_checks_committed_content_and_ignores_dirty_bump(repo):
    write(repo, "data/raw/results.json", "changed\n")
    commit(repo)
    descriptor(repo, 2)
    assert_rejected(check(repo, "origin/main", "HEAD"), "strictly greater")
    assert check(repo).returncode == 0


def test_explicit_target_ref_does_not_read_dirty_descriptor(repo):
    descriptor(repo, 2)
    write(repo, "data/raw/results.json", "changed\n")
    commit(repo)
    descriptor(repo, False)
    result = check(repo, "origin/main", "HEAD")
    assert result.returncode == 0, result.stderr


def test_base_uses_merge_base_instead_of_unmerged_upstream_changes(repo):
    original = git(repo, "rev-parse", "HEAD")
    descriptor(repo, 3)
    write(repo, "data/raw/results.json", "upstream\n")
    upstream = commit(repo)
    git(repo, "update-ref", "refs/remotes/origin/main", upstream)
    git(repo, "checkout", "--quiet", "--detach", original)
    write(repo, "README.md", "branch-only code change\n")
    commit(repo)
    result = check(repo, "origin/main", "HEAD")
    assert result.returncode == 0, result.stderr


def test_bad_ref_is_rejected_without_echoing_ref(repo):
    result = check(repo, "invalid-secret-like-ref")
    assert_rejected(result, "reference")
    assert "invalid-secret-like-ref" not in result.stdout + result.stderr
