# Production logging

Application, scheduler and tunnel diagnostics are JSON on stdout, with UTC
`timestamp`, `severity`, `service` and static `event` fields. API failures include a
generated request correlation ID; each refresh has a generated job correlation
ID. Incoming IDs are not trusted. Successful API responses include `X-Request-ID`.
Caddy uses a Python adapter to sanitize its runtime events before stdout and
export, with the same common fields. New Relic's own brief
agent bootstrap/registration diagnostics retain its native format.

| Severity | Events |
| --- | --- |
| INFO | Backend/scheduler/tunnel start and stop; refresh start/completion with outcome and duration; tunnel connections registered |
| WARNING | Overlapping refresh skipped, provider timeout/unavailable feed, invalid job status, last successful refresh older than 12 hours, stale early-voting data observed through the activity API, handled 4xx other than routine 404 |
| ERROR | Unhandled API/database failures, handled 5xx, provider/import failures, failed refresh completion, connector failures |
| CRITICAL | Backend cannot initialize its database, SQLite corruption/not-a-database, scheduler/cron cannot operate, refresh runtime cannot initialize, connector unexpectedly exits |

Stale-source warnings occur when the activity endpoint observes existing stale
metadata. They do not fetch providers or change results. There is no new retry
loop; provider requests retain their existing timeouts. A timeout is recoverable
for serving previous data, but the job still records a failed refresh outcome.

## Reading logs and troubleshooting

Run from the repository root in PowerShell. The existing `.env` Compose override
keeps New Relic enabled.

```powershell
docker compose --profile scheduled --profile public logs --since 30m --tail 200 backend scheduler tunnel frontend
docker compose --profile scheduled --profile public ps
# Refresh JSON is also retained on the Linux state volume:
docker compose exec -T backend tail -n 50 backend/local/logs/early-voting-refresh.log
```

Start with `severity=ERROR` or `CRITICAL`, then follow the correlation ID through
that request/job. API logs record route templates and HTTP status; exceptions
record type and up to twelve filename/function/line frames. They deliberately
omit messages, SQL, source lines and local variables. Inspect the corresponding
code location and New Relic APM error trace for diagnosis. Provider errors include
only an allowlisted feed category; raw acquisition/source audits remain separate
from diagnostic logging and are not forwarded. Preserve historical audit files.

For `early_voting_data_stale` or `refresh_last_success_stale`, inspect the latest
refresh outcome and source status in the app. For connector failures, check its
health and network connectivity. The pinned cloudflared binary is supervised by a
small Python adapter: it discards raw diagnostic messages/URLs and emits static
connection/lifecycle events. This trades raw network error text for avoiding
visitor query/header disclosure. Health checks still use cloudflared directly.
Caddy removes attached request and response-header objects from runtime logs;
request access logging remains disabled.

## Volume, storage and privacy

Successful requests, health checks, 404s, SSE notifications/heartbeats and polling
are not logged individually. Unhandled health-check errors remain important and
are logged. Python warnings/errors with the same event, route, status, exception
type and feed are suppressed for five minutes per process. The next occurrence
after that window includes `suppressed_count`; there is no extra timer log. The
limiter keeps at most 1,024 keys. Critical events are never suppressed. Duplicate
Uvicorn tracebacks for already-logged exceptions are suppressed. Caddy samples
repeated messages; the connector uses the same Python limiter.

All Compose services retain Docker's `json-file` rotation: 10 MB per file, three
files per container (approximately 30 MB each). Refresh jobs additionally retain
one 1 MiB JSON file and three backups (approximately 4 MiB total). The former
`early-voting-scheduler.log` is no longer written; old rotated files are retained,
not deleted. Container recreation can discard that container's Docker log history;
the refresh file survives on the state volume. This is incident diagnostics, not
an indefinite audit archive.

Application logs use an allowlist of static identifiers, numeric metadata and
safe exception locations. They do not serialize messages, raw paths, queries,
request/response headers, bodies, cookies, credentials, tokens or SQL. Do not add
dynamic/user-provided event names or route templates. New Relic additionally
strips exception messages from APM error traces and retains SQL obfuscation.

`APP_LOG_LEVEL=INFO` is the default. Set it in the ignored `.env` and recreate the
backend and scheduler to raise the minimum severity:

```powershell
docker compose --profile scheduled up -d --no-deps --wait backend scheduler
```

Supported values: DEBUG, INFO, WARNING, ERROR, CRITICAL. DEBUG does not enable
request payload/access logging or raw third-party messages. WARNING suppresses
lifecycle summaries; keep INFO for routine operations. Caddy and the connector
keep fixed safe logging policies; do not enable cloudflared's raw debug logs.

## New Relic free-tier policy

Verified October 29, 2026 against [official pricing](https://newrelic.com/pricing)
and [billing documentation](https://docs.newrelic.com/docs/accounts/accounts-billing/new-relic-one-pricing-billing/new-relic-one-pricing-billing/):
100 GB/month of free ingest is shared across telemetry, not a separate log budget.
Pricing and behavior beyond that allowance depend on the account's plan and
settings. This implementation does not guarantee free-tier usage or a zero bill.

Both `application_logging.enabled` and `application_logging.forwarding.enabled`
are false to prevent automatic forwarding of raw LogRecords. The sanitized Logs
API exporter described below is enabled instead. Existing APM transactions,
errors, metrics and distributed traces also consume ingest. External integrations
or other apps may contribute to the account's total usage. Disabling automatic
log instrumentation does not disable APM error collection.

Selected logs are now exported asynchronously via the official New Relic Logs
API from all four services. WARNING, ERROR and CRITICAL events are eligible,
along with the small startup/shutdown and refresh-completion summaries. Normal
requests and heartbeats remain excluded. Events are serialized through the same
safe formatter and duplicate filter before entering the export queue. The key is
mounted privately in each service and sent only in the HTTPS authentication
header. Cron explicitly inherits the export flags, never the key itself.

Each process selects at most 10 events/minute by default, with a 100-event memory
queue and batches of at most 10. Oversized exception details are omitted above
8 KiB. HTTP calls run on a daemon thread with a five-second timeout; failures
cause a sixty-second backoff, a local diagnostic, and loss of that failed batch.
Queue overflow, the rate cap, shutdown and connectivity failures may also drop
forwarded logs; local rotating logs remain the recovery source. Critical events
are complete locally but subject to the export cap. There is no disk export
spool and no backfill of logs produced before this was enabled. Counters/limits
reset when processes restart; the cap is not an account/monthly budget guarantee.

Set `NEW_RELIC_LOGS_PER_MINUTE=10` (allowed range 1–60),
`NEW_RELIC_LOGS_REGION=US`, or `NEW_RELIC_LOGS_ENABLED=false` in `.env` and recreate
the affected services to change export settings. Automatic APM log forwarding
stays disabled: the sanitized Logs API exporter is the sole log shipping path.
Existing APM telemetry **and these selected logs** consume the shared ingest
allowance. No paid feature or account billing setting was enabled.

In New Relic, open Logs and filter `application` to
`Arizona Election Explorer (Production)`, then filter `service` to `backend`,
`scheduler`, `refresh`, `frontend` or `tunnel`. Backend logs also attach APM
linking metadata when the agent has it available. For example, run this NRQL:

```sql
SELECT timestamp, severity, service, message, correlation_id
FROM Log
WHERE application = 'Arizona Election Explorer (Production)'
SINCE 30 minutes ago LIMIT 100
```

A local `log_export_connected` event confirms that New Relic returned HTTP 202
for the first batch from that process. It does not assert UI indexing. Allow a
few minutes for the Logs UI. A local `log_export_delivery_failed` means delivery
failed; raw HTTP error text is deliberately omitted to protect credentials.

In New Relic, review the
account's usage/billing page, configure a data-usage alert appropriate to your
shared monthly budget, and confirm no separate integration forwards Docker logs.
Do not enable automatic agent forwarding in the installation wizard. Keep exactly
one forwarding path with filtering and redaction **before ingestion**. A rate cap alone
is not a monthly budget cap, and server-side query filters do not reduce ingest.
See the [Logs API](https://docs.newrelic.com/docs/logs/log-api/introduction-log-api/),
[Python log forwarding](https://docs.newrelic.com/docs/logs/logs-context/configure-logs-context-python/)
and [exception message stripping](https://docs.newrelic.com/docs/apm/agents/python-agent/configuration/python-agent-configuration/).

Windows sleep, Docker shutdown, network/power loss and a stopped app cannot send
logs. Configure an external uptime monitor on
`https://azelections.app/api/health` and connect its failures to your notification
destination. Account-specific monitor allowances should be checked before setting
its frequency and locations. No notification destination or account billing
settings were changed by this deployment.

## Deployment verification — October 29, 2026

The initial local-only logging phase was deployed to the existing Windows host. All four services were healthy, the local
20-entry catalog/detail/deep-link verification passes, public HTTPS health,
catalog/activity/deep-link requests return 200, and the New Relic agent registered
again. The scheduler's ordinary startup refresh completed with exit code 0 and
emitted structured start/completion events sharing a job ID. A future natural
six-hour cron slot has not yet been observed for this revision.

All 26 isolated logging, migration, refresh and SSE tests passed (one existing
Starlette/httpx deprecation warning). The tests used disposable databases/data
copies with no production mounts or network. Additional isolated probes verified
unprivileged cron stdout routing and removal of synthetic query/header secrets
from a Caddy proxy error. Repeated live health checks generated no request logs;
no failures were deliberately injected into production. Docker/Caddy configuration
and effective New Relic privacy/forwarding settings passed validation.

Pre-deployment recovery database:
`.production/backups/backup-20261029T055553353026Z.db` (UTC filename).

### Log forwarding enabled — October 29, 2026

The user clarified that logs must be visible in New Relic. Sanitized Logs API
forwarding is now enabled for backend, scheduler, refresh jobs, frontend and
tunnel. Each process logged `log_export_connected`, confirming HTTP 202 acceptance
of its first batch. This verifies ingest acceptance; the New Relic Logs UI was
not inspected from this session. Existing log files are not backfilled.

All 32 focused logging/export, migration, refresh and SSE tests passed using
disposable copies with network disabled. The proxy wrapper separately passed
an isolated frontend/privacy smoke check. All four live containers are healthy,
and the ordinary startup refresh completed successfully. Automatic APM log
forwarding remains off to prevent a second ingestion path.

Pre-forwarding recovery database:
`.production/backups/backup-20261029T060845845304Z.db` (UTC filename).
