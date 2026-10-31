"""Local public-repository guard. Reports locations/categories, never matches.

This complements a full secret scanner; it is not a guarantee of confidentiality.
Only Git-listed content is read. Ignored local credentials are not inspected.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess


RULES = {
    "personal_home_path": re.compile(
        r"(?i)(?:[a-z]:[\\/]+(?:Users|Documents and Settings)[\\/]+([^\\/\s\"'<>:]+)"
        r"|/(?:Users|home)/([^/\s\"'<>:]+))"
    ),
    "email_address": re.compile(
        r"(?i)[A-Z0-9.!#$%&'*+/=?^_{|}~-]{1,64}@[A-Z0-9.-]{1,253}\.[A-Z]{2,}"
    ),
    "known_secret_format": re.compile(
        r"\b(?:NRAK-[A-Za-z0-9]{20,}|NRAL-[A-Za-z0-9]{20,}|"
        r"gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,}|"
        r"(?:AKIA|ASIA)[A-Z0-9]{16}|AIza[A-Za-z0-9_-]{30,}|"
        r"xox[baprs]-[A-Za-z0-9-]{15,}|sk-(?:proj-)?[A-Za-z0-9_-]{25,})\b"
    ),
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "credential_url": re.compile(
        r"(?i)(?:https?|postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis)://"
        r"[A-Z0-9._~%-]+:[^/\s@\"'<>`]+@[A-Z0-9.-]+"
    ),
    "secret_url_parameter": re.compile(
        r"(?i)[?&](?:access_token|api_key|apikey|token|password|secret|license_key)="
        r"([^&\s\"'<>`]{8,})"
    ),
    "identifying_host": re.compile(
        r"\b(?:DESKTOP|LAPTOP)-[A-Z0-9]{6,15}\b|"
        r"(?i:[a-z0-9-]*(?:macbook|imac)[a-z0-9-]*\.local)|"
        r"https?://(?:192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|"
        r"172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+)(?::\d+)?"
    ),
}
REVIEWABLE = {"email_address", "credential_url", "secret_url_parameter"}
EXAMPLE_USERS = {"example", "example-user", "username", "user", "your_user", "app", "root"}
EXAMPLE_VALUES = {"PRIVATE_SENTINEL", "SECRET_SENTINEL", "REDACTED", "redacted", "example-token", "test-token"}
PRIVATE_SUFFIXES = {".env", ".db", ".sqlite", ".sqlite3", ".pem", ".key", ".p12", ".pfx", ".keystore", ".log", ".jsonl"}
PRIVATE_DIRS = {"secrets", "backups", "exports", "test-results", "playwright-report", ".aws", ".production", ".production-cache"}


@dataclass(frozen=True)
class Finding:
    category: str
    file: str
    line: int = 1


def safe_path(path: str) -> str:
    for name in ("personal_home_path", "email_address", "known_secret_format"):
        path = RULES[name].sub("[redacted]", path)
    return path


def private_artifact(path: str) -> bool:
    p = PurePosixPath(path)
    parts = {s.lower() for s in p.parts[:-1]}
    name = p.name.lower()
    return bool(parts & PRIVATE_DIRS or
                (name.startswith(".env") and name != ".env.example") or
                p.suffix.lower() in PRIVATE_SUFFIXES or
                re.search(r"\.(?:db|sqlite3?)-(?:wal|shm|journal)$", name) or
                name in {"id_rsa", "id_ed25519"} or
                path in {".codex/auth.json", ".claude/settings.local.json", ".gemini/settings.local.json"})


def acceptable_example(category, match):
    if category == "personal_home_path":
        return (match[1] or match[2]).lower() in EXAMPLE_USERS
    if category == "email_address":
        domain = match[0].rsplit("@", 1)[-1].lower()
        return domain in {"example.com", "example.net", "example.org"} or domain.endswith((".invalid", ".test", ".example"))
    if category == "secret_url_parameter":
        return match[1] in EXAMPLE_VALUES or match[1].startswith(("${", "{{"))
    return False


def scan_content(path: str, data: bytes, approvals: dict) -> list[Finding]:
    display = safe_path(path)
    if private_artifact(path):
        return [Finding("private_artifact", display)]
    checksum = hashlib.sha256(data).hexdigest()
    try:
        text = data.decode("utf-8-sig")
        binary = "\x00" in text
    except UnicodeDecodeError:
        binary = True
    if binary:
        approved = any(v["path"] == path and v["sha256"] == checksum for v in approvals.get("binary", []))
        return [] if approved else [Finding("binary_review_required", display)]
    # Git may check out CRLF on Windows and LF in CI. Text approvals describe
    # content rather than a checkout's line-ending convention; binary hashes
    # above remain byte-exact. This does not alter any public source file.
    checksum = hashlib.sha256(text.replace("\r\n", "\n").encode("utf-8")).hexdigest()
    allowed = set()
    for entry in approvals.get("content", []):
        if entry["path"] == path and entry["sha256"] == checksum:
            allowed.update(set(entry["categories"]) & REVIEWABLE)
    findings = set()
    for category, pattern in RULES.items():
        if category in allowed or (category == "email_address" and "@" not in text):
            continue
        for match in pattern.finditer(text):
            if not acceptable_example(category, match):
                findings.add(Finding(category, display, text.count("\n", 0, match.start()) + 1))
    return sorted(findings, key=lambda v: (v.file, v.line, v.category))


def git(root, *args, input=None):
    result = subprocess.run(["git", "-C", str(root), *args], input=input, capture_output=True)
    if result.returncode:
        # Git errors can contain credential-bearing remotes or private paths.
        raise RuntimeError("Git inspection failed; no raw error was emitted")
    return result.stdout


def load_approvals(path):
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("version") != 1:
        raise ValueError("Unsupported privacy approval format")
    for section in ("content", "binary"):
        for entry in value.get(section, []):
            p = PurePosixPath(entry["path"])
            if p.is_absolute() or ".." in p.parts or not re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]) or not entry.get("reason"):
                raise ValueError("Invalid privacy approval")
            if section == "content" and not set(entry["categories"]) <= REVIEWABLE:
                raise ValueError("Secrets and personal paths cannot be allowlisted")
    return value


def scan_repository(root, approvals, *, staged=False, include_untracked=False):
    root = root.resolve()
    if staged:
        names = git(root, "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z")
    else:
        args = ["ls-files", "--cached", "-z"]
        if include_untracked:
            args += ["--others", "--exclude-standard"]
        names = git(root, *args)
    findings = []
    count = 0
    for name in sorted(set(names.decode("utf-8").split("\0")) - {""}):
        target = root / name
        if staged:
            data = git(root, "show", ":" + name)
        else:
            if target.is_symlink() or not target.resolve().is_relative_to(root):
                findings.append(Finding("symlink_review_required", safe_path(name)))
                continue
            if not target.is_file():
                continue
            data = target.read_bytes()
        count += 1
        findings.extend(scan_content(name, data, approvals))
    return findings, count


def identity_findings(root):
    findings = []
    for role in ("AUTHOR", "COMMITTER"):
        identity = git(root, "var", "GIT_" + role + "_IDENT").decode("utf-8")
        match = re.search(r"<([^<>]+)>", identity)
        email = match[1].lower() if match else ""
        if not (email.endswith("@users.noreply.github.com") or email == "noreply" + "@github.com"):
            findings.append(Finding("non_noreply_" + role.lower() + "_email", "[next commit metadata]"))
    return findings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--staged", action="store_true", help="Read added/modified Git index contents, not working-tree copies")
    parser.add_argument("--include-untracked", action="store_true", help="Also scan untracked files not excluded by .gitignore")
    parser.add_argument("--check-identity", action="store_true", help="Require GitHub noreply author/committer identities without displaying addresses")
    args = parser.parse_args()
    try:
        approvals = load_approvals(args.root / "tools/privacy_allowlist.json")
        findings, count = scan_repository(args.root, approvals, staged=args.staged, include_untracked=args.include_untracked)
        if args.check_identity:
            findings.extend(identity_findings(args.root))
        print(json.dumps({"files_scanned": count, "findings": [asdict(v) for v in findings]}, indent=2))
        return 1 if findings else 0
    except Exception:
        print(json.dumps({"error": "Privacy scan failed closed; inspect configuration and Git access locally. No raw exception was emitted."}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
