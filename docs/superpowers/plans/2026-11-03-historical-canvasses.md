# Historical canvasses implementation plan

> **For agentic workers:** Use superpowers:executing-plans for integration and
> superpowers:dispatching-parallel-agents for independent source transcription.

**Goal:** Populate the requested offices from all eight supplied canvasses.

**Architecture:** Retain page-referenced transcriptions and validate source hashes.
Import historical records transactionally into existing contest/result models;
serve historical district overviews through a map-optional archive route. Keep
existing reviewed statewide datasets and modern district routes intact.

**Tech Stack:** Python, FastAPI, SQLAlchemy, React, TypeScript, pytest, Vitest.

**Spec:** `docs/superpowers/specs/2026-11-03-historical-canvasses-design.md`

## Global constraints

- Import only offices actually in the supplied PDFs. Preserve all reported candidates.
- Preserve alphanumeric district labels and multiple seats. No invented winner.
- Maps are optional; never substitute current district boundaries.
- Null is not zero. Preserve source differences and source hashes.
- Work on the requested branch; no deployment or production database changes.

## Review focus

- Old district labels and multi-seat Senate races must survive unchanged.
- Incomplete county coverage must not become false zeroes or verified county maps.
- Existing contests must not duplicate or lose their prior county-level evidence.
- Historical House overviews must coexist with modern House routes.
- Repeated imports must preserve unrelated records and event-wide turnout.

## Task 1: Source transcriptions

**Files:** `data/raw/historical-canvasses/{year}.json`, source audit report.
**Produces:** Source metadata and contests with office_id, district, page,
candidate name, party, write_in, votes, and optional county_votes.

- [x] Independently transcribe 1966/1970, 1974/1978, 1982/1986 and 1990/1994.
- [x] Visually inspect every relevant page and record absent offices and uncertain cells.
- [x] Verify file hashes, visible rosters, district uniqueness and readable totals; damaged source cells remain explicit.

## Task 2: Normalization and database import

**Files:** `scripts/historical_canvasses.py`, `backend/tests/test_historical_canvasses.py`.
**Consumes:** Task 1 schema. **Produces:** Validated normalized records and repeatable import.

- [x] Write failing tests for hash rejection, district-label preservation, multi-seat
  safety and repeatable imports preserving existing county evidence.
- [x] Implement normalization and transactional import using existing models.
- [x] Write processed audit inputs and integrate into bootstrap/full import.
- [x] Run tests against disposable databases; PASS.

## Task 3: Historical district API and catalog sections

**Files:** historical archive API module, main API routing, frontend archive page,
catalog office configuration and integration tests.
**Consumes:** Imported contests. **Produces:** Year/office overviews with separate districts.

- [x] Write failing API tests for district isolation and missing-map behavior.
- [x] Implement dedicated historical archive response, preserving modern House routing.
- [x] Add Secretary of State, State House and State Senate sections.
- [x] Show candidate vote shares with multi-seat explanation and source page links.
- [x] Run API tests, frontend tests and production build; PASS except separately
  documented existing full-import source mismatch.

## Task 4: Reconciliation and final review

- [x] Audit every year/office/district against the source inventory and readable totals.
- [x] Obtain independent review, resolve significant findings, rerun affected checks.
- [x] Write import report with actual coverage, unresolved cells and verification commands.
- [x] Leave changes on the requested branch for review without deployment.

## Execution ledger

Ruling: user selected map-free district results; continue the explicitly requested
archive population with the existing stack and catalog design.

Ruling: physically erased scan data is unavailable, not zero; retain five null
totals and an incomplete roster notice in two legislative contests. Source-level
arithmetic discrepancies retain both printed representations.

Ruling: use explicit source-name/party aliases to compare prior reviewed records;
persist supplemental source audits while preserving county votes and turnout.
Correct the clearly printed 1986 David Zilly SWP party label through the existing
transcription/provenance pipeline.

Task 1: complete to source limits — 538 contests, 1,448 visible candidate entries.
Task 2: complete — source/import contract tests GREEN; repeated import checked.
Task 3: complete — 24 district overviews; new office sections; mobile/desktop check.
Task 4: complete — independent reviews addressed; 11 backend and 20 frontend tests,
browser test and production build passed. Known baseline House checksum blocker
is documented in `docs/historical-canvasses-import-report.md`.
