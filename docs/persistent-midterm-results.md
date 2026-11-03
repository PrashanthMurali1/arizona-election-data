# Persistent midterm results

## Findings and provider use

Previously, a cold API process loaded one aggregate file or discarded it after three hours and
performed a civicAPI search followed by three sequential county-detail requests. The 20-second
single-flight memory cache deduplicated concurrent requests, but the first visitor still waited
for the complete upstream chain. County failures could join old county counts to new statewide
totals. The frontend fetched all six offices together and discarded hook state on tab unmount.

The old code's only rationale against SQLite was “unofficial, changing figures, not a retained
import”; no documented provider prohibition was found. Reviewed 2026-11-04:

- [Official API documentation](https://civicapi.org/api-documentation) permits personal,
  noncommercial and commercial purposes, and requires attribution for non-personal projects.
- [Official home page](https://civicapi.org/) describes open raw API use for developers and
  journalists. Neither reviewed page publishes a retention duration or a separate redistribution
  restriction. Persistence for this attributed results display is an interpretation of that broad
  permission, not an explicit standalone data-storage license. Review again if provider terms change.

The existing visible civicAPI attribution/source links remain. No provider account or key is needed.

## Storage and publication

Alembic `0003` adds only `live_race_snapshots`. It never resets, removes, imports into, or updates
the historical tables. Each election-date/race-id key has one complete JSON race, including
candidate vote/null values, percentages, county arrays and reporting values. Scalar columns retain
office, source URL, raw hash, content revision, successful retrieval time, attempt time, last detail
error, completion and certification guards. Election date and office indexes support filtered reads;
the unique election/race constraint makes repeated ingestion idempotent.

One transaction publishes the valid batch. A county detail error retains the **whole prior race**,
its successful timestamp and a separate error/attempt timestamp. Empty candidate lists, missing
prior candidates or newly missing vote values cannot erase a known-valid race. Protection is per
candidate: only a previously known vote count turning missing (or no known candidate remaining)
retains the prior race with "Incomplete candidate snapshot retained"; a candidate that stays null,
is withdrawn or is renamed does not freeze it. Operators seeing that message should check civicAPI
for a candidate whose votes disappeared. A county failure on a race with no stored prior publishes
its statewide totals with empty counties and a `refresh_error`, so other races are never blocked.
Per-run metadata (`retrieved_at`, `status`, `attempted_at`, `refresh_error`) lives only in columns,
so the revision, SSE notification and ETags change only when votes or the error state change.
Absent races are retained. Malformed/truncated/empty aggregate responses abort before publication. Explicit zero
remains zero, missing votes remain null, and `results_state` distinguishes unreported/partial/reported
without changing existing totals calculations. civicAPI's reviewed response does not supply a
reliable source-update timestamp: `source_updated_at` stays null rather than inventing one.

Certified live rows are frozen by the ingestion guard. This is not automatic certification; all
civicAPI ingestions remain unofficial and cannot overwrite historical certified publications.

Only `production/midterm_refresh_job.py` calls upstream. A process-safe advisory lock prevents
overlap; Relay's existing `election-production` resource also excludes deployments. Search is one
bounded request (limit 500; truncation rejected). Up to three county detail requests run concurrently,
with `(5,25)` second connect/read timeouts, two attempts, one-second backoff and a capped 30-second
Retry-After for 429/5xx/network failures. Retries are bounded and do not retry ordinary 4xx errors.

The existing Relay interval is now **five minutes** for active election coverage, with a fail-closed
read-only readiness guard pending deployment of this release and schema. Complete
(100%-reporting) races keep their existing snapshot for two hours between detail checks; a winner
call alone does not imply completion. Certified rows are skipped. The single search response still
includes all offices on each active scheduler run because civicAPI provides one race catalog/search.
There is no visitor-triggered upstream request, including for static district boundaries.

## API and caches

- SQLite is the durable source of truth; restart/offline upstream does not erase results.
- `GET /api/midterm-2026?office=governor` reads only that office's JSON and returns independently.
  Other offices prefetch after Governor paints, and selection can prioritize a queued request.
  The aggregate URL remains compatible for existing consumers.
- `/api/midterm-2026/catalog` returns office/race IDs independently, without candidate/county blobs.
  The existing static frontend office names avoid making catalog availability block Governor.
- API memory cache is a 20-second serialization/read optimization for the legacy aggregate only.
  Its metadata-only revision check invalidates immediately on a new database publication.
- SSE uses the existing Relay job status marker and database revision; office and aggregate responses
  share the revision. ETags hash the exact representation. Fresh browser HTTP responses expire after
  60 seconds; overdue/error responses require revalidation. All are `private`, so Cloudflare must
  honor origin headers and bypass these API/SSE routes rather than install an edge cache rule.
- Browser HTTP cache and ETags own persistent response storage. A `default` Governor lookup can
  display its cached response immediately, followed by a `no-cache` conditional validation. After
  Governor paints, the other five offices prefetch through a shared queue capped at two concurrent
  requests (Governor validation counts toward the cap). A slow validation does not block warming
  the remaining offices. Governor and selected-office work take priority over queued background work.
  There is no localStorage/sessionStorage results layer or separate client freshness TTL.
- Memory retains render snapshots and selection for tab revisits. Requests deduplicate by office;
  responses cannot land under another office heading. A single SSE connection stays open across
  office switches. Valid office-targeted notifications revalidate only those offices; notifications
  without valid targets revalidate all loaded/queued offices, including prefetched ones. The latest
  announced revision is also applied to offices whose cache lookup finishes later. The five-minute
  missed-notification backstop revalidates all retained offices. Updates preserve visible results,
  sorting, selection, county details and scroll, including on failure. Full reload returns to Governor
  and restores result bodies through the HTTP cache.

Overdue active data is marked stale after 15 minutes; complete data after six hours. Last valid
results remain available indefinitely. Cold empty SQLite returns a quick 503; visitors cannot repair
it by fetching upstream. Operators must seed it with the scheduled job after migration.

## Rollout

The Relay manifest was updated on 2026-11-04 IST to five minutes and the SQLite readiness guard;
all other automation definitions, enabled states and schedules were verified unchanged. The old
deployed image lacks the new guard and schema, so ingestion safely skips until deployment. The
prior manifest was retained under Relay's `.local/manifest-backups`. No application deployment,
production database migration or ingestion was performed during this automation update. Use the existing
reviewed deployment process: backup, apply candidate-image Alembic migrations (`alembic -c
backend/alembic.ini upgrade head`), run the existing Relay refresh once, verify Governor/catalog/SSE,
and verify the already-configured five-minute schedule passes preflight. Keep the existing coalescing/resource/recovery settings and
single scheduler; do not add cron, another service, or another database. Existing file snapshots are
operator compatibility artifacts, not an API fallback. Boundaries are populated by that job and
served from the existing raw volume. A missing boundary returns 503 without blocking vote results.

## Validation and measurements

Focused tests cover disposable SQLite idempotence/restart, office projection/no HTTP upstream,
transaction rollback, malformed/empty/partial protection, certified guards, retained stale data,
conditional requests and migration preservation of an existing historical row. Frontend tests cover
dedupe/cache corruption, demand loading, office/tab/reload reuse and SSE refresh preserving county
details DOM and scroll. The full backend suite has two pre-existing Linux-only `fcntl` collection
dependencies on Windows; report them separately from portable checks.

Reproduce the offline loader measurement with `.venv/Scripts/python.exe
scripts/benchmark_midterm_persistence.py --baseline 537313a`. It uses a temporary database, fixture
races, synthetic counties and a 200ms fake upstream per request. Initial measured cold load:
previous missing-file fallback 803.4ms / four upstream calls; previous retained file 7.5ms;
SQLite Governor 1.0ms / zero upstream calls (aggregate 4.4ms). Warm medians: previous file 0.16ms,
Governor 0.51ms. The legacy tiny memory-cache hit is faster than a database read; persistent reads
target cold reliability and smaller office payloads. Aggregate 41,964 bytes vs Governor 9,381 bytes
(77.6% reduction). These are uncompressed serialized loader payloads, not production latency claims.

The initial architecture measurements below predate the HTTP-cache/prefetch revision and should
not be used as final frontend performance claims. `node scripts/benchmark_midterm_browser.mjs` builds baseline and current production bundles into
temporary directories and records real Chromium navigation-to-results timing with injected API
delays. Its controlled network setup disables browser HTTP caching, so warm baseline requests are
not a model of a previously cached production HTTP response. See the script output for separate
equal-latency and slow-upstream scenarios, body-byte counts and refresh stability. Production
Cloudflare/network latency and provider availability have not been measured or changed.

Equal 5ms API-delay Chromium runs (one run per viewport; milliseconds, previous → current):

| Navigation to Governor visible | Desktop 1440×1000 | Mobile 393×844 |
| --- | ---: | ---: |
| Cold page | 155.1 → 174.5 | 168.8 → 155.6 |
| Warm full reload | 110.1 → 109.1 | 100.9 → 83.1 |
| Tab revisit | 132.5 → 112.8 | 133.3 → 100.9 |

Cold results body was 38,221 → 9,058 bytes; current warm/revisit results requests were zero.
Both versions retained county DOM/selection/scroll through SSE updates. Small single-run timing
differences are noise; the repeatable gains are office payload size and avoiding repeat fetches.
In a separate simulated missing-snapshot upstream scenario (800ms old API delay, 5ms current),
cold visibility was 1413.1 → 156.4ms. This is not normal retained-file production latency.

Final focused validation: 33 backend tests, 33 frontend unit tests, 17 midterm browser tests,
TypeScript and production build passed. Broader Windows validation was not green: two modules
require Linux `fcntl`; excluding them produced 91 passes, one failure and 53 setup errors. The
importer reports a retained House-source checksum mismatch for
`data/raw/us-house/calendar/vacancies-114.html`; that broader input problem was not repaired by
this feature, and was not independently checked on the baseline. Generated historical artifacts
from those checks were restored; historical data files have no feature diff.

The subsequent HTTP-cache/prefetch revision passes 36 frontend unit tests, 18 midterm behavior
tests and two real-HTTP browser tests, plus TypeScript and a production build. The real-HTTP spec
uses a loopback origin and production bundle without route interception: it observes an origin
304 with `If-None-Match`, a cached Governor response visible while validation is held, max-two
prefetch concurrency, all-office SSE refresh, and no persistent JavaScript result copies.
