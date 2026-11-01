#!/usr/bin/env python3
"""Require data release versions before merging substantive data changes.

Usage: python scripts/check_data_version.py [base-ref] [target-ref]
Defaults: origin/main WORKTREE. Pass HEAD as target-ref for committed-only CI
checks. Comparisons start at the merge base of base-ref and target-ref (HEAD
for WORKTREE). WORKTREE includes staged, unstaged, and untracked data files.
The repository is located from this script, so invocation works from any cwd.
This command uses only the Python standard library and a local Git executable.
"""

import argparse
import json
from pathlib import Path
import subprocess
import sys


DESCRIPTOR = "data/data-release.json"
DERIVED_PATHS = frozenset({
    "data/processed/reconciliation.json",
    "data/processed/us-house/reconciliation.json",
    "data/processed/us-house/elections.json",
    "data/processed/2018/vest-comparison.json",
})


class CheckError(Exception):
    """A safe, user-facing explanation without file contents or Git output."""


def git(repo, *args):
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), *args], capture_output=True, check=False
        )
    except OSError:
        raise CheckError("Git could not be executed.") from None
    if result.returncode:
        raise CheckError("Git operation failed; check repository and references.")
    return result.stdout


def commit_ref(repo, ref):
    try:
        return git(repo, "rev-parse", "--verify", "--end-of-options", ref + "^{commit}").decode("ascii").strip()
    except (CheckError, UnicodeError):
        raise CheckError("Cannot resolve Git reference; fetch the base reference first.") from None


def release_version(content, label):
    try:
        release = json.loads(content.decode("utf-8"))
    except (ValueError, UnicodeError):
        raise CheckError(f"{label} descriptor must contain valid UTF-8 JSON.") from None
    if not isinstance(release, dict):
        raise CheckError(f"{label} descriptor must be a JSON object.")
    version = release.get("version")
    if type(version) is not int or not 1 <= version <= 2147483647:
        raise CheckError(f"{label} descriptor version must be an integer from 1 to 2147483647.")
    summary = release.get("summary")
    if (not isinstance(summary, str) or not summary.strip() or len(summary) > 200
            or any(char in summary for char in "\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029")):
        raise CheckError(f"{label} descriptor summary must be one nonempty line of at most 200 characters.")
    return version


def ref_descriptor(repo, ref, label, allow_missing=False):
    present = git(repo, "ls-tree", "-z", ref, "--", DESCRIPTOR)
    if not present:
        if allow_missing:
            return 0
        raise CheckError(f"{label} descriptor is missing.")
    return release_version(git(repo, "show", f"{ref}:{DESCRIPTOR}"), label)


def check(repo, base_ref="origin/main", target_ref="WORKTREE"):
    base = commit_ref(repo, base_ref)
    target = commit_ref(repo, "HEAD" if target_ref == "WORKTREE" else target_ref)
    common = git(repo, "merge-base", base, target).decode("ascii").strip()
    old_version = ref_descriptor(repo, common, "Baseline", allow_missing=True)
    if target_ref == "WORKTREE":
        try:
            content = (repo / DESCRIPTOR).read_bytes()
        except OSError:
            raise CheckError("Candidate descriptor is missing or unreadable.") from None
        new_version = release_version(content, "Candidate")
        changed = git(repo, "diff", "--name-only", "--no-renames", "-z", common, "--", "data/")
        changed += git(repo, "ls-files", "--others", "--exclude-standard", "-z", "--", "data/")
    else:
        new_version = ref_descriptor(repo, target, "Candidate")
        changed = git(repo, "diff", "--name-only", "--no-renames", "-z", common, target, "--", "data/")
    paths = {path.decode("utf-8", errors="surrogateescape") for path in changed.split(b"\0") if path}
    substantive = paths - DERIVED_PATHS - {DESCRIPTOR}
    if new_version < old_version:
        raise CheckError("Data release version decreased from the baseline.")
    if substantive and new_version <= old_version:
        raise CheckError("Importable data changed: data release version must be strictly greater than the baseline.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("base_ref", nargs="?", default="origin/main")
    parser.add_argument("target_ref", nargs="?", default="WORKTREE")
    args = parser.parse_args(argv)
    try:
        check(Path(__file__).resolve().parents[1], args.base_ref, args.target_ref)
    except CheckError as exc:
        print(f"Data version check failed: {exc}", file=sys.stderr)
        return 1
    print("Data version check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
