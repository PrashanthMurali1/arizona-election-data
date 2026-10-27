# Arizona Attorney General elections

## Historical results

All three general elections use the Attorney General contest rows in the Arizona Secretary of State's official statewide canvass. The official canvass reports county columns and a separate TOTAL column. The reviewed transcriptions preserve all 15 county entries, explicit zero write-in votes, party labels and statewide totals. County sums were independently computed and reconciled to each canvass TOTAL. The PDFs were readable from the official indexed canvass sources but could not be acquired as local binaries during implementation; the retained files are checksummed CSV transcriptions, not copies of the original PDFs.

| Year | Candidate | Party/category | County sum | Official statewide | Reconciliation |
|---|---|---|---:|---:|---|
| 2014 | Mark Brnovich | Republican | 782,361 | 782,361 | Match |
| 2014 | Felecia Rotellini | Democratic | 696,054 | 696,054 | Match |
| 2014 | Anthony Camboni | No affiliation, write-in | 265 | 265 | Match |
| 2018 | Mark Brnovich | Republican | 1,201,398 | 1,201,398 | Match |
| 2018 | January Contreras | Democratic | 1,120,726 | 1,120,726 | Match |
| 2018 | Anthony Camboni | No affiliation, write-in | 346 | 346 | Match |
| 2022 | Abraham “Abe” Hamadeh | Republican | 1,254,102 | 1,254,102 | Match |
| 2022 | Kris Mayes | Democratic | 1,254,613 | 1,254,613 | Match |
| 2022 | Samantha Severson | Libertarian, write-in | 418 | 418 | Match |

Each year has **3 candidates, 15 counties, no missing candidate cells, no candidate-roster differences, and zero statewide discrepancies**. Totals across all reported candidates are 1,478,680 (2014), 2,322,470 (2018) and 2,509,133 (2022). Official canvasses list one write-in category each year: Camboni in 2014/2018, and named candidate Samantha Severson in 2022. The 2022 total reflects the official statewide canvass, including the Attorney General contest's statewide recount.

Official inputs:

- [2014 General Election Canvass](https://apps.azsos.gov/election/2014/general/Canvass2014GE.pdf), Attorney General table. Report date December 1, 2014.
- [2018 Official Statewide Canvass](https://apps.azsos.gov/election/2018/2018_1203_signed_official_statewide_canvass.pdf), Attorney General table (printed page 10). Reported November 30, 2018, 8:11:45 a.m. MST; certified December 3.
- [2022 General Election Canvass](https://apps.azsos.gov/election/2022/General/canvass/2022dec05_general_election_canvass_web.pdf), Attorney General table (printed page 10 / PDF page 9). Reported December 5, 2022, 10:00 a.m. MST.

Reviewed transcriptions and provenance/checksums are in data/raw/attorney-general/. Normalized files are in data/processed/attorney-general/; the ordinary reconciliation report includes each Attorney General contest. Official turnout is election-wide rather than office-specific, so the existing Governor import remains its sole event-level turnout record; Attorney General imports do not duplicate or replace turnout.

## 2026 activity

The 2026 Attorney General contest is present in the catalog and API. It uses the existing November 3 general-election participation snapshots attached to the shared election event, with the same metric definitions, source coverage, timestamps and warnings described in the [2026 Governor lifecycle report](2026-import-report.md). As of October 27, 2026, the official general-election candidate-results release time has not arrived. The page therefore shows neutral county coloring and general-election participation, with no Attorney General candidates, totals, shares, leaders or winners.

## Rebuild and import

From the repository root, run:

~~~sh
.venv/bin/python -m alembic -c backend/alembic.ini upgrade head
.venv/bin/python scripts/normalize_transcription.py
.venv/bin/python scripts/import_data.py
.venv/bin/python scripts/refresh_2026.py
~~~

normalize_transcription.py rebuilds the historical Governor and Attorney General normalized datasets. import_data.py --year 2018 scopes by year while preserving other contests. Re-imports replace that contest's result cells and reconciliation record; they do not duplicate candidate rows, turnout or event records.

For a reviewed future 2026 Attorney General candidate release, provide office_id: "attorney-general" and stream results-attorney-general in the strict snapshot manifest, with an official retained source, candidate/write-in roster, explicit vote scope, county cells and completeness declarations. Import with python scripts/refresh_2026.py --manifest path/to/reviewed-manifest.json. No automatic 2026 results feed is configured. Unofficial figures remain provisional. Certification requires the final canvass, a reviewed reference table and complete county/state reconciliation.

Historical Governor API fingerprints were checked after importing these contests and remain unchanged.
