# Production dashboard and alerts

Created October 29, 2026 in account 8675480 for the existing production APM entity.

[Open the private Production Health dashboard](https://one.newrelic.com/redirect/entity/ODY3NTQ4MHxWSVp8REFTSEJPQVJEfGRhOjEzNDE0MDM5).

The **API Performance** page shows API throughput, error rate, p50/p95/p99 latency,
slow endpoints, database time, backend process memory, and telemetry continuity.
Health checks and the long-lived SSE update stream are excluded from ordinary API
performance charts. Their errors remain included in the overall web-error panel
and burst condition. The separate health-traffic panel makes their volume visible.

The **Errors and Refresh** page shows APM error classes, HTTP status codes,
forwarded failure diagnostics and job IDs, refresh outcomes/duration, and warnings.
Refresh panels retain their 24-/48-hour ranges independently of the dashboard's
current time picker, because jobs run every six hours.

Metric throughput/error panels use APM timeslice metrics. Percentile/endpoint and
HTTP-status panels use Transaction events, which can be sampled. Logs are also
rate-capped and deduplicated; they are diagnostic evidence, not complete counts.
Empty error tables are normal when there are no recorded errors. Backend memory
is the Python process's memory in MB; it is not Windows-host RAM or frontend
browser performance.

## Alert conditions

In New Relic, open **Alerts → Alert conditions (Policies)** and select
**Arizona Election Explorer - Production Health**, policy ID `8259249`.
All seven conditions are enabled. Notifications remain in New Relic only, as
requested: no email, SMS, Slack, or webhook workflow was created. The account had
no active external workflow during verification.

| Condition | Warning | Critical |
| --- | --- | --- |
| Web error burst | At least 1 error in a 5-minute bucket | At least 5 errors in a 5-minute bucket |
| Sustained API error rate | Above 2% for 5 minutes | Above 5% for 5 minutes |
| Sustained API p95 latency | Above 500 ms for 5 minutes | Above 1,000 ms for 5 minutes |
| APM reporting silent | — | No matching web metrics for 5 minutes |
| Refresh job failed | — | An observed forwarded refresh failure |
| Successful refresh missing | — | No successful completion for 7 hours |
| Critical service event | — | An observed forwarded CRITICAL event |

These are initial operational thresholds, not learned baselines or performance
guarantees. Adjust after several days of representative traffic. API percentage
and p95 conditions require sustained observations; low traffic makes percentages
volatile, while quiet windows are not fabricated as zero-latency success.

The main metric conditions use event-flow aggregation with a 120-second delay to
allow agent reporting to arrive. Consequently alert appearance is not immediate
at the end of the threshold period. Sparse log conditions use event timers.
The burst condition uses aligned 5-minute aggregation buckets, not a rolling
5-minute window. Issues are grouped per condition and auto-close after a maximum
24-hour violation lifetime if no normal recovery has closed them sooner.

Loss-of-signal checks arm only after the streaming alert engine observes a
matching signal. In particular, the missing-refresh condition must first see a
successful live completion after creation; a historical dashboard row does not
prove the condition is armed. No production refresh or failure was forced just
to test alerting. Log-based failures can be missed if export is capped or offline;
the missing-success condition supplies independent silence coverage once armed.

APM reporting silence can detect a stopped Docker engine or host from New Relic,
but it does not prove public Cloudflare/DNS/TLS availability. A separate external
HTTPS monitor is still needed for public availability. No synthetic monitor,
infrastructure/browser agent, new ingest stream or paid feature was enabled by
this dashboard task. Charts query the telemetry already being collected.

## Source, credentials and verification

- Reviewable dashboard and condition definitions: `production/newrelic-dashboard.json`.
- Creation/resume and verification: `scripts/setup_newrelic_dashboard.py`.
- Credential-safe NerdGraph client: `scripts/newrelic_admin.py`.
- Private resource IDs/state: `.production/newrelic-monitoring-state.json`.
- Query results: `.production/newrelic-query-validation.json`.
- Saved remote configuration read-back: `.production/newrelic-dashboard-verification.json`.

The User API key is read from `.production/secrets/newrelic-user-api-key` only for
local administration. It is never passed on the command line, baked into images,
mounted into production containers, printed, or written into dashboard JSON.
The runtime ingest key remains separate.

From the repository root in PowerShell:

```powershell
# Rebuild the local definition and validate all 30 queries without changes:
.\.venv\Scripts\python.exe scripts/setup_newrelic_dashboard.py --validate
# Read back the saved private dashboard and the seven enabled conditions:
.\.venv\Scripts\python.exe scripts/setup_newrelic_dashboard.py --verify
```

`--apply` creates missing resources or resumes an interrupted creation using the
saved state; it does not overwrite existing dashboard/condition edits. Retain that
state file to avoid duplicate creation. Change thresholds in New Relic when
tuning, then update the source definitions deliberately. A subsequent `--verify`
will flag divergence from the versioned source. No app/container restart is
needed for dashboard or alert changes.

All 30 NRQL queries were executed against real account telemetry before creation.
NerdGraph read-back verified both private pages, all 25 widget layouts/queries,
all seven enabled condition queries/thresholds, loss-of-signal settings, and the
absence of active external notification workflows. The browser could not be
controlled in this session, so visual layout was verified structurally through
the API rather than with a browser screenshot. Alerts were not deliberately
triggered by injecting failures or synthetic telemetry into production.

References: [APM metric definitions](https://docs.newrelic.com/docs/data-apis/understand-data/metric-data/query-apm-metric-timeslice-data-nrql/),
[NRQL alert configuration](https://docs.newrelic.com/docs/alerts/create-alert/create-alert-condition/create-nrql-alert-conditions/),
[NerdGraph dashboards](https://docs.newrelic.com/docs/apis/nerdgraph/examples/nerdgraph-dashboards/),
[NerdGraph alert conditions](https://docs.newrelic.com/docs/apis/nerdgraph/examples/nerdgraph-api-nrql-condition-alerts/).
