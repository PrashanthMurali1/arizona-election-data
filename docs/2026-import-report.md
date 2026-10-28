# 2026 early-voting participation reports

Updated October 28, 2026. One **2026 Early Voting** catalog entry now presents shared civicAPI participation at `/elections/az-2026-early-voting`. The previous 2026 Governor and Attorney General page URLs redirect to it. No candidate-result, polling or forecast endpoints are queried by the current refresh. No deployment, visual redesign or schema migration was performed.

## Displayed participation

| Provider category | Statewide count | County coverage | Provider snapshot date |
| --- | ---: | ---: | --- |
| Requested | 3,289,914 | 15/15 | October 28, 2026 (date only) |
| Returned | 1,143,275 | 15/15 | October 28, 2026 (date only) |

| Provider party category | Requested | Returned |
| --- | ---: | ---: |
| Democratic | 1,053,507 | 430,622 |
| Other | 1,071,953 | 267,217 |
| Republican | 1,164,454 | 445,436 |

These party categories describe the provider's participation breakdowns. They are not votes or support for candidates. The API's field named `votes` holds ballot counts in these early-vote endpoints.

Statewide counts and party breakdowns appear on the shared page. The existing table currently shows **County, Requested and Returned**. Columns are hidden only when all counties lack their values; explicit zero keeps a column visible, and missing cells remain N/A in partially populated columns. The default sort is Returned descending, falling back to another visible metric or County when needed. County details retain the supplied party breakdowns and source definitions. Registration, mailed/issued, accepted and in-person figures remain unavailable.

The map uses only each county's Returned breakdown: a unique Democratic maximum is blue, a unique Republican maximum is red, and Other maxima, ties or missing breakdowns are gray. The current snapshot yields five blue and ten red counties. Requested and statewide party counts never determine county coloring. The existing colors, shapes and selection interactions are preserved. The map heading, legend and tooltips refer to registration, and the explanation states: **Colors show the largest party-registration group among returned early ballots in each county. They do not show which candidates voters selected or how they voted.**

## Source discovery and extraction

The public [Arizona early-vote tracker](https://civicapi.org/early-vote/az) uses these feeds:

- [Requested](https://civicapi.org/api/v2/early-vote/AZ/requested).
- [Returned](https://civicapi.org/api/v2/early-vote/AZ/returned).
- [Capabilities](https://civicapi.org/api/v2/early-vote/AZ/capabilities), which lists requested/returned party data for Arizona.
- [In-person](https://civicapi.org/api/v2/early-vote/AZ/inperson), which returned HTTP 404 with `early-vote data not found`.

Decision Labs' [public API documentation](https://www.decisionlabs.ai/docs/api) was inspected for participation endpoints; it does not list an early-voting feed. civicAPI supplies the usable data, so no Decision Labs values are combined with it.

Each `statewide_total` object contains provider party buckets. The adapter displays its supplied aggregate when one exists, otherwise sums the party-bucket counts in that same object, as the provider tracker does. Each county total similarly uses that county's own supplied buckets. Missing counts are never treated as zero when forming a total. Statewide figures are never inferred from county totals. Requested and Returned are separate stages and are never added together into turnout.

All source party labels and counts are preserved. A county or category with missing fields remains partial/unavailable without blocking other supplied records. There is no comparison between county and state sums, no corroboration against other providers or government sites, no write-in investigation and no independent election-data verification. Only response parsing, geographic assignment and storage/display integrity are checked.

## Retained snapshots and provenance

The acquisition index is `data/raw/2026/providers/early-vote-acquisition-20261028T065111735917Z.json`. It retains the exact tracker/documentation/capability/feed URLs, HTTP statuses, retrieval timestamps, raw file paths and SHA-256 values, including the unavailable in-person response.

The feeds publish `snapshot_date: 2026-10-27` without a clock time; that date precision is preserved. Retrieval timestamps are separate, shown in America/Phoenix by the application and recorded in UTC below. Each checksum identifies the exact retained response bytes, not a derived total or official canvass.

- **Requested**: retrieved `2026-10-28T06:51:10.914382+00:00`. Response `data/raw/2026/snapshots/f0aacef62e2bd85dfad449b2d87c48c9814bbabcb63387abb5797bcdd2296b24.json`. SHA-256 `f0aacef62e2bd85dfad449b2d87c48c9814bbabcb63387abb5797bcdd2296b24`.
- **Returned**: retrieved `2026-10-28T06:51:11.323836+00:00`. Response `data/raw/2026/snapshots/6b443a57cc7ae5e3856065e9320c4cbfb2386f74cb379e4ecf151291963c780f.json`. SHA-256 `6b443a57cc7ae5e3856065e9320c4cbfb2386f74cb379e4ecf151291963c780f`.

The automatic-refresh implementation exercised two live manual refreshes. The latest acquisition index is `data/raw/2026/providers/early-vote-acquisition-20261028T083439812841Z.json`. Both feeds now report `snapshot_date: 2026-10-28`, with unchanged participation counts; the repeated refresh reused snapshot/observation records (`created: false`) and advanced retrieval times. Requested was retrieved at `2026-10-28T08:34:38.495297+00:00`, retained as `data/raw/2026/snapshots/96128180593e87d694606477192980dfd3dd91edbd0d4a43eb825db3d9aaebf7.json`, SHA-256 `96128180593e87d694606477192980dfd3dd91edbd0d4a43eb825db3d9aaebf7`. Returned was retrieved at `2026-10-28T08:34:39.508833+00:00`, retained as `data/raw/2026/snapshots/d980bf7a56c668bfdbd583524cc66195c37dee0d7275c0624081c70d60238795.json`, SHA-256 `d980bf7a56c668bfdbd583524cc66195c37dee0d7275c0624081c70d60238795`. Each digest covers the exact named response file. Earlier releases above remain retained.

After the user granted macOS Documents access to Python, the persistent LaunchAgent successfully ran the same importer without a foreground terminal at `2026-10-28T08:37:21.976899+00:00`. The newer acquisition index `data/raw/2026/providers/early-vote-acquisition-20261028T083721879082Z.json` records the new retrieval timestamps and the same retained response files/checksums. Both imports returned `created: false, advanced: true`. The six-hour schedule is active; see [operations](early-voting-refresh.md) for its local-host limitations.

Each category is stored once on the November 3 general-election event. The shared catalog/API view is a read-only alias over the existing storage anchor; it creates no new office, contest, snapshot or observation records. Original office API URLs remain compatible, while their browser page URLs redirect to the shared page. The two retained releases contain 128 observations: 16 geographic units × 2 categories × (one total plus three party buckets). No candidate `Participation` or `VoteResult` records are created.

Stable snapshot identities prevent duplicates when data is unchanged. A new retrieval updates the check time. Older dated responses are archived without replacing newer category values. Archived official-source and earlier result-record snapshots are excluded from these current participation views; they are not re-fetched by this workflow.

## Exact import commands

From the repository root:

```sh
# Fetch only civicAPI Arizona early-voting participation feeds.
.venv/bin/python scripts/refresh_2026.py --early-voting

# Equivalent alias; also early-voting-only.
.venv/bin/python scripts/refresh_2026.py --providers

# Replay these exact retained responses offline.
.venv/bin/python scripts/refresh_2026.py --manifest data/raw/2026/manifests/early-vote-requested-b73d820adab8aee59251bed245089e719dbd6615ad109f585b48d967d0a7ffce.json
.venv/bin/python scripts/refresh_2026.py --manifest data/raw/2026/manifests/early-vote-returned-597dd81a7b1e8e6561d564081e4a12f44356056a30680aabb8c2c36663299f38.json
```

No-argument offline replay also includes the early-vote manifests; older result-record manifests cannot reactivate the earlier candidate-record source panels while event participation is active. Retrieval dates are not changed by offline replay. The live command now uses a cross-process lock and records job status. A persistent macOS LaunchAgent runs the same command every six hours. See [refresh operations](early-voting-refresh.md) for installation, status, logs and schedule changes. Current refreshes no longer request the tracker, capabilities or Decision Labs documentation used during initial discovery.

The shared page loads its existing API on entry, then uses SSE revision notifications after completed import commits. It does not poll every minute. Connection/reconnection announces the current revision, so missed updates are recovered without repeatedly fetching an unchanged revision. API requests read the database directly, so imports become visible without restarting the server. Background updates preserve county selection and table sorting; failed requests keep the last loaded data. The bottom Sources & coverage section distinguishes the source report date from the last successful retrieval and uses the existing notice style for failed refreshes or stale data. The removed Source snapshots section stays absent. See [refresh operations](early-voting-refresh.md) for the local audit-file notification mechanism and reconnect behavior.

Automatic-refresh technical checks cover feed scope/timeouts, successful and repeated imports, old-snapshot protection, failed/empty feed preservation, overlapping-job exclusion, logging/status and launchd configuration. Additional SSE checks cover canonical-only revisions, post-import finished markers, initial/reconnect catch-up, duplicate suppression and disconnect cleanup. Focused browser checks cover the canonical page, zero/missing behavior, no periodic data requests over six simulated hours, revision-driven updates, retained selection/sorting, reconnect recovery, failures and leaving/re-entering the page. These are application checks, without independent election-data verification.

The SSE change passed 14 focused backend tests, 7 frontend unit tests, 3 focused browser checks and the production TypeScript/Vite build. The real browser also confirmed the SSE endpoint returns streaming content with caching disabled. The six-hour LaunchAgent remains loaded with its prior successful exit status; its configuration and ingestion path were not changed by this display-refresh update.

## County records displayed

These values are extracted separately from each county's own Requested/Returned party buckets. The rows are not added together or reconciled against statewide values.

| County | Requested | Returned |
| --- | ---: | ---: |
| Apache | 29,358 | 6,646 |
| Cochise | 55,783 | 22,009 |
| Coconino | 64,602 | 27,000 |
| Gila | 25,122 | 12,541 |
| Graham | 12,716 | 4,400 |
| Greenlee | 2,843 | 956 |
| La Paz | 6,582 | 2,216 |
| Maricopa | 2,006,719 | 659,063 |
| Mohave | 96,648 | 37,683 |
| Navajo | 46,108 | 16,524 |
| Pima | 492,659 | 183,930 |
| Pinal | 205,200 | 77,962 |
| Santa Cruz | 21,789 | 2,679 |
| Yavapai | 140,951 | 71,652 |
| Yuma | 82,834 | 18,014 |

## Technical checks and remaining limits

Technical checks cover parsing and field mapping, shared event storage, explicit zero versus missing behavior, partial coverage, absence of candidate results, retained response binding, idempotent replay and older-snapshot protection. They do not corroborate or reconcile election figures.

Executed checks passed: 6 focused backend tests, 7 frontend unit tests, 10 browser checks, production TypeScript/Vite build, Alembic schema check and whitespace check. Coverage includes the single catalog entry, canonical API alias, both old-page redirects, all-empty columns, explicit zero/partial values, visible default sorting, Democratic/Republican maxima, Other/ties/missing cases, county selection, keyboard controls and mobile overflow. Both exact manifests were replayed without duplicating stored records. All 19 historical election-view API fingerprints match the pre-change baseline. Canonical and office snapshot APIs expose the same shared early-vote release IDs.

The full historical backend suite previously stopped during its unrelated House bootstrap at a checksum mismatch for `data/raw/us-house/calendar/vacancies-114.html`. That file is outside this update and is unchanged. Dedicated early-vote tests use an isolated migrated database without that historical bootstrap.

The usable feeds cover Requested and Returned statewide and all 15 counties. No in-person data is available from the inspected Arizona endpoint, and registration, mailed/issued and accepted values are not supplied. No missing category is zero-filled or substituted from another source.
