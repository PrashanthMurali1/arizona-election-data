# Implementation report

Completed locally on October 27, 2026. **The 2022 MVP satisfies all 12 acceptance criteria under the documented reviewed-source workflow.** 2018 coverage has subsequently been completed and verified; see [the focused 2018 update report](2018-import-report.md). No deployment, paid service, user account or authentication infrastructure was introduced.

## Implemented features

- Dark responsive homepage, archive statistics and API-derived election cards grouped by office, with verified/incomplete badges and no preferential featured election.
- Separate reusable results pages with office-scoped year navigation; statewide totals and every reported candidate, including named write-ins.
- Official 15-county Census geometry, GEOID joins, solid party-winner colors, hover/focus, selection and an explicit neutral legend.
- Desktop map on the left/table on the right; stacked mobile layout with contained table scrolling.
- Sortable county table, initial descending contest-vote order, major-party shares, individual candidate winner, contest votes and official turnout.
- Dedicated county detail panel with all candidates and official ballots/registration/turnout. Selection preserves statewide results and the complete table.
- Source links, in-app reconciliation report and methodology, loading/error/empty/incomplete states, explicit N/A and safe suppression of conclusions from incomplete data.
- Semantic tables, accessible labels, keyboard county navigation, focus indicators, skip link and non-map exploration.

## Architecture

React 19 / TypeScript / Vite, React Router and D3 Geo communicate through a Vite REST proxy with FastAPI/Pydantic. SQLAlchemy manages a normalized SQLite schema migrated by Alembic. Generic offices, events, contests, participations, parties, results, turnout, sources and versioned geography support expansion beyond governor races. The initial source adapter is specific to governor/county tables; the extension guide identifies the changes needed for other source formats and reporting units.

Versioned raw reviewed CSVs and the official Census ZIP feed reproducible normalization/conversion scripts. The importer independently reads reference totals and candidate rosters, checks non-null county cells/affiliations against the source snapshot, reconciles every candidate, replaces results transactionally, records import runs and writes a machine-readable report.

## Data coverage

| Year | Result coverage | Reconciliation | Turnout |
| --- | --- | --- | --- |
| 2022 | All 15 counties, 9 candidates including 7 named write-ins | Every candidate exactly matches official statewide total; 2,559,485 contest votes | Official reported ballots, eligible registration and percentage for counties and state |
| 2018 | All 15 counties, 8 candidates including 5 named write-ins | Every candidate exactly matches official statewide total; 2,376,441 contest votes | Official reported ballots, eligible registration and percentage for counties and state |
| 2014 | All 15 counties, 10 candidates including 6 named write-ins | Every candidate exactly matches official statewide total; 1,506,416 contest votes | Official reported ballots, eligible registration and percentage for counties and state |

Numerical authority: Arizona Secretary of State certified statewide canvasses (governor page 2; turnout page 1), linked in `docs/data-methodology.md`. The official 2022 recount notice was checked; governor was not among the recounted contests. Geography: official Census 2022 county cartographic boundaries, 1:500,000, retained as ZIP plus derived Arizona-only GeoJSON. All 15 county GEOIDs match the result dataset.

Direct Arizona PDF downloads were blocked by Cloudflare HTTP 403. Reviewed transcriptions from readable official web-extracted PDF tables are retained for 2022 and 2014. Snapshot checksums identify the retained CSVs, not original PDF binaries. The 2018 update uses retained VEST/OpenElections inputs checked against official statewide totals and reviewed turnout references; no election-night values were substituted. See the source manifest and methodology for the precise provenance and verification scope.

## Executed tests and builds

| Check | Result and evidence |
| --- | --- |
| Frontend production build | PASS: TypeScript compilation and Vite bundle |
| Vitest utility checks | PASS: 3 tests for numerical/name sorting, preserved selection identifiers, input immutability and null/zero formatting |
| pytest database/pipeline/API checks | PASS: 8 tests on a fresh temporary SQLite database using actual Alembic migrations and actual imports |
| Alembic schema drift check | PASS: `No new upgrade operations detected.` |
| FastAPI startup | PASS: real Uvicorn server started and served API during Playwright checks |
| Playwright Chromium | PASS: 4 browser tests, no uncaught page errors in the primary flow |
| Desktop browser QA | PASS: catalog, statewide candidates, 15 bounded county paths, map selection/details, sorting in both directions, keyboard selection, year navigation, verified 2018 data and 404 state; map left/table right |
| Mobile browser QA | PASS: 390px viewport, no whole-page horizontal overflow, table county selection and responsive details |
| Source reconciliation | PASS for every 2022/2018/2014 candidate; exact differences zero, no missing candidate/county cells |
| Repeat import | PASS: no additional contest, participation, vote-result or turnout rows; audit runs append |
| Missing/inconsistent data | PASS: nulls withheld, genuine zeros retained; missing candidate, modified statewide total, equal/opposite county edits and invalid turnout are detected |
| Dependency audit | PASS: npm installation audit reported zero vulnerabilities after updating the test dependency |

Backend checks include all 15 individual county-detail responses, turnout separation, complete percentages, correct geographic joins, sources, unknown IDs and safe suppression of partial results. The clean-state pytest database is separate from the ordinary local database. Playwright starts/stops temporary local servers. Screenshots were captured and the desktop catalog/results screenshots were visually inspected.

The latest Python TestClient emits a non-failing upstream `httpx` deprecation warning. Windows has not been tested on hardware; portable setup commands and platform-aware browser-test Python executable selection are provided. No claim of testing all browser engines, all viewport sizes or production hosting is made.

## Local startup

From the repository root on macOS:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
npm ci --prefix frontend
python scripts/bootstrap.py
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

In a second terminal from the repository root:

```sh
npm run dev --prefix frontend -- --port 5173 --strictPort
```

Open http://127.0.0.1:5173; API docs are at http://127.0.0.1:8000/docs.

For separate initialization/import steps, run:

```sh
python -m alembic -c backend/alembic.ini upgrade head
python scripts/normalize_transcription.py
python scripts/geography.py
python scripts/import_data.py
```

The active SQLite database is ignored under `backend/local/`. A custom `DATABASE_URL` supports an absolute local path outside sync directories. See README for Windows commands, source downloads, browser installation and troubleshooting.

## Acceptance criteria

| # | Approved criterion | Status |
| --- | --- | --- |
| 1 | Starts locally on M1 with documented commands | PASS — native Apple Silicon Python/Node environment; real local servers/browser execution |
| 2 | Dark homepage with available election catalog | PASS — database-derived office catalog and status badges |
| 3 | All verified 2022 candidates and statewide shares | PASS — 9 candidates, 7 named write-ins; contest-vote denominator |
| 4 | All 15 counties on official boundary map | PASS — Census-derived geometry, GEOID coverage and browser path checks |
| 5 | County click opens verified results/turnout | PASS — browser map click, table alternative, full detail and turnout checks |
| 6 | County table sorts correctly by total votes | PASS — numerical unit checks and real browser ascending/descending interaction |
| 7 | County candidate totals reconcile with published statewide results | PASS — all nine 2022 candidates exactly match independently retained official reference totals |
| 8 | Unavailable data visibly identified, never silently zero | PASS — N/A, null/zero and partial-result tests; 2018 is now verified |
| 9 | Import scripts rebuild SQLite from documented sources | PASS — reviewed official intermediate CSVs and retained Census ZIP, clean-database execution |
| 10 | Frontend build and backend/database smoke checks succeed | PASS — build, API tests, real startup, migration and drift checks |
| 11 | Setup, architecture, methodology and extension documentation | PASS — README plus the required docs and source manifest |
| 12 | Final implementation report and outstanding limitations | PASS — this report and delivery response |

## Remaining limitations

1. VEST’s 2018 broader write-in aggregate (3,203) is not interchangeable with the five certified named candidates (275); it remains excluded and fully documented. The completed candidate dataset has no outstanding reconciliation discrepancies.
2. Original Arizona PDF binaries were not obtained locally. The reviewed raw CSVs are the reproducible numerical source snapshots; independent original-PDF auditing remains possible when source access permits.
3. Districts, precincts, other offices, historical boundary layers, multi-seat winner rules and other election systems require new source adapters/appropriate reporting-unit semantics. Generic schema support does not mean these datasets are already implemented.
4. Optional web fonts use Google Fonts with local system fallbacks. All election results and geometry are local.
5. Windows and other browser engines have documented or compatible paths but were not actually executed. Production hosting/process management is outside this local MVP.

No mandatory 2022 acceptance criterion remains blocked. Data completeness beyond 2022 is reported separately from MVP completion.
