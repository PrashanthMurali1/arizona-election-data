# Historical data deployment failure, November 3, 2026

The manual deployment of `7e0c2633487416f69f3f3ba6e44248079d3d9499`
stopped in preflight with `data_path_unmapped`. The production database was
still release version 1 with 96 contests, no historical-canvass contests,
and no pending release. The application remained on `0b9e54b`.
The release-version bump fixed the GitHub merge check, but did not extend
the installed production worker's supported data paths.

The worker now maps the early/historical raw directories and normalized
historical archive to one `historical` scope. The release runner invokes
the dedicated historical importer. The delta also includes a 1986 Senate
party correction; Senate-only transcription/provenance changes no longer
cause an unrelated full modern House import. Shared statewide source
changes still select both offices, and unknown data paths still fail closed.

The runtime also needs source JSON, presidential-ticket metadata and PDFs.
These are copied into a hash-verified immutable bundle on the persistent
state volume before release version advancement. Historical API readers
select a bundle only through the committed release ledger. Retries verify
and reuse the same bundle; incomplete copies cannot become the active
release. Disposable candidate checks restore the bundle next to their
copied database. No test database replaces production, and no release
acknowledgment bypass is used.

## Rehearsal

An online backup was made through the existing production backup command:
`.production/backups/backup-20261103T172016260975Z.db`.
The backup was copied into `tmp/historical-release-rehearsal/`, then imported
using the currently deployed backend image, candidate scripts, a disposable
writable data copy, no network, and no production volume mount.

The actual production delta selected `historical` and `us-senate`.
Both completed with release version 2, 1,248 contests, and no pending release.
The historical importer added 1,152 archive-owned contests while preserving
independently reviewed existing records; all 4,381 original vote-result rows
retain their values. David Zilly's 1986 Senate party is corrected to SWP.
SQLite quick-check passed and foreign-key check returned no violations.

With the candidate data mount removed, the new backend served 1911 Secretary
of State (21,130 total votes), 1914 and 1942 Governor, 1956 President (290,173),
1966 State Senate, 14-county results, and the retained 38,224,013-byte Mason PDF
from the persistent bundle.

Regression checks passed: 134 focused Windows tests; 175 Linux deployment,
refresh and historical tests (47 Git-dependent tests skipped because the
production image contains no Git CLI). All four source-bundle tests, including
the final presidential/PDF API regression, also passed separately on both
Windows and Linux.

## Applying the fix

The live database and installed privileged worker are unchanged by the
rehearsal. Merge the reviewed fix before updating the installed worker.
As described in `automatic-deployment.md`, pause and drain both Relay
production schedules, acquire both the Relay resource and original
deployment locks, archive the installed worker/config, install the tested
worker and its reviewed trust hash together, then release the locks and
deliberately retry through Relay. Restore the previous schedule settings
after checking the release ledger, retained sources, application health,
and exclusive scheduler ownership.

Version 2 remains the intended release: production never applied it. No
further data-version bump is needed for this code-only deployment repair.
Do not clear pending state, overwrite the production database from the
preview, reinitialize its volume, or mark the data release acknowledged.
