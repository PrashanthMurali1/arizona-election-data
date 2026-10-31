# Public repository privacy checks

Keep personal machine configuration, home paths, private contact information,
credentials, backups, databases, diagnostic output and local assistant settings
outside Git. `.production/` is private operational storage, not a publication
directory. Ignoring an already tracked file does not remove it from Git.

Public election-source contacts, public officials, original source documents,
license attribution and intentionally published project URLs are legitimate
repository content. Preserve their provenance and attribution. A public source
document is not the same thing as a private production export.

## Local check

From the repository root:

```powershell
.\.venv\Scripts\python.exe tools/privacy_scan.py --include-untracked
.\.venv\Scripts\python.exe -m unittest discover -s tools/tests -v
```

The standard-library guard reads Git-listed working-tree files, optionally adding
untracked files that Git does not ignore. It does not open ignored local secret
files. Findings contain a category, relative filename and line, never a matching
value or source excerpt. Exit codes are 0 for clean, 1 for findings, 2 for an
inspection/configuration error; errors fail closed without raw Git messages.

Checks cover personal home paths, unexpected email addresses, identifying hosts,
common credential formats, private-key headers, credential-bearing URLs, private
artifact filenames and unreviewed binaries. This is a guard, not an exhaustive
secret detector or a confidentiality guarantee. Intentionally fictitious
reserved-domain examples are allowed; environment examples still get secret
checks. A local credential must never be put in `.env.example`.

`tools/privacy_allowlist.json` records exact reviewed content. Text approvals use
SHA-256 after UTF-8/BOM and CRLF/LF normalization, so Windows and Linux checkouts
agree without changing the original files. Binary approvals remain byte-exact.
Changed files require review again. Public-source contacts and deliberate
redaction-test sentinels have narrowly scoped approvals; known credential formats,
private keys and personal home paths cannot be approved away. Do not regenerate
approvals merely to silence a new finding.

## Before a commit

```powershell
.\.venv\Scripts\python.exe tools/privacy_scan.py --staged --check-identity
```

This reads the actual Git index, so removing a secret from the working copy does
not conceal a still-staged copy. The optional identity check requires GitHub
noreply author and committer emails, reporting categories without addresses.
An unset or inaccessible identity fails closed. Do not bypass findings to finish
a commit; decide what should be public first.

An opt-in `.githooks/pre-commit` runs that command. If there is no existing hook
arrangement to preserve, enable it deliberately:

```powershell
git config --local core.hooksPath .githooks
```

The audit does not change hook configuration or Git identity automatically.
Review existing hooks before replacing their configuration. To change future
commits, copy the correct GitHub-provided noreply address from your account's
email settings and configure it locally:

```powershell
git config --local user.email "<your-github-noreply-address>"
```

Also review GitHub's email privacy and personal-email push-protection settings.
Changing these settings does not edit existing commits. See
[GitHub's commit email guide](https://docs.github.com/en/account-and-profile/how-tos/email-preferences/setting-your-commit-email-address).

## Full secret and history review

Use a trusted local installation of [Gitleaks](https://github.com/gitleaks/gitleaks)
alongside the guard. It does not require uploading repository contents to a
scanning service. For history, keep redacted reports and all scanner output in
ignored private storage:

```powershell
New-Item -ItemType Directory -Force .production/privacy-audit | Out-Null
gitleaks git . --log-opts="--all" --redact=100 --no-banner --report-format json --report-path .production/privacy-audit/history-secrets.json --log-level error *> .production/privacy-audit/scanner-output.txt
```

Gitleaks reports can contain commit identity metadata even when secrets are
redacted. Do not add those reports to Git or paste raw findings into chat.
Avoid indiscriminately scanning private ignored configuration when auditing what
is public. Scan a snapshot made only from the intended Git files for working-tree
secret checks; do not export private local directories into that snapshot.

Review reachable branches/tags and author/committer metadata separately from
working-tree cleanup. Inspect PDFs, archive members, screenshots and other binary
artifacts according to their provenance; text matching cannot inspect everything
inside an image. Local refs do not establish coverage of unfetched pull requests,
other clones/forks, published packages, CI artifacts or cached pages.

If a real credential was ever committed, revoke/rotate it first. Removing it from
the current tree is insufficient. History rewriting is a separate coordinated
operation requiring explicit authorization, collaborator coordination and review
of automation tied to commit hashes. It cannot remove other people's existing
clones or guarantee removal from forks, caches or published artifacts. See
[GitHub's sensitive-data removal guide](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository).

Do not rotate account credentials, rewrite history, force-push or alter production
settings as an incidental part of a source cleanup. Keep identifying audit reports
private and publish only policy or appropriately masked summaries.
