# Windows automatic deployments

Installed task: **Arizona Election Explorer - Deploy main**. It checks the public
repository's `origin/main` every two minutes and 15 seconds after its Windows
owner signs in. It runs as that same Docker-owning user with least privilege,
InteractiveToken authentication, no stored password, and `pythonw.exe` (no terminal
window). Task Scheduler uses IgnoreNew; a cross-process byte lock also serializes
scheduled runs, manual deployments and recovery.

## Layout and deployment behavior

All worker state is private under `.production/deploy/`, outside the IDE's Git
checkout. The worker directory has an ACL granting the installing user access.

| Path | Purpose |
| --- | --- |
| `worker/` | Installed, reviewed worker/logger snapshot; independent of IDE edits |
| `checkout/` | Dedicated single-branch Git clone; never reset or cleaned automatically |
| `releases/<commit>/` | Detached, immutable-source worktrees used for builds/checks |
| `configs/` | Private resolved Compose files with absolute production bind/secret paths |
| `state.json` | Per-service source/config fingerprints, exact image IDs, checked commit, failures and recovery journal |
| `logs/deploy.jsonl` | Rotating sanitized deployment diagnostics |
| `browser-cache/` | Shared Playwright browser download cache |
| `checks/` | Disposable copied databases; removed after candidate checks |

The app keeps project name `az-election-explorer`, existing named volumes, original
raw/backup/secret directories, loopback port, Cloudflare connector and New Relic
settings. The IDE checkout is not pulled, switched, reset, or cleaned. Git runs
without credential helpers, prompts, inherited GitHub tokens, or global/system
Git configuration: this public repository needs anonymous **read-only** access.
If it becomes private, the worker defers; provision a read-only transport through
a reviewed worker update instead of adding a broad personal token.

Each cycle verifies running image IDs and runtime identities against the manifest,
then fetches main. It compares runtime inputs, not checkout HEAD or a single
last-deployed commit. Frontend code/public assets/build dependencies affect the
frontend; packaged backend/importer code affects backend and scheduler; shared
logging and supervisor files affect their dependent images. Compose service
configuration is compared separately. Documentation, tests, dashboard definitions
and administration-only worker scripts do not trigger app deployment. Test/build
dependency lockfiles are treated conservatively as build inputs.

An unchanged runtime records a no-op. If relevant files changed, the worker:

1. Builds affected image groups using `git-<full-commit>-<unique-build-id>` tags and
   OCI revision labels. Previously deployed tags are never overwritten.
2. Runs focused backend/migration/logging/refresh/SSE tests in disposable Linux
   containers when Python images change. It deliberately does not gate on the
   historical full-suite provenance failures documented in the Windows guide.
3. For frontend/Python changes, takes an online backup and copies it into a
   disposable candidate database. Migration rehearsal and API/browser checks use
   that copy, a separate Docker bridge, no production network attachment and no
   credentials. A standard bridge is necessary for host Playwright on Docker
   Desktop; this staging bridge has normal outbound connectivity. Unit/fixture
   containers use `--network none`.
4. Runs the frontend unit suite and the reviewed catalog/explorer/House browser
   specs from that release, not tests that force production imports.
5. Saves an atomic, flushed activation journal. It drains the scheduler when
   affected, stops the backend when updating it, then runs migrations through the
   **explicit candidate backend image** with `--no-deps`. That migration command
   makes a fresh backup before upgrading the actual database.
6. Activates only affected services (also resuming a scheduler drained for a
   backend update), always with `--no-deps`. Initialization is never run and old
   initialization/migration containers are never selected as dependencies.
7. Verifies every service's health/image, the local and public catalog, historical
   detail APIs, early-voting activity, HTML deep links and expected asset URLs and
   responses. It checks affected services' log-ingest acceptance and backend APM
   registration. Only then does it record the new deployed manifest.

The worker finishes a deployment before checking main again. It processes up to
three successive heads in one invocation; the next timer catches additional
changes. It does not deploy every intermediate commit in a rapid sequence when a
newer main is already available.

Retained-source `data/` changes require a separate data-release procedure; the
worker never bootstraps or overwrites the production raw sources/database from
Git. New host mounts/secrets, storage names, published ports/networks, container
identities, timezone/refresh cadence, log rotation or existing New Relic settings
are protected and fail closed. New services or advanced build options also need
a reviewed worker update. This is automation for the existing deployment, not an
unrestricted infrastructure reconciler.

## Status, logs, pause/resume and manual deployment

Run from the IDE repository root in PowerShell. The process-only execution-policy
flag does not change machine policy.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/windows-deploy-worker.ps1 Status
Get-Content .production/deploy/logs/deploy.jsonl -Tail 30
```

Status shows task identity/actions/triggers, last/next run, result code, the last
checked commit, deployed service images and failed commits. `LastTaskResult=0`
means the invocation finished normally; inspect `last_result.status` to distinguish
`noop`, deployment success, infrastructure deferral, or a previously failed commit
being skipped. A failed build/check/activation returns 1. Pausing prevents new
scheduled runs and leaves an active deployment to finish:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/windows-deploy-worker.ps1 Pause
# Wait for Status to show no active run before doing maintenance.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/windows-deploy-worker.ps1 Run
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/windows-deploy-worker.ps1 Resume
```

`Run` manually checks/deploys main through the same lock and checks. Do not use the
old mutable `:local`/`:newrelic` tags or the IDE Compose Start/Build operations for
deployment after the worker takes ownership: doing so can select old images and
will trigger the worker's drift guard. Existing read-only Verify/Status/Logs and
online Backup operations remain useful. No-op polls do not restart containers or
continually emit logs.

After fixing a failed main commit's cause, explicitly permit another attempt:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/windows-deploy-worker.ps1 Retry
```

Retry clears only the current main's failed-commit suppression. Ordinary failures
do not stop consideration of newer main commits. Network/Docker deferrals are
retried naturally and do not poison a commit. Repeated deferral diagnostics are
limited to one per reason/commit per 15 minutes. A recovery-blocked database must
be repaired before Retry or a newer commit can proceed.

## Rollback, migrations and interruption recovery

Activation failure attempts to restore the previous affected image/config set
only when rollback is allowed. It verifies the restored deployment before
recording rollback success. It never restores an older database automatically.
The failed target stays suppressed so the next poll does not redeploy it.

For a completed, compatible deployment, manual rollback uses the saved previous
release and similarly suppresses the rolled-back target:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/windows-deploy-worker.ps1 Pause
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/windows-deploy-worker.ps1 Rollback
```

The first adopted baseline has no previous worker release to roll back to. Keep
backups and retained images; do not prune volumes or delete state/config files.

Changed Alembic files or `production/manage_db.py` make migration rollback unsafe
by default. To declare a migration compatible with the currently deployed Python
release, add `production/migration-compatibility.json` containing:

```json
{"backward_compatible_with": "<full source_sha of the currently deployed backend>"}
```

The worker also starts the **previous backend image against the migrated copy**
and checks its APIs before using that declaration. The declaration is the
migration author's compatibility contract; the API checks are not proof of every
possible application behavior. A failed/unknown migration is always blocked; no
declaration can authorize rollback before the migration has returned successfully.

After a power loss or interrupted activation, the next run reads the durable
journal and attempts compatible rollback before processing new main. If rollback
is unsafe or cannot be verified, the journal and blocked state are retained and a
critical event is emitted. To retry a compatible interrupted rollback:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/windows-deploy-worker.ps1 Recover
```

For an unsafe migration, pause automation and have an operator finish/fix the
migration, or restore a verified backup with all writers stopped using the
[database recovery procedure](windows-deployment.md). Choose the complete previous
or target image/config set recorded in `state.json`; do not mix arbitrary image
versions. Then:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/windows-deploy-worker.ps1 AcceptRecovery
```

AcceptRecovery performs no database writes. It accepts only a full known previous
or target image set with passing local/public APIs/assets, SQLite quick_check and
an exact match between the live Alembic revision and that backend image's heads.
It refreshes runtime identities, clears the journal/block and keeps the failed
target suppressed until an explicit Retry. External manual deployments or
intentional protected hosting changes require a reviewed baseline/policy update;
the worker never silently adopts arbitrary containers.

## Updating or removing the worker

The installed worker/logger snapshot is pinned. A push containing only automation
or dashboard administration code does not self-modify a running deployment
worker. Review/pull those changes into the IDE checkout, pause and wait for any
active deployment, then update the snapshot/task:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/windows-deploy-worker.ps1 Install
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/windows-deploy-worker.ps1 Verify
```

Install preserves state, immutable releases and production containers. Verify
checks owner SID, InteractiveToken mode, IgnoreNew, pythonw action, working
directory, both triggers, and a newly requested task run's result. To remove the
automation after its active run finishes:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/windows-deploy-worker.ps1 Uninstall
```

Uninstall removes only the task; it retains production, source releases, images,
logs, configuration and recovery state. Release worktrees, browser/dependency
caches, backups and old image tags are retained rather than automatically pruned.
Review disk usage periodically; never remove a worktree/config/image referenced
by the current manifest, previous release or an active recovery journal. Temporary
test resources carry an installation-specific label and are the only containers/
networks the worker removes automatically. It never prunes Docker volumes.

## Observability and Windows availability

Logs contain static events, commit SHA, affected services, phase, correlation ID,
duration, outcome and rollback result. Child command output is held only in a
bounded 1 MiB memory buffer, never copied raw into log files. Exceptions/headers,
Git tokens and credential-bearing errors are not serialized. Local worker logs
rotate at 1 MiB with three backups (about 4 MiB total).

The existing sanitized New Relic exporter forwards important deployment summaries
and failures at the existing configured cap (10 events/minute per process here).
No-op summaries are emitted once per newly evaluated head, not every poll.
Credentials are read from the existing private ingest-key file; the User API key
is not used by the worker or passed into containers. Search New Relic Logs with:

```sql
SELECT timestamp, event, commit_sha, services, phase, outcome, rollback, reason
FROM Log WHERE application = 'Arizona Election Explorer (Production)'
AND service = 'deploy_worker' SINCE 1 day ago LIMIT 100
```

App logging and the worker share the same safe formatter/export implementation;
deployment fields and summary events were explicitly allowlisted. Existing Docker
rotation is preserved. Export is still best effort and consumes the account's
shared ingestion allowance; there is no zero-cost guarantee.

The task needs its owner signed in. Locking the desktop is fine; sign-out, reboot
before sign-in, sleep, power loss and connectivity outages still affect hosting.
Docker Desktop's own AutoStart setting remains false. If its engine is unavailable,
the worker may launch the installed Docker Desktop with a hidden startup request
at most once per ten minutes and defer until a later poll. It does not install or
reset Docker, bypass prompts, enable automatic Windows login, or disable updates.
Current AC/DC idle sleep and hibernate timeouts are Never; those settings were
inspected and left unchanged. The task does not wake a manually sleeping PC.

## Verification — October 29, 2026

- 53 focused worker/export checks passed on Windows using a fresh private temp
  directory. An earlier run's shared pytest temp permissions were a test-harness
  issue; the clean isolated run passed.
- 79 isolated Linux logging/deployment/migration/refresh/SSE checks passed, with
  one existing Starlette/httpx deprecation warning.
- The real candidate path passed online-backup copying, candidate-only migration,
  API checks, npm unit checks and all reviewed browser specs without activation.
- Existing live files and the verified frontend deployment record were audited
  before adopting immutable aliases and exact running image IDs. The baseline's
  source SHA denotes verified equivalent runtime inputs, not a retroactive claim
  that legacy images originally had Git revision labels.
- Task owner, action, working directory, two-minute/sign-in triggers and locking
  policy were read back. A fresh scheduled invocation returned result 0 and
  `noop` for `ea59ccee8f232a88d207875140fef191975d1624`; no production restart was
  forced. A subsequent two-minute timer run also returned result 0. Worker source
  and installed snapshot hashes matched.
- New Relic returned HTTP 202 for worker adoption/no-op diagnostics. A setup-time
  public health probe was initially rejected for urllib's generic user-agent;
  using the explicit `ArizonaElectionDeploy/1.0` identity fixed it without changing
  TLS or Cloudflare settings. Production remained healthy.

No production failure, unsafe migration, real rollback, sign-out/reboot or Docker
shutdown was deliberately induced. Failure/rollback/interruption behavior is
covered by mocks/disposable resources; reboot catch-up awaits a natural event.

References: [Task Scheduler repetition](https://learn.microsoft.com/en-us/windows/win32/taskschd/repeating-a-task),
[IgnoreNew instance policy](https://learn.microsoft.com/en-us/windows/win32/api/taskschd/ne-taskschd-task_instances_policy),
[Compose project/path behavior](https://docs.docker.com/reference/cli/docker/compose).
