# Windows deployment and migration

The Windows migration keeps the existing Compose services, single-worker FastAPI backend, Caddy frontend, SQLite named volume, cron refresh worker and remotely managed Cloudflare Tunnel. Preparation does not activate the Windows public connector. Run commands from the repository root unless stated otherwise; stop on any command failure.

## Verified status — October 28, 2026

- Host: Windows build 26200, AMD64. Node 24.15.0/npm 11.14.1 and Python 3.14 are available. Production still uses Python 3.13 and Node 22 inside its unchanged Dockerfiles.
- Docker Desktop 4.97.0 installed successfully through WinGet. Its CLI reports 29.9.2 and Compose reports 5.6.1. After the user completed WSL installation, the engine reports `linux/x86_64`. Both production images build successfully on Windows. Both default and public/scheduled Compose configurations pass `docker compose config --quiet`.
- WSL is now verified at version 3.0.3.0 with kernel 6.18.54.1-1. Earlier installation attempts failed with `0x80072ee2`; that prerequisite is resolved. No reboot was initiated by the agent.
- Frontend: `npm.cmd ci`, all 7 unit tests and production build pass on Windows. Python: all 4 standalone migration tests and 11 backend checks (backup/restore, Cloudflare inspection and retained 2026 participation API tests) pass. These tests use disposable databases and synthetic credentials.
- Linux container checks: all 5 migration tests pass, including a complete export/import round trip with retained job audit and nested source manifests. All 5 backup/restore and Cloudflare inspection tests pass in a disposable container without network access or production mounts. Caddy validates the built configuration. The pinned cloudflared 2026.10.3 image pulls and reports its version on AMD64; it was never started as a connector.
- PowerShell helper syntax and its real healthy-engine preflight pass. Its missing-Docker guard was exercised before installation. Build also succeeded directly through Compose; app start/verify remain pending data transfer.
- A broader native backend run could not complete: raw House calendar HTML files in the checkout do not match their recorded hashes, even after LF/CRLF normalization. Original mixed source bytes may have been lost when initially committed. Do not change recorded hashes or regenerate election figures to bypass this. Transfer the original `.production/raw` from the Mac. Native Unix refresh-lock/SSE test modules also require Linux; run the full suite inside Docker once available.
- No production database, private token or `.production` state was present in this checkout. The user confirmed access to the Mac for export. No Windows app containers, scheduler or connector have been started. Live Mac state and authenticated Cloudflare settings have not been inspected in this migration session.

The end-to-end migration is pending authentic Mac data transfer, local application/container checks and approved cutover. No application containers remain running after the disposable checks. The older Mac execution reports are historical evidence only.

## Compatibility and preserved configuration

| Concern | Windows approach |
| --- | --- |
| ARM64 Mac → AMD64 Windows | Both application images rebuilt successfully from source on Windows; no forced `platform`, copied virtualenv, `node_modules` or ARM64 image. Pinned Caddy and cloudflared tags are available on AMD64. |
| Docker engine | Docker Desktop with WSL 2 and **Linux containers**. The application runs cron, `fcntl`, Unix ownership and signals inside Linux. |
| SQLite locking | Keep `az-election-explorer_state` on Docker's Linux filesystem. Never bind-mount the live SQLite database onto NTFS, OneDrive or a network share. |
| Host files | Relative Compose bind mounts work with this checkout's spaces. `.production/raw`, `backups` and read-only `seed` stay on the host. Create/import them before startup. |
| Identity | `APP_UID=501`, `APP_GID=20` are valid **container** IDs on Windows too. Keep them consistent with existing volume ownership; they are unrelated to Windows accounts. |
| Line endings | Linux code/config uses LF; PowerShell uses CRLF. Retained data uses LF with explicit exceptions for checksum-sensitive CRLF snapshots. The Senate secondary 2024 CSV requires LF. Original Mac raw files must be transferred byte for byte. |
| Permissions/secrets | Linux mode bits protect named-volume state. Windows uses NTFS ACLs, not `chmod`, for private host files. Token saving now protects its parent directory before writing. |
| Networking | Only `127.0.0.1:8080` is published. Backend/database remain private. Tunnel origin is `http://caddy:80` on the shared Compose network, never Windows loopback. |
| Schedule | One Linux cron worker, default 00:00/06:00/12:00/18:00 Asia/Kolkata. Startup performs a catch-up refresh. Do not run competing Mac and Windows production writers. |
| Native tooling | Use `npm.cmd`/`npx.cmd` if PowerShell blocks npm scripts. Host Python is optional except for the standard-library import/token helpers. Windows Python installs pinned timezone data from requirements. |

## Verify runtime or recover installation

Runtime installation is complete on this computer and Docker's Linux engine is verified. The installation commands below are retained for recovery or another Windows host.

Use an administrator PowerShell terminal for Windows feature installation. These are recovery commands, not commands that succeeded during this session:

```powershell
wsl --install --no-distribution
wsl --update
wsl --status
wsl --version
```

If Windows requests a restart, save work and restart manually. If the package is still unavailable, retry `winget install --id Microsoft.WSL --exact --source winget` after resolving its download/installer error. Confirm firmware virtualization is enabled if WSL reports it disabled. Enable Docker Desktop's WSL 2 backend and Linux containers, complete any first-run prompts, then open a new terminal:

```powershell
docker version
docker info --format '{{.OSType}}/{{.Architecture}}'
docker compose version
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/windows-production.ps1 Preflight
```

The engine must report `linux/x86_64` or equivalent and include a Server section. If the current terminal cannot find the installed CLI, temporarily set `$env:PATH = 'C:\Program Files\Docker\Docker\resources\bin;' + $env:PATH`. The process-only execution-policy flag avoids changing the computer's persistent PowerShell policy. An organizational policy may still require administrator assistance.

Docker documents its [Windows installation requirements](https://docs.docker.com/desktop/setup/install/windows-install/) and [WSL backend](https://docs.docker.com/desktop/features/wsl/). Microsoft documents [WSL installation](https://learn.microsoft.com/en-us/windows/wsl/install).

## Export the current Mac production state

### Copyable prompt for the agent on the Mac

Paste this into Codex on the M1 Mac, with the existing deployment repository open:

```text
Prepare a verified migration export of my live Arizona Election Explorer
(azelections.app) from this M1 Mac for the Windows deployment already prepared.
Inspect the repository instructions and current Compose deployment first.

Keep the live Mac application, Cloudflare connector and scheduler running.
Do not perform cutover, change DNS/routes, rotate tokens, rebuild/restart live
services, bootstrap election data, or modify election figures/source hashes.

Export the ACTIVE Docker database and raw-source mount, not the archival
backend/local/elections.db or initial seed. Use the updated
production/manage_db.py export action if available. If this checkout lacks it,
add a narrowly scoped export helper that implements the following contract,
and run it in a disposable backend container sharing the existing state/raw
mounts without starting dependencies or changing the deployed image.

Hold the importer's existing early-voting-refresh.lock with exclusive flock
throughout the snapshot. Use SQLite's online backup API, export a standalone
DELETE-journal database, close all connections, verify PRAGMA quick_check is
ok and that contests is populated. Copy the current raw sources byte for byte,
plus the job status and rotating logs while holding that same lock.

Create a new .production/backups/windows-transfer-<UTC timestamp>/ containing:
  elections.db
  raw/                         (complete production raw-source directory)
  audit/early-voting-refresh-status.json  (if present)
  audit/logs/                  (if present)
  manifest.json

Write manifest.json LAST as a JSON object mapping each exported file's relative
POSIX path to its SHA-256 digest. Include nested files named manifest.json;
exclude only the export's root manifest.json. Hash every exported file and
verify the completed export against the manifest. Refuse to overwrite prior
exports. Keep all migration artifacts ignored by Git and out of Docker builds.

Report database table counts and compare raw-source checksums to existing
provenance, including data/raw/us-house/calendar/*.html. If a retained source
does not match, report it without altering either the file or recorded hash.
Do not fetch replacement sources or refresh election data for this export.

Provide the absolute export folder path, its size, validation results, and
instructions for transferring the entire folder to Windows without changing
file bytes. Do not transfer anything to an unspecified destination.

Separately identify the .env settings and existing connector-token file needed
for Windows. Do not put credentials in the export, print them, paste them into
chat, or commit them. No account API token is needed. Do not activate any
additional tunnel connector. Confirm that the live Mac services remain running
when finished. This is a rehearsal export; final cutover will require a fresh
snapshot after an explicitly approved pause of the Mac scheduler.
```

### Manual export command

The Mac's `backend/local/elections.db` and original seed are archival. Export the **active Docker volume**. Bring the updated `production/manage_db.py` to the Mac checkout first. The following command mounts only that helper into a disposable container, so it can run against the existing deployment without rebuilding/restarting the Mac backend:

```sh
# On the Mac, from its deployment checkout. Mac stays live during rehearsal export.
docker compose run --rm --no-deps --volume ./production/manage_db.py:/app/production/manage_db.py:ro backend python production/manage_db.py export
```

The helper takes the same advisory lock as the importer, makes a checked SQLite online backup including committed WAL data, and copies raw sources, last job status and rotating logs. Output identifies `/backups/windows-transfer-<timestamp>`, which is `.production/backups/windows-transfer-<timestamp>` on the Mac. `manifest.json` hashes every exported file. An interrupted export is rejected on import.

Transfer the **whole completed directory** using a trusted file-transfer method preserving file bytes. It contains `elections.db`, `raw/`, `audit/` and `manifest.json`. Do not copy an open database file, omit WAL sidecars from a live file copy, or move Docker Desktop's VM disk between architectures. Keep an independent copy of the export outside Docker storage.

Separately retain the Mac `.env` and connector-only `.production/secrets/tunnel-token` securely, or obtain the existing connector token at a hidden local prompt later. Do not copy tokens into chat. No account API token, `cert.pem`, new tunnel, DNS record or new hostname is needed. Retain optional read-only account inventory separately if available.

## Import and start privately on Windows

Choose a complete exported directory outside `.production`, for example `C:\migration\windows-transfer-<timestamp>`. Run once in a checkout without a `.production` directory. The importer refuses replacement, validates the file inventory/checksums and populated SQLite database, then prepares the raw mount and seed. It does not bootstrap or fetch election data.

```powershell
py scripts/prepare_production.py --from-export 'C:\migration\windows-transfer-<timestamp>'
if ($LASTEXITCODE -ne 0) { throw 'Import failed' }
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
# Review the Mac values before continuing; retain its interval/timezone/port choices.
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
icacls .production /inheritance:r /grant:r "${identity}:(OI)(CI)F" /T
icacls .env /inheritance:r /grant:r "${identity}:F"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/windows-production.ps1 Build
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/windows-production.ps1 Start
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/windows-production.ps1 Verify
```

Review `.env` for `APP_UID`, `APP_GID`, `LOCAL_PORT`, `REFRESH_TIMEZONE`, `REFRESH_INTERVAL_HOURS` and `CLOUDFLARE_TOKEN_FILE`. Compose sets its own Linux `DATABASE_URL`; do not substitute a Windows path into it. Do not copy `COMPOSE_PROFILES=public` or a stale `DOCKER_DEFAULT_PLATFORM=linux/arm64` into the environment. Keep cloud-sync software away from the checkout and backups. The token may remain absent during private testing.

The helper explicitly targets only backend/frontend; it never starts the scheduler or tunnel. Initialization seeds an empty volume, retains transferred audit/log files, applies Linux ownership and runs backup-before-migration. Changing the seed later does **not** replace an existing database.

## Local verification before cutover

Inspect maps, county/district selections, sorting, historical details, early-voting metrics, source links and deep-link reloads at `http://127.0.0.1:8080`. Confirm exported record counts and retained source checksums against the Mac before allowing any refreshes. Verify a stopped/recreated backend/frontend retains those records.

```powershell
# Standalone technical migration tests (host Python, no app dependencies).
py -m unittest discover -s production/tests -v
# Full backend suite in Linux; isolated temporary DBs, scheduler remains stopped.
docker compose run --rm --no-deps backend python -m pytest backend/tests -q
# Private mutating smoke test: real refresh, SSE, failure/recovery and persistence.
# This existing script assumes port 8080 and requires host requests.
.\.venv\Scripts\python.exe scripts/check_production.py

Push-Location frontend
$env:PLAYWRIGHT_BROWSERS_PATH = 'node_modules/.cache/ms-playwright'
npx.cmd playwright install chromium
$env:PLAYWRIGHT_BASE_URL = 'http://127.0.0.1:8080'
npm.cmd run test:e2e -- --workers=1
Remove-Item Env:PLAYWRIGHT_BASE_URL
Pop-Location
```

Install host requirements in a local virtualenv if using `check_production.py`; production itself does not require host dependencies. Browser production tests perform actual local imports. Do not target the public Mac site while these tests mutate Windows data. If full tests attempt to rewrite read-only packaged data as the unprivileged app user, run the disposable test container with `--user 0:0`; never change the production service's user for this purpose.

## Tunnel review and credential preparation

Retain tunnel **azelections-prod**, ID **333d2484-25bd-408c-94d6-a0d1e44bf19c**. Existing intended routing is `azelections.app` → `http://caddy:80`, Host header `azelections.app`, catch-all `http_status:404`; the proxied apex CNAME points to that UUID's `cfargotunnel.com` name. `production/cloudflare-route.json` is a template, not an authenticated export. Review **all** published routes on this tunnel in the dashboard and confirm the Windows network can serve every origin before activation. Retain API cache bypass, HTTPS redirects and unrelated records unchanged.

```powershell
# Optional: save existing connector token at a hidden prompt; no network calls.
py scripts/inspect_cloudflare.py save-connector-token
# Validate configuration without displaying token contents.
docker compose --profile public --profile scheduled config --quiet
```

The token helper checks the embedded tunnel ID, protects the NTFS parent directory and saves the token without printing it. That verifies local format/ID only; Cloudflare acceptance/readiness remains pending activation. Existing Linux UID/GID can read the Compose secret through Docker Desktop's file-sharing implementation; verify this during approved activation. If access fails, stop the connector and fix the private mount/ACL; do not publish the token or make it broadly readable.

No remote account access is needed for ordinary migration if the existing routing is as documented. Optional authenticated read-only inventory remains available through `inspect_cloudflare.py authenticate` and `inspect`. No account credentials were supplied here. Cloudflare [replicas can receive live traffic through the same tunnel](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/configure-tunnels/tunnel-availability/); starting Windows alongside Mac is a production change, not a harmless readiness check.

## Approved final cutover

Request approval only after private checks pass and current route inventory is reviewed. Proposed Cloudflare configuration diff is **zero** if it matches the existing origin. Scope of cutover: stop Mac scheduler, transfer a final consistent snapshot, stop Mac connector, start Windows connector and scheduler. Expect a short outage while the connectors switch; open SSE sessions reconnect. Retain Mac state for rollback.

1. On Mac, after approval: `docker compose --profile scheduled stop scheduler`. Confirm any legacy LaunchAgent/host writer remains disabled. Re-run the export command above with writers stopped. Keep Mac backend/tunnel serving reads while transferring the final export.
2. On Windows, stop any rehearsal scheduler and frontend/backend: `docker compose --profile scheduled stop scheduler frontend backend`. Keep tunnel stopped. Validate/import the final export in a fresh staging checkout using `prepare_production.py --from-export`; its checks run before modifying the rehearsal state. Copy its verified raw files into the Windows `.production/raw` mount and its database into `.production/backups/cutover.db`:

```powershell
# Replace both example paths with the verified staging checkout paths.
Copy-Item -LiteralPath 'C:\migration\verified-stage\.production\seed\elections.db' -Destination '.production/backups/cutover.db'
robocopy 'C:\migration\verified-stage\.production\raw' '.production/raw' /E /COPY:DAT /DCOPY:DAT
if ($LASTEXITCODE -ge 8) { throw 'Raw copy failed' }
docker compose run --rm --no-deps backend python production/manage_db.py restore --backup /backups/cutover.db --offline
if ($LASTEXITCODE -ne 0) { throw 'Restore failed' }
docker compose run --rm --no-deps backend python production/manage_db.py migrate
if ($LASTEXITCODE -ne 0) { throw 'Migration failed' }
docker compose up -d --wait backend frontend
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/windows-production.ps1 Verify
```

`restore` saves the rehearsal database before replacement. Preserve the initial audit export in staging; an existing Windows volume retains its rehearsal job files until the next Windows refresh replaces the status. Stop/review if final source inventory or schema differs unexpectedly. Do not rerun mutating smoke/browser tests after installing the final snapshot unless their imports are intentional.

3. On Mac: `docker compose --profile public stop tunnel`. Confirm it has stopped. Do not remove its route, DNS, token or state volume.
4. On Windows, after the approved Mac connector stop:

```powershell
docker compose --profile public up -d --wait tunnel
docker compose --profile public ps
docker compose --profile public logs --tail 50 tunnel
curl.exe --fail https://azelections.app/api/health
curl.exe -I 'http://azelections.app/elections/az-2026-early-voting?cutover=check'
curl.exe --fail -N --max-time 20 https://azelections.app/api/elections/az-2026-early-voting/updates
docker compose --profile scheduled up -d --wait scheduler
docker compose exec scheduler cat /etc/cron.d/early-voting
docker compose exec backend cat backend/local/early-voting-refresh-status.json
```

Confirm connector readiness, valid TLS, HTTP→HTTPS path/query preservation, public API/deep links, live committed-import SSE and reconnect behavior. An SSE timeout after receiving an initial revision and heartbeat is expected. Confirm cron's startup refresh completes and subsequently observe a natural scheduled slot. Public readiness is not established by Compose parsing or token-ID validation alone.

## Operations and rollback

```powershell
# Local status, logs, backup. The helper does not activate public profiles.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/windows-production.ps1 Status
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/windows-production.ps1 Logs
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/windows-production.ps1 Backup
docker compose --profile scheduled logs --tail 100 scheduler
docker compose --profile public logs --tail 100 tunnel

# Update after reviewing source changes; retain last known-good source/images.
docker compose --profile scheduled stop scheduler
docker compose exec -T backend python production/manage_db.py backup
docker compose build backend frontend
docker compose up -d --wait backend frontend
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/windows-production.ps1 Verify
docker compose --profile scheduled up -d --wait scheduler
# An already active connector is retained; do not start a new one during preparation.
```

For database recovery, stop scheduler/frontend/backend, run `manage_db.py restore --backup /backups/<chosen>.db --offline` in `docker compose run --rm --no-deps backend`, migrate, restart and verify as in cutover. Raw files must match the chosen backup's source history. Keep off-machine backups; a named volume is not a backup. Never use `docker compose down -v`, prune the state volume or reset Docker Desktop storage without verified recovery copies.

For immediate cutover rollback, **first** stop Windows tunnel and scheduler with `docker compose --profile public --profile scheduled stop tunnel scheduler`. On Mac restart backend/frontend if needed, then `docker compose --profile public --profile scheduled up -d --wait tunnel scheduler`. Validate public HTTPS and SSE. DNS and ingress stay unchanged. The Mac contains the final pre-cutover snapshot; any later Windows refreshes will be absent. Export/preserve Windows state before rollback and plan reconciliation/replay before another migration attempt rather than overwriting either database blindly.

Enable Docker Desktop startup at Windows sign-in if desired. Verify a real sign-out/reboot recovery after cutover; `restart: unless-stopped` requires Docker to be running and does not restart deliberately stopped services. Windows login/first-run prompts, sleep, power loss and network outages affect availability. Keep power/network available and configure sleep for the desired hosting hours. No persistent startup or sleep settings were changed by this migration.
