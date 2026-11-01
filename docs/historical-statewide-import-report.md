# Historical Governor and Attorney General expansion

Added Governor 1994, 1998, 2002, 2006 and 2010; Attorney General 1994, 1998, 2002, 2006 and 2010. Each has every candidate reported in its canvass table, all fifteen county cells and separately reported statewide totals. All nine contests reconcile exactly.

**Update (official canvass checked):** the official 1994 canvass PDF was later supplied and retained; it showed the one-vote Crawford difference described below was an omitted cell (Yavapai, 1), now fixed, and 1994 Governor is `verified` with no differences. The text below is the original note.

1994 Governor is active with status `reported`. Per user direction, the published statewide total is authoritative for display: Charles M. "Chuck" Crawford has 11 statewide votes; the indexed county cells sum to 10. Both are retained without adjustment. All ten candidates and fifteen counties display, with statewide vote shares calculated from the published statewide candidate totals (1,129,607 votes). The reviewed one-vote difference is explicitly declared in normalized metadata and remains visible in reconciliation in the retained audit data. It is not marked fully reconciled. No cause, including overseas voting, is inferred. Other discrepancies or source mismatches still fail validation.

A civicAPI lookup was attempted on October 31, 2026; the attempted race-list route returned HTTP 404 (retained in `data/raw/historical-statewide/1994-civicapi-check.json`). This does not establish whether civicAPI holds the election, and no civicAPI verification is claimed. Display uses the published official statewide total as requested.

## Sources and acquisition

Official Arizona Secretary of State general-election canvasses:

- 1994: https://apps.azsos.gov/election/files/hist/canvass1994ge.pdf (printed page 2)
- 1998: https://apps.azsos.gov/election/1998/General/Canvass1998GE.pdf (Governor page 2; AG page 10)
- 2002: https://apps.azsos.gov/election/2002/General/Canvass2002GE.pdf (Governor page 2; AG page 10)
- 2006: https://apps.azsos.gov/election/2006/General/Canvass2006GE.pdf (Governor page 2; AG page 11)
- 2010: https://apps.azsos.gov/election/2010/General/Canvass2010GE.pdf (Governor page 3; AG page 11)

Direct binary downloads from both Secretary of State and State Library returned HTTP 403. Retained inputs are indexed official canvass excerpts and CSV transcriptions, not original PDFs or visually verified scans. Provenance records have null PDF checksums and checksummed retained excerpts/CSVs. Indexed extraction can contain errors that arithmetic reconciliation alone cannot detect.

1994 source party abbreviations D/R/L/I/N map to DEM/REP/LBT/IND/NONE. 1998 RPA is Reform Party. Source labels `Write-In` without affiliation map to NONE; no political affiliation is inferred. Known merged single-digit rows are explicitly enumerated in the transcription adapter. The 1994 official election-wide turnout table (canvass page 1) is retained separately and imported once through Governor for the shared election event: 1,153,724 ballots, 2,075,322 registrations, published statewide turnout 55.59%, and all fifteen county rows. Both Governor and Attorney General share these figures. Official turnout is also retained and imported for 1998, 2002, 2006 and 2010, with statewide and all fifteen county registration/ballot/percentage rows shared across both offices. Rebuild these CSVs with `python -X utf8 scripts/transcribe_historical_turnout.py`. Statewide published turnout percentages: 1994 55.59%; 1998 45.82%; 2002 56.33%; 2006 60.47%; 2010 55.65%.

## Rebuild and validation

`python -X utf8 scripts/transcribe_historical_statewide.py` rebuilds the reviewed CSVs and provenance. To rebuild only these normalized contests, call `scripts.normalize_transcription.normalize(year)` and `scripts.normalize_attorney_general.normalize(year)` for each new year. The ordinary normalizer also discovers all new inputs, but its unrelated House normalization currently fails a retained calendar snapshot checksum check in this Windows checkout.

`python -X utf8 scripts/import_data.py --office governor` and `--office attorney-general` import the active archive. The 1994 Governor file is included with its reported-results status and reconciliation note.

Focused tests: `python -X utf8 -m pytest backend/tests/test_historical_statewide.py -q --basetemp=.pytest_cache/historical-check`. Twelve tests pass, covering nine reconciled contests, the displayed 1994 discrepancy, rejection of unexpected discrepancies, isolated database migrations, county API totals, repeated imports and unchanged existing 2014 API responses.

Broader backend collection is blocked on Windows by existing `fcntl` imports in early-voting modules. Full bootstrap also encounters existing House calendar snapshot checksum mismatches. Neither check is reported as passing.

## User-facing corrections

County tables select the two leading participating parties rather than hardcoding Democratic and Republican columns. The 1994 AG table shows Lbt and Rep shares, including sorting. The prominent reconciliation notice and special reconciliation badge text were removed; the retained source/audit records remain unchanged. Local browser validation confirmed both party columns, statewide turnout, all fifteen county turnout values and absence of the notice.

Validation after the turnout expansion: 12 focused backend tests pass; 16 frontend tests pass; the frontend build passes. Live browser validation checked all ten local election pages, all 150 county turnout cells, nonempty statewide turnout, Libertarian column sorting, and concise source descriptions without acquisition diagnostics.
