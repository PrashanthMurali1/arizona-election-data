# Historical Statewide Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans for native implementation.

**Goal:** Add ten historical statewide general-election contests.
**Architecture:** Official canvass tables become reviewed source CSVs, normalized JSON, and existing transactional database imports.
**Tech Stack:** Python, CSV/JSON, SQLAlchemy, pytest.
**Spec:** docs/superpowers/specs/2026-10-31-historical-statewide-design.md

## Global Constraints
Preserve existing contests. Include all reported candidates and write-ins. Never infer missing votes or turnout. Retain provenance and reconcile all fifteen counties against published totals.

## Execution record

Native execution authorized. Work performed in the existing checkout; no branch, commit, deployment or merge created.

Sources and transcriptions retained for all ten contests. Nine reconcile and are active; 1994 Governor remains pending due to Crawford's county sum 10 versus official total 11. Ruling: withhold this contest from active imports rather than alter a vote or break the standard rebuild; cost is incomplete 1994 Governor coverage until the original scan is available.

Focused validation: 11 tests pass, including isolated API/import repeatability and preserved 2014 responses. Full backend test collection is blocked by existing Windows fcntl imports; global normalization is blocked by an existing House snapshot checksum mismatch.

Independent review: historical_review found a Linux path separator bug in Attorney General references; corrected to as_posix(), regenerated, and covered by a portability assertion. No other important findings reported. Implementation remains partial because the pending source discrepancy is unresolved.

## Review Focus
Merged OCR digits; zero-vote write-ins; unknown party labels; repeated imports; unchanged existing records.

### Task 1: Acquire and review sources
- [ ] Obtain official canvass tables and retain provenance for all five years.
- [ ] Produce reviewed CSVs with complete rosters, county cells and independent totals.

### Task 2: Extend normalization
- [ ] Add historical coverage tests in backend/tests/test_historical_statewide.py; run them and observe missing coverage.
- [ ] Extend date/source metadata and Attorney General file discovery in scripts/normalize_transcription.py and scripts/normalize_attorney_general.py.
- [ ] Rebuild normalized data and require all new contests to reconcile.

### Task 3: Verify integration
- [ ] Test historical catalog/API coverage, repeated imports and prior-election preservation using an isolated test database.
- [ ] Run backend regression tests; document sources, any limitations, and verified coverage.

## User-directed correction

User requested displaying 1994 Governor using published statewide totals despite the county discrepancy. This supersedes the earlier withholding ruling. The active contest is labeled reported, retains Crawford statewide 11 versus county sum 10, and shows a reconciliation notice. Unexpected source discrepancies still fail. No overseas-vote explanation or civicAPI verification is asserted.

## Turnout and table corrections

User requires turnout for every added contest and county. Retained official page-one tables for all five years, created reproducible turnout transcription adapter, imported event-wide turnout for all ten contests, and removed technical acquisition commentary from displayed source descriptions. County table uses participating parties, including LBT/REP for 1994 AG. Regression tests and live browser checks cover all ten pages and 150 county turnout cells.
