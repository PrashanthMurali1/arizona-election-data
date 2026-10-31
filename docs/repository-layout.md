# Repository contents and cleanup policy

This repository is the application's rebuild kit, not a copy of the production
SQLite database. The API normally serves SQLite, but importers, tests and clean
installations still need source files outside that database. A successful import
alone is not a reason to delete the file it read.

## Which JSON files are necessary?

| Files | Keep in Git? | Purpose |
| --- | --- | --- |
| `data/processed/{year}.json`, `attorney-general/{year}.json`, `us-senate/az-*.json` | Yes, under the current workflow | `scripts/import_data.py` enumerates these directly; historical, Senate and API tests read them. They can be regenerated, but not every importer/test prepares them first. |
| `data/raw/**/*.json` | Yes | Source acquisition records, manifests, checksums, provenance and retained API snapshots. These are evidence and replay inputs, not redundant copies of database rows. |
| `data/geography/*.geojson` and accompanying source JSON | Yes, under the current workflow | Fresh imports and provider tests require geography before the database can serve it. |
| `data/processed/reconciliation.json`, House reconciliation | Yes for now | Audit output and existing scoped-import/test behavior preserve or inspect prior contest reports. Removing them needs explicit workflow changes. |
| `data/processed/**/validation/*.json`, historical baselines | Yes | Some are explicit test fixtures; others retain historical comparisons that are not recreated by ordinary bootstrap. |
| `data/processed/us-house/elections.json` | Retained for now | House import normalizes raw sources directly instead of reading this generated file. It is potentially removable, but the current raw-source checksum blocker prevents a successful fresh regeneration, so the last normalized audit snapshot remains retained. |
| `data/processed/2018/vest-comparison.json` | No; generated locally | The 2018 normalizer recreates this report, and the retained `2018.json` already embeds its validation information. The missing report was regenerated offline and compared with the original during cleanup verification. |
| Package/TypeScript configuration, lockfiles and production JSON | Yes | Runtime/build configuration, dependency reproducibility and reviewed monitoring/routing definitions. Do not delete files just because they use JSON. |
| `backend/local/**`, private assistant settings | No | Machine-local databases, metrics and runtime state; retain on disk and ignore. |

Before cleanup, all processed JSONs together were about **528 KiB**; the normalized
governor/Attorney General/Senate election inputs account for about **139 KiB**.
Removing those inputs saves little and can silently omit contests from a direct
glob-based import. The raw source PDFs, CSVs, ZIPs and manifests provide independent
verification; database rows do not replace them.

Moving all derived election/geography files out of Git is possible as a separate
change: generators must create all output directories, every import/test needs an
explicit data-preparation step, and missing inputs must not silently reduce
coverage. Until then, keep these rebuild inputs.

## Tooling and generated artifacts

The three agent adapters retain their skill documentation, launchers, version
pins and checksum manifests. Their bundled Mac ARM engine copies are no longer
versioned. Local copies are preserved, and launchers support verified cache or
download fallback. A fresh Mac checkout needs a cached/preinstalled engine or
network access for its first download; offline users should provision it before
disconnecting. The adapters themselves are not interchangeable copies and remain
in place.

This removes about **50.7 MiB** of native binaries from the proposed tracked tree,
plus the generated comparison and local permissions file. It does not erase old
Git objects, shrink existing history, or delete the local caches.

`.claude/settings.local.json` is local configuration and remains on disk.
The new `.claude/settings.json` is shared project plugin configuration and is
preserved with the other existing edits. Licensed fonts and their license files
remain because the frontend uses them.

`.gitignore` excludes local runtime state, native engine caches and the specific
regenerable comparison output. `.dockerignore` excludes agent/editor tooling from
application build contexts. No blanket JSON or raw-data exclusion was added.

## Verification and an existing source-integrity blocker

Cleanup checks run in disposable source copies and databases, never in the
production volume or the working dataset. Original edits/new historical inputs
are fingerprinted before checks, and local copies of untracked artifacts remain.

The current checkout has seven House calendar snapshots whose bytes do not match
their recorded checksums (`data/raw/us-house/calendar/vacancies-113.html` through
`vacancies-119.html`). Before- and after-cleanup offline bootstraps fail at the
same first mismatch. Simple LF/CRLF conversion does not reproduce the expected
hashes. This is an existing source-integrity issue; cleanup does not change the
files, manifests or checksum validation. A complete bootstrap/full-suite pass
must not be claimed until those sources are restored from verified evidence.

The removed VEST comparison can be regenerated independently with
`python scripts/normalize_2018.py`. Historical-import and production checks can
run against disposable resources while the unrelated House blocker is recorded.

Private audit/test records are under `.production/repository-cleanup/`. This
cleanup does not commit, push, rewrite history, update production or remove
historical source evidence.
