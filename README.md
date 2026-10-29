# Arizona Election Explorer

The Docker Compose production build is now hosted on this **Windows computer** at **https://azelections.app**, with local viewing at **http://127.0.0.1:8080**. Frontend, backend, six-hour refresh scheduler and the existing Cloudflare Tunnel connector are healthy after the approved Mac-to-Windows cutover. See [Windows deployment and operations](docs/windows-deployment.md) for verification, backups and rollback. The [Mac hosting report](docs/production-hosting.md) records the previous deployment.

The production backend also supports [New Relic APM monitoring](docs/newrelic-monitoring.md), enabled through a Compose override and a private runtime license-key mount.
See [production logging](docs/production-logging.md) for structured events, rotation, incident diagnosis and the free-tier ingestion policy.

A local, dark-themed dashboard for exploring Arizona election results. Browse the election catalog, compare candidates, select a county or congressional district on the map or sortable table, and inspect results, turnout and source details.

**2026 Early Voting is available as one catalog entry.** The shared page at `/elections/az-2026-early-voting` displays civicAPI's October 28 participation data: **3,289,914 requested** and **1,143,275 returned** ballots, plus all 15 counties and party-registration breakdowns. The table hides wholly unavailable columns. Counties are blue/red for the uniquely largest Democratic/Republican registration group among returned ballots; Other/ties/missing remain gray. Colors do not indicate candidate choices. The old 2026 Governor/AG page URLs redirect here. Refresh with `.venv/bin/python scripts/refresh_2026.py --early-voting`; see [2026 sources and coverage](docs/2026-import-report.md).

**Attorney General results are also available for 2014, 2018 and 2022**, with all three candidate rosters reconciled to the official canvass across 15 counties. Current 2026 participation appears in the shared Early Voting entry. See the [Attorney General report](docs/attorney-general-import-report.md).

**2022 MVP implemented and verified.** 2022, 2018 and 2014 governor results reconcile for every reported candidate across all 15 counties. The 2018 import combines VEST ballot-candidate precinct sums, OpenElections named write-ins and official turnout, with documented source checks. The current Docker/Cloudflare hosting status is documented above.

**U.S. Senate results are available for 2016, 2018, 2020 (special), 2022 and 2024.** All 61 candidate records reconcile across 15 counties per election, including every officially canvassed named write-in. The 2020 special election uses the existing interface and labels. There is no 2014 or 2026 Arizona U.S. Senate entry. See the [Senate source and verification report](docs/us-senate-import-report.md).

**U.S. House results are available for all nine districts in 2014, 2016, 2018, 2020, 2022 and 2024.** All 54 regular contests and 160 candidate records reconcile, including the final 2014 CD2 recount. House views use the appropriate historical congressional district maps with the existing design. The April 24, 2018 CD8 and September 23, 2025 CD7 special views display civicAPI candidate reports, clearly labeled as civicAPI data rather than official canvass results. See the [House import and validation report](docs/us-house-import-report.md).

## Requirements and stack

Tested on an Apple Silicon Mac with **Python 3.13.7**, **Node 24.9.0**, and **npm 11.6.0**. Use Python 3.13 and Node 24 LTS for the documented setup. No Docker, accounts, API keys or paid services are required.

- React 19, TypeScript 5.9, Vite 7; React Router for office/contest routes.
- D3 Geo 3 renders official Census GeoJSON as responsive SVG; no map tiles or external map service.
- FastAPI, Pydantic, SQLAlchemy 2 and SQLite; Alembic migrations.
- PyShp converts Census shapefiles; Requests acquires sources; pypdf supports optional text extraction.
- pytest, Vitest and Playwright provide focused pipeline, API, utility and browser checks.
- CSS uses DM Sans and Manrope with system fallbacks. The optional Google Fonts stylesheet may require Internet access; all results and map geometry are served locally.

Optional Python formatting tools are declared in `backend/requirements-dev.txt`. Exact Python versions are pinned in `backend/requirements.txt`; npm versions are locked in `frontend/package-lock.json`.

## Install and initialize (macOS, from repository root)

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
npm ci --prefix frontend
python scripts/bootstrap.py
```

`bootstrap.py` applies Alembic migrations, normalizes the retained official source transcriptions, regenerates the 15-county GeoJSON from the retained Census archive, imports/reconciles historical data, and replays retained 2026 releases. It works offline after dependencies are installed. Repeating it replaces contest results transactionally and creates import audit records, without duplicating elections, votes or snapshots.

The active database defaults to **`backend/local/elections.db`**, which is ignored by Git. Keep the checkout outside Google Drive and other synchronization folders. To put the database elsewhere, set an absolute URL before **both initialization and backend startup**:

```sh
export DATABASE_URL="sqlite:////absolute/path/outside/cloud-sync/elections.db"
```

Create the parent directory first. `.env.example` is a reference; the app does **not** automatically load `.env` files. The default requires no configuration.

## Start locally

Terminal 1, from the repository root with the virtual environment active:

```sh
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

Terminal 2, from the repository root:

```sh
npm run dev --prefix frontend -- --port 5173 --strictPort
```

Open **http://127.0.0.1:5173**. FastAPI's OpenAPI UI is **http://127.0.0.1:8000/docs**. Vite proxies `/api` to FastAPI, so local browser requests share one origin. Keep both terminals running.

## Individual data and migration commands

With `.venv` active, from the root:

```sh
python -m alembic -c backend/alembic.ini upgrade head
python scripts/normalize_transcription.py
python scripts/geography.py
python scripts/import_data.py
python scripts/refresh_2026.py
```

The importer reads the normalized Governor and Attorney General records, independently checks each candidate's county cells and statewide total against the retained canvass transcription, and writes **`data/processed/reconciliation.json`**. An incomplete import with results exits nonzero. The 2018 Governor import retains and reports VEST’s noncomparable aggregate write-in field separately; it is not assigned to named candidates. Input type/relationship errors abort the transaction.

For a scoped 2018 rebuild/import, preserving other election years:

```sh
python scripts/normalize_2018.py
python scripts/import_data.py --year 2018
```

Its retained public inputs can be checked/reacquired with `python scripts/download_2018.py`; add `--try-official` to attempt the PDF again. Source checksums and the OpenElections revision are pinned. See [2018 validation](docs/2018-import-report.md) for the write-in discrepancy investigation and all candidate totals.

Optional source reacquisition:

```sh
python scripts/download_sources.py
python scripts/normalize.py
```

For the current 2026 refresh, run `.venv/bin/python scripts/refresh_2026.py --early-voting` (`--providers` is an alias). It fetches only civicAPI's Arizona participation feeds; it never queries candidate races, polling or forecasts. Requested and returned categories are stored once per event and shared by both offices. No state/county corroboration or canvass reconciliation is performed. Offline replay preserves original retrieval times. The [2026 report](docs/2026-import-report.md) documents snapshots and coverage. A macOS LaunchAgent supports persistent refreshes at 00:00, 06:00, 12:00 and 18:00 in the host timezone. The shared page loads current data on entry and uses server-sent revision notifications after completed imports; it does not poll the API every minute. See [refresh operations](docs/early-voting-refresh.md) for activation, status, logs and disabling the schedule.

The Secretary of State PDF URLs returned Cloudflare HTTP 403 during development. Downloads report failures; they never substitute election-night results. `normalize.py` is an optional PDF-layout adapter and writes normalized 2022 data only when all nine candidate rows parse; historical PDF extraction is review-only. The documented bootstrap uses reviewed CSV snapshots and does not require live PDF access. See [data methodology](docs/data-methodology.md).

To verify migrations on a fresh separate database without deleting the working database:

```sh
DATABASE_URL=sqlite:////tmp/az-explorer-check.db python scripts/bootstrap.py
```

Use a new filename for a genuinely clean check. The pytest suite creates its own temporary database automatically.

## Verification

```sh
python -m pytest backend/tests -q
npm run test --prefix frontend
npm run build --prefix frontend
```

Browser checks start and stop temporary backend/frontend servers automatically (ports 8000 and 5173). Initialize the normal local database first. To keep browser binaries inside the ignored project dependencies:

```sh
cd frontend
PLAYWRIGHT_BROWSERS_PATH=node_modules/.cache/ms-playwright npx playwright install chromium
PLAYWRIGHT_BROWSERS_PATH=node_modules/.cache/ms-playwright npx playwright test
```

Playwright checks county map clicks, full detail results, keyboard table selection, sorting, election-year navigation, 2018 results/source provenance, errors, desktop placement and mobile overflow. Screenshots are written to ignored `frontend/test-results/`.

Successful executed checks and the original 12-item acceptance matrix are recorded in [the implementation report](docs/implementation-report.md). The [2026 report](docs/2026-import-report.md) records additional lifecycle checks. Source/API/browser checks use retained real data; future-stage, correction and failure tests use explicitly synthetic releases in isolated temporary databases. Python's TestClient currently emits an upstream `httpx` deprecation warning; tests pass.

## Windows development

Use Python 3.13 and Node 24. In PowerShell, from the root:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
npm ci --prefix frontend
.\.venv\Scripts\python.exe scripts/bootstrap.py
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

In a second terminal run `npm.cmd run dev --prefix frontend -- --port 5173 --strictPort`. Activation is optional because the commands use the virtual environment executable directly. A custom database can use `$env:DATABASE_URL = "sqlite:///C:/local-data/elections.db"`; create its parent directory first. Native participation job locking and macOS LaunchAgent management use Unix APIs; use the Linux Docker scheduler for Windows production. Windows timezone data is installed automatically by the requirements file.

For browser tests use `$env:PLAYWRIGHT_BROWSERS_PATH = "node_modules/.cache/ms-playwright"` in `frontend`, run `npx.cmd playwright install chromium` and `npx.cmd playwright test`. The test-server config locates the Windows virtual environment executable automatically. For production use [the Windows Docker deployment guide](docs/windows-deployment.md), which keeps the existing cron worker and Cloudflare Tunnel architecture.

## Troubleshooting

- **Dashboard reports a loading error:** run bootstrap and start FastAPI; check `/api/health`. A blank database is not seeded automatically on server startup.
- **Port already in use:** stop your existing project server or change both the backend port and Vite's proxy. Playwright expects the documented ports.
- **`no such table`:** run `python -m alembic -c backend/alembic.ini upgrade head` against the same `DATABASE_URL` used by FastAPI.
- **`ModuleNotFoundError`:** run backend commands from the repository root using the project virtual environment.
- **Source HTTP 403:** use the retained CSVs and Census ZIP with bootstrap; original PDFs may need a normal browser download for further auditing.
- **Import exits nonzero:** inspect its output and reconciliation report; never adjust vote counts to make totals match. Resolve the source or mark data incomplete.
- **Fonts unavailable:** the interface falls back to local system fonts; results and geometry remain usable.
- **Browser executable missing:** install Chromium with the same `PLAYWRIGHT_BROWSERS_PATH` used for test execution.
- **Dependency installs cannot reach package registries:** Internet access is needed for initial pip/npm installation, but not for normal source-snapshot imports.

## Repository structure

```text
frontend/src/          Routes, reusable components, typed API client, styles
frontend/e2e/          Browser interaction checks
backend/app/          ORM, response models, result services, REST routes
backend/alembic/      Versioned schema migration
backend/tests/        Isolated database/pipeline/API checks
data/raw/             Reviewed official table transcriptions, source manifest, Census ZIP
data/processed/       Normalized JSON, 2018 source comparison, reconciliation report
data/geography/       Derived Census Arizona GeoJSON, vintage and provenance
scripts/              Download, normalization, conversion, import and bootstrap tools
docs/                 Architecture, methodology, extension guide, implementation report
```

See [architecture](docs/architecture.md), [data methodology](docs/data-methodology.md), and [adding elections](docs/extending-elections.md). The schema, office catalog, result records and React views support multiple candidates and offices. Only the initial source adapter is specific to governor county tables.
