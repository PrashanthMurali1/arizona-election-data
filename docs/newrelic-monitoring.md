# New Relic production APM

The Python agent monitors the FastAPI backend inside Docker: request timing,
errors, database operations and outbound HTTP calls. It does not monitor Windows,
the scheduler or frontend page performance. An external uptime monitor is needed
to alert when Windows or Docker is down.

Save the New Relic **ingest license key**, not a user API key, as one line in
`.production/secrets/newrelic-license-key`. This directory is ignored by Git and
excluded from Docker builds. The key is mounted at runtime into the backend for
APM and into all four services for sanitized Logs API export.
Keep the existing private NTFS permissions; never paste the key into a command,
commit it or print resolved Compose configuration.

Set the following in the ignored `.env` (these two settings are not secrets):

```dotenv
NEW_RELIC_APP_NAME=Arizona Election Explorer (Production)
# US; use collector.eu.newrelic.com for an EU account.
NEW_RELIC_HOST=collector.newrelic.com
# Persist the override for normal Docker Compose operations on Windows.
COMPOSE_PATH_SEPARATOR=;
COMPOSE_FILE=compose.yaml;compose.newrelic.yaml
```

Build and activate from the repository root:

```powershell
docker compose -f compose.yaml -f compose.newrelic.yaml config --quiet
docker compose -f compose.yaml -f compose.newrelic.yaml build backend
docker compose -f compose.yaml -f compose.newrelic.yaml up -d --no-deps --wait backend
docker compose -f compose.yaml -f compose.newrelic.yaml logs --tail 60 backend
curl.exe --fail https://azelections.app/api/health
```

Activation briefly restarts the backend. The existing database, scheduler,
frontend and public tunnel remain in place. Use both Compose files for subsequent
updates, or retain the COMPOSE_FILE setting above so ordinary Compose commands
and the Windows operations helper also include monitoring. Docker restart
policies retain the monitored command across engine restarts. Explicitly using
only the base file to recreate the backend disables APM.

Open **APM & services → Arizona Election Explorer (Production)** in New Relic.
Visit a few public election pages. Allow up to five minutes for the first data.
Confirm transactions, response times and error rate appear. Agent logs should
confirm registration and reporting; a healthy app alone does not establish that
New Relic received data.

SQL is obfuscated, request parameter/header attributes are excluded, exception
messages are stripped, and automatic browser injection and APM log instrumentation/
forwarding are disabled. Sanitized selected logs use a separate bounded Logs API
exporter. See [production logging](production-logging.md) for diagnostics, limits
and privacy behavior. The license key is not baked
into an image or passed as a command-line argument.

For outage detection, configure a public New Relic synthetic monitor against
`https://azelections.app/api/health`, expecting HTTP 200 and `status: ok`, and
connect its failure alert to your desired notification destination. APM cannot
send telemetry when the host is asleep or Docker is stopped.

Disable APM while retaining the current logging code, without modifying data:

```powershell
docker compose -f compose.yaml build backend
docker compose -f compose.yaml up -d --no-deps --wait backend
```

This builds and starts `az-election-explorer-backend:local` without the agent
launcher. Build first: an older local image may lack the current startup script.
Also remove COMPOSE_FILE and COMPOSE_PATH_SEPARATOR from `.env` to keep APM and
Logs API export disabled in subsequent base-only operations.

References: [Python agent setup](https://github.com/newrelic/newrelic-python-agent),
[agent configuration](https://docs.newrelic.com/docs/apm/agents/python-agent/configuration/python-agent-configuration/),
[telemetry endpoints](https://docs.newrelic.com/docs/new-relic-solutions/get-started/networks/).
