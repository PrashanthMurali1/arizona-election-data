# Early Arizona canvasses implementation plan

> Execute with superpowers:executing-plans. Use independent transcription agents
> for separate date ranges and an independent review before delivery.

**Goal:** Extend the approved archive workflow to the supplied 1906–1964 files,
preserving the existing 1966–1994 records and local preview.

**Architecture:** Retain the supplied PDFs, inventory actual election dates and
source coverage, and produce page-referenced JSON transcriptions under
`data/raw/early-canvasses/`. Extend the existing historical importer to consume
both collections and retain normalized rebuild records. Keep general and special
events distinct, accept county-based legislative labels, and preserve presidential
elector results as printed. Reuse the current catalog and map-optional archive UI.

**Spec:** The user requested the same office coverage and source handling as the
previous archive expansion; see the prior design at
`docs/superpowers/specs/2026-11-03-historical-canvasses-design.md`.

## Constraints and review focus

- Use the source heading/date, not the filename, to identify an event.
- Do not duplicate overlapping scans, primary results, referendum compilations,
  or administrative reports as general candidate elections.
- Territorial delegate results remain distinct from state-era assumptions.
- Preserve county-qualified district labels and multiple-member contests.
- Preserve individual elector tallies or printed slate totals without combining
  elector votes into an invented presidential ticket vote.
- Keep unknown data null and source omissions explicit; source absence does not
  mean that an election or office historically did not exist.
- General and special contests must not collide. Preserve prior IDs and results.
- Serve retained source PDFs through checked local links so page references work.
- Update the already authorized local preview after verification; no public deployment.

## Tasks

- [x] Inventory all 36 new supplied files, retain hashes, identify duplicates,
  noncandidate documents and source coverage.
- [x] Transcribe 1906–1926, 1928–1940, 1944–1958, and 1960–1964 independently;
  inspect every relevant page and preserve readable rosters/totals.
- [x] Write failing regressions for county labels, special events, supplemental
  sources, pre-1910 counties and presidential elector semantics.
- [x] Extend source validation, import identity, reconciliation, PDF delivery and
  archive responses; verify old archive tests remain green.
- [x] Add Presidential elections to the Federal catalog and adapt the archive UI
  for elector results and special-event labels. Verify browser and build behavior.
- [x] Audit every supplied file and imported event; independently review significant
  changes and fix findings with regressions.
- [x] Import into the local preview, verify the running site and commit the extension.

## Execution ledger

Ruling: continue on the existing feature branch and reuse the previously approved
source/transcription workflow; this is the requested expansion of the same work.

Ruling: primary-only and ballot-measure-only material is inventoried rather than
silently turned into requested candidate contests. Actual special candidate
elections remain in scope. Misnamed and duplicate files remain retained evidence.

Completed: 36 source files retained, 28 events / 608 contests / 1,345 candidate entries imported. See `docs/early-canvasses-import-report.md` for coverage, unresolved data and verification. Independent final review findings were fixed. Keep this feature branch for the requested local preview; no merge or public deployment. Full backend collection remains blocked by existing Windows-incompatible fcntl imports.
