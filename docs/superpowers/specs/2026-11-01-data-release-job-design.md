# Data release job for Relay

## Understanding

**What you asked for.** When a change to the election data (`data/`) is merged to `main`,
Relay should apply it to the production database by itself, using a data version number to
tell whether production is behind. Today this is manual: the deploy worker fails with
`data_release_required` and an operator imports the data and runs `ack-data-release` by hand
(this is what happened with the Senate release).

**Success looks like.** Merging a data PR leads to production serving that data within a few
minutes, with no manual steps, a backup taken first, a clear audit trail, and no change to
production when nothing changed. A data change merged without a version bump is caught
before it can be merged or deployed.

**Assumptions (correct me if wrong).**
- Relay stays unmodified: the new job is an app-owned job registered through a Relay
  manifest, as `docs/AUTOMATIONS.md` describes.
- The deploy worker (`scripts/deploy_worker.py`) is not changed; the job uses its existing
  `ack-data-release` and `retry` commands.
- "DB changes" means data content imports. Schema migrations already ship through the deploy
  worker and are out of scope.

## Design

### 1. Data version
- `data/data-release.json`: `{"version": <integer>, "summary": "<one line>"}`. The version
  only ever increases. A PR that changes anything under `data/` bumps it.
- Baseline: version `1` is the data state of commit `700e2a9` (the Senate release, already
  in production).
- `tools/check_data_version.py <base-ref>` fails if `data/` changed against the base ref
  without a higher version, or if the version decreased. It runs from a pre-push hook now
  and is ready to become a required CI check later.

### 2. Where production records its version
- `PRAGMA user_version` in the production SQLite database holds the applied data version.
  Alembic and SQLAlchemy do not use it, so there is no schema migration and no ordering
  problem with the deploy worker (which refuses to deploy data commits until acknowledged).
- A host-side audit file, `.production/deploy/data-releases.jsonl`, appends one line per
  release attempt: version, commit, backup name, offices imported, outcome, timestamps.

### 3. The job: `scripts/release_data.py`
Runs on the host under Relay. Steps, stopping at the first failure:
1. Fetch `origin/main`; read `data/data-release.json` at that commit.
2. Read production's applied version from a one-off container. Equal: log "up to date" and
   exit 0. File lower than applied: fail (a version went backwards). Applied version unset
   (0): fail unless run once with `baseline <n>`.
3. Preflight: backend healthy; deploy worker not `blocked` and no open journal.
4. Plan: map changed `data/` paths to import scopes (`data/raw/us-senate`,
   `data/processed/us-senate` becomes `--office us-senate`). A changed path that maps to no
   known office (for example geography) fails with a message and leaves production alone.
5. Back up with `manage_db.py backup`; check out the commit in a clean release folder
   (`.production/deploy/data-releases/<sha>`, using git so `.gitattributes` line endings
   apply).
6. Import: run `scripts/import_data.py --office <x>` per scope in a one-off container of the
   currently deployed backend image, with the production state volume and the release
   folder's `scripts/` and `data/`, as the same non-root user as the backend.
7. Verify: backend health; catalog still lists at least the previous number of elections.
8. Record: set `user_version` to the new version, append the audit line.
9. Unblock the deploy: run the worker's `ack-data-release --commit <sha>` and then `retry`.
   The first failure of `deploy-main` for that commit is expected and harmless; the job
   clears it.

Modes: `--dry-run` (plan and checks only, nothing written), `status` (applied vs available
version), `baseline <n>` (one-time marking).

**Failure behaviour.** A nonzero exit fails the Relay run. Production is never restored
automatically; the backup name is in the audit line and the output. Imports are idempotent,
so re-running after a fix is safe. The job also refuses to run if the previous attempt for
the same commit left a started-but-not-finished audit line, until an operator acknowledges it
in Relay (Relay's `recovery_required` handling plus a recovery guard that checks
backend health and the importer lock).

### 4. Relay registration (no Relay source changes)
`.local/applications/election-data-release.json`: application `election-data`, automation
`data-release`, argv `[<repo .venv python>, scripts/release_data.py]`, cwd the repo,
resource `election-production` with scope `global` (same resource as `deploy-main` and
`early-vote`, so they never overlap), interval every 5 minutes, manual runs allowed, retry
policy `manual`, a preflight guard (`release_data.py guard-preflight`) and a recovery guard.
It is registered with scheduling **paused**, run once as `--dry-run` through Relay, then
enabled after you confirm.

### 5. Testing
- Unit tests (`production/tests/test_release_data.py`) with fakes for git and docker:
  version comparison, path-to-office mapping, unknown-path refusal, baseline requirement,
  preflight deferral, idempotent no-op, audit-line contents, failure leaves the version
  unchanged.
- `tools/check_data_version.py` tests on temporary git repositories.
- Rehearsal: `--dry-run` against production (should report "up to date at 1"); a full run
  against a copy of the production database using a throwaway version bump.

## Out of scope
- Changes to Relay's source or to `deploy_worker.py`.
- Automatic rollback of data.
- GitHub Actions / branch protection (discussed separately).
- Schema migrations.

## Decisions I made for you (say if you want any changed)
1. Version lives in `PRAGMA user_version`, not a new table, to avoid a migration and a
   deadlock with the deploy worker's data gate.
2. Imports are scoped to the offices whose files changed, never a full re-import.
3. The job acks and retries the deploy itself, so no human step remains.
4. Scheduling starts paused until a dry run through Relay succeeds.
