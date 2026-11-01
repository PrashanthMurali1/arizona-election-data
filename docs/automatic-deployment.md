# Relay-managed production operations

Relay at **http://127.0.0.1:8765** is the sole scheduling authority:
- Deployment checks `origin/main` every 120 seconds.
- Refresh runs at 00:00, 06:00, 12:00, 18:00 **Asia/Kolkata**.
- Deployment and refresh share one resource lock. Refresh also holds the deployment engine's original Windows lock; the refresh itself retains its Linux flock.
- The old **Arizona Election Explorer - Deploy main** Windows task and Docker cron container/service have been removed. `scripts/windows-deploy-worker.ps1`, `production/start_scheduler.py` and the `scheduled` Compose profile are retired.
- `scripts/deploy_worker.py` remains the deployment engine used by Relay; `production/refresh_job.py` remains the refresh entry point. Neither is a separate scheduler.

## Status and controls

Use Relay's overview and automation detail pages for schedule ownership, next run, logs, manual execution, pause/resume and deliberate retry. A deployment no-op is shown as skipped with exit code 0. Failed commits remain suppressed by the deployment engine until deliberate retry; newer commits are still considered. Docker/network deferrals retry at later slots. Do not reintroduce a task or cron alongside Relay.

Relay source and operations guide:
`../automation-service/README.md`

The Windows startup task **Relay - Local automation platform** remains installed under the Docker-owning signed-in user. It starts/rechecks the hidden supervisor at sign-in and every two minutes with IgnoreNew. Windows must be awake and signed in; Docker Desktop must be available. No automatic login, update or power policy changes are part of this cleanup.

Read-only election inspection:
```powershell
Get-Content .production/deploy/logs/deploy.jsonl -Tail 30
docker compose --profile public ps -a
docker compose --profile public logs --tail 100 backend frontend tunnel
docker compose exec -T backend cat backend/local/early-voting-refresh-status.json
```

## Retained safeguards and state

The private `.production/deploy/` directory remains:
- `worker/`: installed reviewed deployment engine and sanitized logger/exporter snapshot.
- `checkout/`, `releases/`: isolated clone and immutable-source release worktrees.
- `configs/`: pinned image references, absolute protected bind/secret paths.
- `state.json`: actual deployed image IDs, per-service source/runtime fingerprints, failed commits and migration/activation journals.
- `logs/`, `browser-cache/`: bounded deployment diagnostics and test browser cache.
- `retired/`: exported disabled task XML, prior installed worker/config, and retirement outcome. These files are private and excluded from Git.

All named volumes, production database, raw sources, backups, images, credentials, Cloudflare routing and existing New Relic settings are preserved. Historical manifests/configs may still record a cron image. The current engine verifies only backend, frontend and tunnel, ignores the retired entry, and filters cron out of old rollback journals. It never recreates or restarts cron.

Backend/importer/shared logging changes affect the backend image; frontend and tunnel dependencies remain independently classified. Documentation/test-only changes are skipped. The worker compares source/config fingerprints and real running image IDs rather than the IDE checkout HEAD. No checkout changes are discarded automatically.

Build/checks still use disposable candidate resources. Activation backs up the database, invokes explicit candidate-image migrations with `--no-deps`, verifies health, HTTPS/API/deep links/assets/monitoring, and records success only after verification. No old initialize/migrate image is implicitly started. Compatible failures restore application images; unknown/incompatible migrations block rollback. No older production database is restored automatically.

## Manual deployment and recovery

Prefer Relay's Run now / Retry. Before manual deployment, image rollback, migration recovery or database maintenance, pause **both** production schedules in Relay and wait for queued/running jobs to finish. Unknown-outcome runs require investigation and deliberate recovery acknowledgment. Pausing a schedule does not cancel an active run.

For direct access to the existing engine after the drain:
```powershell
$config=Join-Path $PWD '.production/deploy/config.json'
$worker=Join-Path $PWD '.production/deploy/worker/scripts/deploy_worker.py'
$python=(Get-Content -LiteralPath $config -Raw | ConvertFrom-Json).python
& $python $worker --config $config status
# Deliberate operator actions only after investigating status and compatibility:
& $python $worker --config $config run
& $python $worker --config $config retry
& $python $worker --config $config recover
& $python $worker --config $config rollback
```

`rollback` applies to a completed compatible prior deployment. `recover` handles a compatible interrupted journal; it cannot make an incompatible migration safe. Use `accept-recovery` only after independently validating a complete image/config set against the database. Resume both Relay schedules only after health and exclusive ownership are verified.

For backwards-compatible migration declarations, retain:
```json
{"backward_compatible_with":"<currently deployed backend source_sha>"}
```
The deployment engine also tests the previous backend against the migrated disposable database. A failed/unknown migration cannot authorize rollback merely through that declaration.

Never use mutable `:local` / `:newrelic` Compose up/build commands to replace worker-owned containers. They can deploy older images and trigger runtime drift. For offline database recovery, pause/drain Relay, stop writers, preserve a fresh backup, and explicitly select the intended pinned image and backup. Never delete a journal to bypass recovery, run `down -v`, prune production volumes, or discard newer data.

## Legacy scheduler retirement and recovery

The removed task was exported to `.production/deploy/retired/deployment-task.xml`. The stopped cron container was removed with `docker rm` **without volume deletion**. No old images or Compose history were pruned. The backend Dockerfile no longer installs cron; existing immutable backend images remain unchanged until the next reviewed release.

Relay now distinguishes confirmed absence from a task/Docker discovery failure. A missing retired task/container is expected; permission/engine failures still block execution. The private config records `legacy_schedulers_removed=true` and the reviewed installed-worker hash. Reappearance of a retired scheduler blocks normal ownership checks.

Do not use the earlier return-to-legacy shortcut: it is explicitly rejected after retirement, before changing ownership. Restoring historical scheduling would require a separate reviewed reverse migration: pause/drain Relay, reconstruct the archived task and a compatible pinned cron image/config, change ownership deliberately, and verify exactly one scheduler. Do not simply register the archived task or start an old cron alongside Relay.

Changes to the installed deployment engine must be reviewed/tested and installed under both locks with its trusted hash updated. Pushing `scripts/deploy_worker.py` does not silently self-update this privileged host component.

## Validation

The cleanup was tested with mocked deployments and disposable resources. Deployment, logging, exporter and Linux refresh-lock tests pass in a disposable container without production data volumes or credentials. Relay tests cover confirmed absence versus discovery errors, data-preserving artifact removal, safe failure journaling and rejection of obsolete authority rollback. The live app retains its original images and data; no deployment/refresh failure was induced.


## Automatic versioned data releases

`data/data-release.json` is the release contract: a positive, increasing integer
`version` and a one-line `summary` (maximum 200 characters). Regenerate and review
processed inputs when changing raw sources; the statewide importer consumes
processed JSON rather than normalizing all raw files. House normalizes its inputs.
Before merging, run:

```powershell
python scripts/check_data_version.py origin/main
```

The Data version GitHub Actions workflow checks PRs and main commits. Configure
its `check-data-version` job as a required branch protection check on GitHub.
The checker includes staged, unstaged and untracked data by default; pass `HEAD`
as the second argument to check committed content only. Exact generated reports
are excluded; geography, raw inputs and provenance are never blanket-excluded.

Inside the existing serialized deployment cycle, before image builds or tests,
the worker compares the descriptor with production SQLite `PRAGMA user_version`
and the immutable `data_release_history` ledger. Identical version/content is a
read-only no-op. New content at the same version or a decreasing version fails
with a specific sanitized reason. Successful import remains recorded even if
later image build/tests fail; a retry does not import it again.

A newer supported release takes an online backup, then runs the deployed backend
image with candidate import scripts and a writable private copy of candidate
data (including an explicit replacement for the inherited raw-data mount).
The one-off container acquires the Linux refresh lock, backs up again inside
that lock, and records `data_release_pending` before importing affected offices.
Quick-check, foreign-key checks and nondecreasing contest count must pass before
history insertion, version advancement and pending removal commit atomically.
The original deployment lock and Relay resource lock serialize scheduled jobs.
No initialize/migrate dependency is implicitly launched.

Mappings cover Governor, Attorney General, Senate and House, including shared
statewide canvasses. Unknown data paths, geography/2026 inputs, and data combined
with schema/model/database/runtime dependency changes fail before import. These
require a separately reviewed release procedure; they are never silently skipped.

Imports can commit before a later office/report fails. Such failures retain the
pending fingerprint and backup, leave the version unadvanced, and stop before
build/tests. Inspect the database and importer using disposable copies, then use
Relay Retry for the same content. Conflicting pending content requires deliberate
operator recovery; do not clear the record or restore an older DB automatically.
A stable import container name detects a daemon-side process left running after
a CLI timeout and defers instead of launching a second importer. Never remove an
active import container to force a retry.

`ack-data-release --commit <full-sha>` is an emergency, commit-specific override
that bypasses automatic data validation/import and emits a warning. It does not
advance the version or fabricate a ledger. Normal releases need no import/ack.
The initial v1 ledger is anchored specifically to the already-imported Governor
release `c237d04`, after backup and verification; it does not import that data twice.

Deployment logs retain the existing rotation and New Relic caps. The sanitized
`deployment_data_applied` summary is forwarded through the existing exporter;
failures use existing preflight/backup/migrate phases and bounded reason codes.
Check `.production/deploy/logs/deploy.jsonl`, Relay run logs, worker `status`, and
SQLite release history/pending for incident diagnosis. Import stdout/stderr is
discarded to avoid secret-bearing diagnostic output. Private staging copies are
removed after success; failed copies are retained for deliberate investigation.
Application image rollback never rolls back imported production data.
