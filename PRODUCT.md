# Arizona Election Explorer

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Prioritize election enthusiasts and informed members of the public who want to explore Arizona elections, understand geographic voting patterns, and follow early-voting participation without assembling separate government reports and spreadsheets.

## Product Purpose

Make publicly available Arizona election data easier to access, explore, and understand. Visitors should be able to examine historical results, compare counties and election years, and understand participation statistics with their sources and limitations visible.

This is an independent, unofficial personal hobby project, maintained in spare time. It is informational and educational, with no company or government agency behind it. Development interests are not release commitments.

## Positioning

Bring source-linked historical results, interactive Arizona geography, and early-voting participation into one explorable archive. The mechanism is geographic exploration backed by documented source acquisition, retained data snapshots, and reconciliation of historical results against published references.

## Operating Context

- Visitors browse the election catalog by Live, Federal, and State categories, select an office and year, and explore results through maps, tables, and geographic details.
- Early-voting participation is presented in the homepage's Live Elections tab. Historical election details and sources are accessible through election pages; methodology has a dedicated page.
- The existing application uses React, TypeScript, Vite, and React Router, with a FastAPI backend, SQLAlchemy, Alembic, and SQLite. The Vite development server proxies `/api` to the backend on port 8000.
- Run the frontend from `frontend/` with `npm run dev`; its default local address is `http://127.0.0.1:5173`. The backend and a migrated, populated database are needed for data exploration. Setup and production operations are documented in `README.md` and `docs/`.

## Capabilities and Constraints

- Historical coverage includes Governor, Attorney General, U.S. Senate, and U.S. House elections. Coverage and geographic boundaries vary by contest; do not imply universal coverage of every office or year.
- County views cover Arizona's 15 counties. Preserve contest-appropriate geographic units and boundary vintages, particularly for congressional districts.
- Keep early-voting participation separate from candidate results. Ballot requests, returns, and participation breakdowns do not reveal candidate support or how a ballot was voted.
- Preserve source provenance, verification status, reporting definitions, snapshot dates, and meaningful availability or stale-data notices.
- Missing values remain unavailable; genuine zero values remain zero. Do not silently estimate missing results or turn partial county data into an authoritative statewide total.
- The project does not administer elections, count ballots, or certify results. Official results and election procedures belong to the relevant government authorities.
- No additional product requirements were specified during initialization. Further audience expansion and feature priorities remain open decisions.

## Brand Commitments

Use the established name, Arizona Election Explorer, and preserve its independent, unofficial status. Explain election information clearly and factually; avoid language that implies government affiliation, official certification by this project, or partisan endorsement.

## Evidence on Hand

- `README.md`: product purpose, public project identity, scope, and disclaimer.
- `docs/data-methodology.md`: source acquisition, historical coverage, reconciliation, missing-data semantics, and geographic provenance.
- `docs/architecture.md`: application structure and data semantics; check implementation and newer operational documents before relying on deployment details.
- `docs/us-house-import-report.md`, `docs/us-senate-import-report.md`, and `docs/attorney-general-import-report.md`: contest-specific acquisition and validation records.
- `docs/2026-import-report.md` and `docs/early-voting-refresh.md`: early-voting ingestion and refresh behavior.
- `data/raw/` and `data/processed/`: retained source inputs and processed records. Consult provenance for each dataset rather than assuming every input is an original official document.
- `frontend/src/`: existing user interface, product copy, and interaction behavior.

## Product Principles

1. Make geographic and historical exploration understandable to an informed public audience.
2. Keep sources, definitions, completeness, and verification visible alongside the data they qualify.
3. Preserve the distinction between participation, candidate results, and official election authority.
4. Prefer explicit unavailability to unsupported estimates or invented claims.
5. Support maps with readable tables and clear geographic details.

## Accessibility & Inclusion

Preserve the existing keyboard navigation, visible focus, semantic headings, skip link, accessible table sorting, and table alternatives to maps. Keep data exploration usable on smaller screens. No additional accessibility needs or specific compliance standard were specified during initialization.
