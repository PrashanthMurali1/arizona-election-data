> Scheduling update (2026-10-29): Relay now owns deployment and refresh scheduling. The legacy deployment task and Docker cron service/container were removed. Scheduler/cron commands below describe historical cutover procedures; do not run them. Use [current deployment and recovery operations](automatic-deployment.md).

# Local production hosting on the M1 Mac

> Historical Mac execution report. For the Windows migration, current verification status, data export/import, PowerShell operations and approved cutover procedure, use [Windows deployment](windows-deployment.md). Statements below about active services and login startup describe the Mac deployment, not the Windows computer.

The application is live at **https://azelections.app**, using the existing **azelections-prod** Cloudflare Tunnel after explicit user approval. Local viewing remains **http://127.0.0.1:8080**. The `public` Compose profile is active. No router ports, public backend port or database port are exposed; the UI is unchanged.

## Execution report — October 28, 2026

### Public activation after approval

The user configured the published application route and confirmed the proxied apex CNAME for `333d2484-25bd-408c-94d6-a0d1e44bf19c.cfargotunnel.com`, then explicitly approved public activation. The existing `azelections-prod` connector was started with `docker compose --profile public up -d --wait tunnel`. Connector readiness passed. No new tunnel, account API token, DNS change or route replacement was made by the agent.

Public checks passed on October 28: valid TLS 1.3 for `azelections.app`, certificate expiring January 26, 2027; HTTPS root/API/deep links return 200; HTTP redirects with 308, preserving path/query. Caddy enforces the redirect only for this hostname when Cloudflare forwards the visitor's HTTP scheme, avoiding an HTTPS loop and leaving local loopback access unchanged. API responses carry `Cache-Control: no-store, no-transform` and Cloudflare reported `CF-Cache-Status: DYNAMIC`. The certificate check is retained in `.production/public-tls-check.json`.

All **12 browser tests passed against https://azelections.app**, using `--workers=1`. Coverage includes historical catalog/views, county/district maps, sorting, selection, responsive layout, no minute polling, actual committed civicAPI import → Cloudflare SSE → open browser, and recovery of a missed import after reconnect. No election figures were independently verified. Initial local DNS resolution lagged behind DNS query results; this cleared, and final checks used normal DNS with certificate verification enabled, without resolver overrides.

Frontend, backend, scheduler and tunnel are healthy. Only loopback port 8080 is published; backend/database/tunnel ports remain private. The six-hour cron schedule is unchanged, the old LaunchAgent remains disabled, and Docker Desktop's saved login-start setting is enabled. Availability still depends on the Mac being powered, Docker running and network access.

Current start/stop/status commands include both active profiles:

```sh
docker compose --profile scheduled --profile public up -d --wait
docker compose --profile scheduled --profile public ps
docker compose --profile scheduled --profile public logs --tail 100
docker compose --profile scheduled --profile public stop

# Unpublish immediately without deleting data or changing DNS:
docker compose --profile public stop tunnel
# Resume the already-approved existing tunnel:
docker compose --profile public up -d --wait tunnel
```

Stopping the connector leaves the user-managed DNS/route in place; Cloudflare will show an unavailable-origin/tunnel error until resumed. To remove the public hostname permanently, remove only that hostname route and its associated apex CNAME manually in the dashboard. Preserve all other records/settings. No credentials appear in these commands or this report.

Latest local verification: the frontend now runs **Caddy 2.11.7**, replacing nginx, with Docker network alias **caddy** and internal port **80**. `http://caddy:80/api/health` returned healthy from the backend container, exercising Caddy → FastAPI → SQLite. The host remains loopback-only at `http://127.0.0.1:8080`; the Cloudflare connector is stopped.

The Caddy image build/config validation, full production smoke checks and **all 12 browser checks passed**. Browser checks were run serially on the M1 (`--workers=1`). The initial parallel run hit a five-second House loading timeout; the House API returned in 0.606 seconds in a direct check and the House browser test passed serially. The SSE cache assertion now accepts either `no-cache` or the stronger `no-store`, and requires `no-transform`. No application design or election-data correction was made. All 19 historical API fingerprints matched the pre-Caddy baseline. SQLite `quick_check` returned `ok`, with WAL retained. The scheduler remains healthy at 00:00/06:00/12:00/18:00 Asia/Kolkata.

Cloudflare inventory is **user-confirmed dashboard information**: `azelections-prod` has no published application routes and `azelections.app` has zero DNS records. No existing record needs replacing. Manual configuration steps for the requested origin **http://caddy:80** are in [existing tunnel activation](cloudflare-activation.md). The user subsequently configured the route/CNAME and explicitly approved activation. The agent made no Cloudflare route, DNS or rule changes; the connector and public HTTPS/browser checks have now passed. Docker Desktop login startup is enabled and confirmed.

- Frontend, backend and permanent scheduler are running and healthy, using native `arm64` images. The only published port is `127.0.0.1:8080`.
- Initial database/raw backup: `.production/backups/before-production-20261028T092037796364Z/`. Initial database SHA-256: `5019775353cecc38735d05816fd1bbaed81d7836d51f00a4f7c69646c30064c5`. Migration and current online backups are additional `.db` files in `.production/backups`.
- A final standalone production backup is `.production/backups/backup-20261028T093704190814Z.db`. The backup helper explicitly closes/checkpoints its connections and exports DELETE-journal backups, so recovery does not depend on WAL/SHM sidecars. The live volume remains in WAL mode.
- The old host LaunchAgent is removed/unloaded. Permanent cron is `0 0,6,12,18 * * *`, Asia/Kolkata; next slot after preparation is **October 28 at 18:00 IST**. Startup refresh succeeded. Timed cron was exercised at **14:58 and 14:59 IST** using a temporary one-minute rule in a disposable container; that container was removed. A natural six-hour slot has not yet been observed.
- Production smoke checks passed: committed import → SSE notification through the production proxy; repeated import without new records; cross-container lock exclusion; deliberate network failure retaining metrics; successful recovery; container recreation preserving data; SSE reconnect; unchanged fingerprints for all **19 historical catalog views**. The retained snapshot counts were 69 contests, 2,271 vote-result rows, 278 metric observations and 11 publication snapshots. These are storage checks, not election reconciliation.
- **16 backend tests, 7 frontend unit tests and all 11 existing browser tests passed.** An additional real production browser test passed for committed-import delivery and missed-import recovery while preserving selection and sorting. Both Docker production image builds passed.
- The existing Cloudflare connector is healthy and the approved public site passed certificate-validated HTTPS and all 12 public browser tests. DNS/routes were configured by the user; no account API access was used. See the public activation report below for details.
- Implemented files: `compose.yaml`, `.dockerignore`, `production/` Dockerfiles/Caddy/database/cron/refresh/route helpers, `scripts/prepare_production.py`, `scripts/check_production.py`, environment/ignore documentation, SQLite connection timeout, production browser configuration/test and backup/restore tests. No application UI redesign was made.

## Files and data ownership

- `compose.yaml`: production frontend/Caddy, FastAPI, database initialization/migration helpers, opt-in cron scheduler and opt-in Cloudflare connector.
- `production/*Dockerfile`: native ARM64 builds on this Mac. The backend uses the existing pinned Python requirements; frontend uses `npm ci` and the production build.
- `production/Caddyfile`: one HTTP origin for static assets, React deep links and `/api`. Caddy flushes SSE immediately and preserves cancellation on browser disconnect. The API's 15-second heartbeat keeps idle streams active. The Compose service remains `frontend`, with the network alias `caddy` and internal port 80.
- Docker volume `az-election-explorer_state`: SQLite database, WAL/SHM files, importer lock, job audit and rotating job logs. Keeping SQLite on the VM's native filesystem avoids sharing SQLite locks over the Mac bind mount.
- `.production/raw`: retained raw sources and new civicAPI responses, shared with the importer and API at `/app/data/raw`.
- `.production/backups`: online SQLite backups and the initial raw-source backup, outside the Docker volume.
- `.production/seed`: the immutable initial database snapshot, mounted read-only for first-time initialization.
- `.production/secrets/tunnel-token`: private token file, not an environment value, command argument or image layer. All `.production` files and `.env` are ignored by Git and Docker build contexts.

The original `backend/local/elections.db` and `data/raw` remain intact. The production volume is a separate populated copy. Do not use `docker compose down -v`, reset Docker Desktop storage, or delete this named volume without verified independent backups. A Docker volume is persistent storage, not a backup.

## Initial private setup

Run commands from the repository root:

```sh
# Start the installed runtime, then wait for `docker info` to succeed.
open -a Docker
docker info

# Optional local configuration; edit UID/GID to match `id -u` / `id -g`.
cp .env.example .env

# Exactly once: back up the existing database + raw files and prepare the seed.
.venv/bin/python scripts/prepare_production.py

# Build the shared backend only once, plus the production frontend.
docker compose build backend frontend
docker compose up -d --wait backend frontend
docker compose ps -a
curl --fail http://127.0.0.1:8080/api/health
```

`prepare_production.py` refuses to replace an existing seed. It takes the existing importer lock while making an SQLite online backup and copying retained raw files. Initialization seeds only an empty Docker volume and refuses an empty/unreadable database; it does not bootstrap elections. Migration backs up production SQLite before `alembic upgrade head`, enables WAL, and retains existing records. Connections wait up to 15 seconds for competing SQLite writers. Use one backend worker and one scheduler; existing cross-process file locking prevents overlapping refreshes.

## Scheduler cutover

The `scheduled` profile starts a dedicated cron process, not a timer inside a web worker. It runs at **00:00, 06:00, 12:00 and 18:00 Asia/Kolkata (IST)** by default, matching the previous Mac schedule. `REFRESH_TIMEZONE` and `REFRESH_INTERVAL_HOURS` in `.env` control it; the interval must divide 24. The container sets the cron daemon's actual system timezone, not just a browser timezone. It catches up once at container startup, then uses cron slots. Downtime can miss slots; the next startup refresh catches up once.

Test the replacement against the production copy first. Only after successful checks, disable the old host job and start the permanent container:

```sh
.venv/bin/python scripts/check_production.py
PLAYWRIGHT_BASE_URL=http://127.0.0.1:8080 npm --prefix frontend run test:e2e

# Host change: removes only the old schedule, retaining its data and logs.
.venv/bin/python scripts/manage_early_vote_schedule.py remove
docker compose --profile scheduled up -d --wait scheduler
docker compose --profile scheduled ps

# Manual production refresh uses the same lock, raw retention and job audit.
docker compose exec --user app scheduler python production/refresh_job.py
docker compose exec backend cat backend/local/early-voting-refresh-status.json
```

The check script deliberately fails one refresh using an unavailable local proxy, checks failure preservation, then performs a successful recovery. It does not corroborate election figures. Stop the scheduler before re-running these mutating checks. Avoid enabling the LaunchAgent and container scheduler together; after cutover, the original host database is archival and production updates only the Docker volume.

SSE observes the shared `/app/backend/local/early-voting-refresh-status.json` written after import transactions finish. The backend and worker share the same named volume. The homepage reuses its in-memory cache and revalidates on changed revisions or after five minutes; entry/reconnect recovers missed updates. There is no browser-triggered import. See [browser caching](browser-caching.md). Raw retention, timeouts, zeros/missing values, failure preservation and snapshot ordering remain in the existing importer.

Change the interval/timezone with:

```sh
# Edit .env, then recreate only the scheduler.
docker compose --profile scheduled up -d --no-deps --force-recreate --wait scheduler
docker compose exec scheduler cat /etc/cron.d/early-voting
```

## Start, stop, logs and updates

```sh
docker compose --profile scheduled up -d --wait
docker compose --profile scheduled stop
docker compose --profile scheduled logs --tail 100 frontend backend scheduler
docker compose exec backend tail -n 50 backend/local/logs/early-voting-refresh.log
docker compose exec backend tail -n 50 backend/local/logs/early-voting-scheduler.log

# Back up before updating. Stop all data writers/readers for schema changes.
docker compose run --rm --no-deps backend python production/manage_db.py backup
docker compose --profile scheduled stop
docker compose build backend frontend
docker compose run --rm --no-deps migrate
docker compose --profile scheduled up -d --wait
```

If the tunnel has later been authorized and activated, also stop it before maintenance with `docker compose --profile public stop tunnel`, and restart it after local checks pass. Migration errors stop dependent services rather than serving a newly created empty database. Keep the previous Git revision and built images before updates; immutable image IDs/digests can be inspected with `docker image inspect` and tagged for rollback. After restoring compatible data if needed, check out the previous code revision, rebuild its images and restart locally before re-enabling the tunnel. Do not roll old code back onto a schema it cannot read.

Container stdout/stderr use Docker's JSON log driver with three 10 MiB files per container. Import audit and scheduler diagnostic files rotate at 1 MiB with three backups. Scheduler shutdown stops new cron slots and allows an active importer up to 100 seconds to finish; Compose allows 120 seconds before forced shutdown. SQLite transactions protect interrupted writes.

## Backup and restore

```sh
# Safe online DB backup includes committed WAL contents.
docker compose run --rm --no-deps backend python production/manage_db.py backup

# For a matching DB/raw recovery point, stop the scheduler while copying raw files.
docker compose --profile scheduled stop scheduler
docker compose run --rm --no-deps backend python production/manage_db.py backup
tar -czf .production/backups/raw-snapshots-$(date +%Y%m%dT%H%M%S).tar.gz -C .production raw
docker compose --profile scheduled up -d --wait scheduler

# Restore only while backend/scheduler are stopped. Replace BACKUP_NAME.db.
docker compose --profile scheduled stop
docker compose run --rm --no-deps backend python production/manage_db.py restore --offline --backup /backups/BACKUP_NAME.db
docker compose run --rm --no-deps migrate
docker compose --profile scheduled up -d --wait
```

Restore validates the supplied database and creates a separate `before-restore-*.db` rollback backup before replacing anything. Retained raw files are content-addressed: preserve newer raw files when restoring an older database, and restore missing raw files from the corresponding archive without deleting unrelated files. Store additional copies of backups outside this Mac; local disk loss affects both Docker and `.production`. The initial backup location is recorded in `.production/preparation.json`.

## Active Cloudflare configuration

No local Cloudflare credentials, existing tunnel configuration or Cloudflare account connection was available during preparation. Public DNS lookups returned no A, AAAA or CNAME answer for `azelections.app`; this does not substitute for inspecting the authenticated zone. Before changing anything, inspect/export the zone's current DNS records and existing tunnel routes. Preserve unrelated records, especially MX/TXT and other hostnames.

Use the existing remotely managed tunnel **azelections-prod**, ID **333d2484-25bd-408c-94d6-a0d1e44bf19c**. Do not create a replacement. Account authentication and the approval boundary are documented in [existing tunnel activation](cloudflare-activation.md). Proposed application ingress is retained in `production/cloudflare-route.json`; merge it into the authenticated existing configuration, preserving unrelated routes.

| Item | Proposed value |
| --- | --- |
| Published hostname | `azelections.app` |
| Origin service | `http://caddy:80` |
| HTTP Host header | `azelections.app` |
| Catch-all | `http_status:404` |
| DNS record | Proxied apex CNAME `azelections.app` → `333d2484-25bd-408c-94d6-a0d1e44bf19c.cfargotunnel.com` |
| TLS | Cloudflare edge certificate for `azelections.app`; origin traffic stays within Docker |
| Cache rule | Bypass cache for this hostname's `/api/*`, including SSE |

The supplied UUID identifies the existing tunnel but does not authenticate the connector. The user requested least-privilege access and preservation of the existing configuration: use the connector-only flow in [existing tunnel activation](cloudflare-activation.md). No account API edit permissions are requested. If obtaining the existing tunnel's connector token manually, save it **locally**, without pasting it into chat or shell command arguments:

```sh
mkdir -p .production/secrets
chmod 700 .production/secrets
.venv/bin/python - <<'PY'
from getpass import getpass
from pathlib import Path
p = Path('.production/secrets/tunnel-token')
p.write_text(getpass('Cloudflare Tunnel token: ').strip() + '\n')
p.chmod(0o600)
PY
```

The connector runs as the configured app UID so it can read the private file. Compose injects the token at `/run/secrets/tunnel_token`; it is not baked into the image or passed in the process arguments. The prepared connector uses `cloudflare/cloudflared:2026.10.3`, with a private `/ready` health check and no published ports.

**Only after the local checks pass and public activation is approved**, apply the reviewed hostname/ingress configuration to that new tunnel, add the single proxied CNAME if no conflicting apex record exists, and start the connector:

```sh
docker compose --profile public up -d --wait tunnel
docker compose --profile public logs --tail 50 tunnel
curl --fail https://azelections.app/api/health
curl --fail -N --max-time 20 https://azelections.app/api/elections/az-2026-early-voting/updates
```

The final SSE command normally ends with curl's timeout after receiving an initial revision and a heartbeat; a timeout after valid streamed events is expected. Check HTTPS, deep links and an update/reconnect through Cloudflare before declaring the public site ready. Confirm the edge certificate is active and configure HTTP→HTTPS for this hostname without altering unrelated zone behavior. Do not force-overwrite conflicting DNS. No `www` hostname is added by this configuration.

To unpublish, stop the connector and remove only the reviewed hostname route/DNS record if desired. Local hosting remains available. A Cloudflare token alone does not authorize public activation in this task.

References: [Cloudflare Tunnel setup](https://developers.cloudflare.com/tunnel/get-started/), [connector parameters/token files](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/configure-tunnels/run-parameters/), [Compose dependency ordering](https://docs.docker.com/compose/how-tos/startup-order/), [Compose secrets](https://docs.docker.com/compose/how-tos/use-secrets/).

## Reboot, sleep and power

The user enabled Docker Desktop's **Start Docker Desktop when you sign in** setting. Its saved `AutoStart` value was confirmed **true** on October 28, 2026. Automatic macOS login was not enabled.

Enable Docker Desktop's **Start Docker Desktop when you sign in** setting if desired. `restart: unless-stopped` restarts existing containers when the Docker daemon starts; it does not boot Docker Desktop, log in to macOS, or restart containers deliberately stopped with Compose. After login, start Docker Desktop, wait for `docker info`, then run the documented Compose start command if necessary. Neither Docker nor Cloudflare Tunnel keeps a powered-off or sleeping Mac serving traffic. Network outages also interrupt public availability. Keep the Mac powered and connected for the desired hosting hours; consider power/sleep settings explicitly rather than relying on container restart policies.
