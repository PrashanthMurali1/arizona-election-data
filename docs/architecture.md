# Architecture

## Local application

React/TypeScript → Vite `/api` proxy → FastAPI → SQLAlchemy → SQLite.

React Router provides `/`, `/elections/:contestId` and `/methodology`. The homepage is an API-driven catalog grouped by office. An election page gets its metadata, statewide results, county list and associated geographic vintage from REST endpoints. Switching years filters the catalog to the current office and navigates to a different contest ID.

The Python importer is an explicit offline job, not a web request or startup side effect. It reads source-derived data, validates and reconciles it, and replaces a contest's votes in a single transaction. Geometry and result provenance remain separate.

## Relational design

| Entity | Relationships and purpose |
| --- | --- |
| ElectionEvent | Election date, year and kind; shared by multiple contests and election-wide turnout records |
| Office | Office identity independent of year |
| Contest | Event + office + jurisdiction + boundary version + source + verification status |
| Candidate | Named person or preserved source category; participation is a separate record |
| Party | Source affiliation, including historical or no-affiliation codes |
| Participation | Candidate in a contest, that contest's party affiliation, write-in flag and category |
| GeographicUnit | Stable ID, name and kind; state and county implemented |
| BoundaryVersion | Vintage and geographic-source provenance |
| Geometry | Geographic unit + boundary version + GeoJSON feature |
| VoteResult | Participation + geographic unit + nullable integer votes + source + availability |
| Turnout | Event + geographic unit, nullable ballots/registration/percent, source definition and source ID |
| Source | Official URL, title, retained-snapshot checksum and provenance notes |
| ImportRun | Contest, UTC import timestamp, completeness status and JSON reconciliation report |
| ElectionPublication | Contest publication stage, numerical completeness, source verification and active result snapshot |
| PublicationSnapshot | Immutable event release, source, raw provenance, reporting precision, retrieval time and warnings |
| CurrentSnapshot | Current release and last successful retrieval for each event/source stream |
| MetricObservation | Event-snapshot geographic participation metric with nullable value and exact definition |
| RefreshAttempt | Successful and failed manual acquisitions/imports, retained for audit and stale-data display |

Unique constraints prevent duplicate candidate participation, geographic result cells, turnout records and geometry-version joins. Foreign keys are enabled explicitly for SQLite connections. Votes have a nonnegative constraint. Candidate-specific party columns do not appear in the database. Official statewide values are stored separately on unit `04`, never constructed by silently summing an incomplete county set.

The initial Alembic revision snapshots the schema rather than importing mutable application models. Bootstrap always migrates before importing; server startup does not create tables. Changing the schema requires another revision.

Revision `0002` adds the 2026 publication lifecycle. Participation metrics attach to the election event rather than candidate vote cells. The manual `scripts/refresh_2026.py` job archives official aggregates and advances one source stream transactionally, retaining older snapshots and failed attempts. The activity API supplies separate source dates and coverage. React reuses the existing map/table/detail layout with neutral pre-results colors; unofficial candidate releases use explicit reported-leader labels. See [2026 ingestion and verification](2026-import-report.md) for the reviewed input contract and remaining source limitations.

SQLite lives at an ignored local path, configurable through `DATABASE_URL`. SQLAlchemy's generic types, foreign keys, integer vote records and JSON columns can migrate to PostgreSQL. A PostgreSQL driver, data transfer and migration testing would still be required; PostgreSQL is not currently tested or provisioned.

## Reporting units and boundary vintages

Census GEOIDs identify the state (`04`) and counties (`04001`, etc.). The geographic conversion retains original official county polygons and stable IDs from the 2022 cartographic boundary ZIP. D3 Mercator fits all Arizona features into a fixed SVG viewBox, making the map responsive without zoom/pan controls. GeoJSON winding is normalized for D3's spherical conventions at render time.

A contest references a boundary version. Geometry identity is the pair of unit and version. Historical county results currently use the same documented 2022 visualization vintage. Future district contests must select the historically appropriate version and geographic units; they must not reuse the county boundary layer accidentally.

## API

FastAPI generates OpenAPI at `/openapi.json` and interactive docs at `/docs`.

| Endpoint | Response |
| --- | --- |
| `GET /api/health` | Database-readable health check |
| `GET /api/elections` | Catalog, office, year, coverage, status and boundary ID |
| `GET /api/elections/{id}` | Metadata, statewide candidate results, sources, latest reconciliation |
| `GET /api/elections/{id}/statewide` | Full statewide candidate results and turnout |
| `GET /api/elections/{id}/counties` | County results, initially ordered by contest votes descending |
| `GET /api/elections/{id}/counties/{geoid}` | Full candidate and turnout details for one county |
| `GET /api/elections/{id}/sources` | Election and geographic source references |
| `GET /api/geography/{boundary_id}` | Versioned GeoJSON feature collection |

Pydantic response models describe all election/result shapes. Unknown contests, counties and boundary versions return 404. Error details use FastAPI's standard JSON shape. Health checks deliberately require a migrated database. This local personal-project API has no authentication or rate-limit infrastructure.

The response service only computes totals and percentages when every participation has a verified, non-null result and the contest is reconciled. It returns no winner for incomplete data, empty contests, zero total votes or a tie. Partial candidate values remain nullable/explicitly unavailable. Turnout always retains the official reported denominator and definition.

The current geography-specific endpoints expose counties; adding districts should introduce generic reporting-unit endpoints while preserving these convenient county routes. This requires a small API/service extension, not a schema redesign.

## Frontend implementation

Route components are in `frontend/src/pages`. `CandidateSummary`, `CandidateRow`, `Availability`, `TurnoutMetrics`, `CountyMap` and `CountyTable` render generic API records. TypeScript types mirror API shapes. The API hook and election loader handle loading, empty, error and aborted-request states. Request cancellation prevents old years overwriting a newly selected election.

County selection and sorting are local state. Selecting a county focuses the dedicated detail region and preserves statewide results and the complete table. The table sorts numeric/null values correctly, with nulls last in both directions. Major-party table shares sum **all candidates of that party**, including party-affiliated write-ins; full candidate shares appear in the detail panel.

The design uses restrained mint accents on charcoal, with red/blue reserved for political meaning. Semantic headings, skip navigation, visible keyboard focus, accessible map buttons, `aria-sort`, table captions and a keyboard-accessible county table provide alternatives to map-only use. On small screens the map/table stack; only the table can scroll horizontally. Candidate rows and details adapt to a single column.

The frontend production output is built with `npm run build --prefix frontend`. Local usage serves it through Vite. Future production hosting needs SPA fallback routing and an `/api` reverse proxy; no hosting configuration has been provisioned.

## Scope and tradeoffs

A single local process/database is appropriate for a personal archive. There is no account system, background queue, tile service or cloud dependency. Queries favor clear ORM code over cache infrastructure; the 15-county workload does not need pagination. Browser tests are a small workflow suite, not a general test platform. Election-source extraction is intentionally conservative: an unreadable source stays incomplete rather than being replaced by estimates.
