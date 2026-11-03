# Historical canvass import: 1966–1994

The eight supplied canvasses are represented by **538 contests and 1,448 visible
candidate entries**. All readable requested contests have transcriptions. Two
legislative contests remain incomplete because the original scans destroy values
and, in one case, part of the candidate roster. Missing values are not estimated.

| Year | Contests | Visible candidate entries | Source limitation |
| --- | ---: | ---: | --- |
| 1966 | 60 | 158 | None identified |
| 1970 | 67 | 159 | House district 22: two unreadable totals |
| 1974 | 68 | 175 | House district 16: three unreadable totals and a clipped final candidate row |
| 1978 | 67 | 205 | Source party abbreviation `IW` retained with its uncertainty noted |
| 1982 | 69 | 202 | None identified |
| 1986 | 69 | 160 | Existing David Zilly party label corrected to SWP |
| 1990 | 68 | 199 | General election only; subsequent governor runoff is a separate event |
| 1994 | 70 | 190 | None identified |

## Coverage and source handling

The archive contains 35 congressional district contests, five U.S. Senate
contests, 24 Governor/Attorney General/Secretary of State contests, and 474 state
legislative contests. No presidential contests appear in these midterm canvasses.
U.S. Senate races are absent in 1966, 1978 and 1990. No placeholder election was
invented for an absent office.

Each supplied PDF is byte-identical to an existing retained repository PDF.
Transcriptions under `data/raw/historical-canvasses/{year}.json` identify the PDF,
its SHA-256, the election date, source page, original party labels, candidate
rosters and printed totals. Every relevant federal, executive and legislative
page was visually inspected. Text extraction was used only as an aid. Original
embedded scan images were also inspected for the damaged 1970/1974 entries;
there is no hidden readable content outside the PDF crop that restores them.

Statewide county cells were transcribed for new Senate, Attorney General and
Secretary of State coverage. Reviewed existing statewide datasets are preserved
and audited by candidate identity, party, write-in flag and total. Explicit
name/party aliases handle printed abbreviations without changing source evidence.
Legislative county cells and most historical congressional county cells are not
yet transcribed; these pages show printed contest totals and do not claim county
verification or historical district maps.

The 1966 legislature has 27 distinct district labels in each chamber, including
subdivisions such as `7-A` and `8-O`. Later canvasses have districts 1–30.
Multiple-member contests occur historically in both chambers. Candidate votes
are never pooled across districts, and legislative winners are not inferred from
first place. Shares represent candidate votes, not voters. Pre-1983 statewide
views use the existing 14-county reconstruction; later views use 15 counties.

## Source discrepancies and corrections

- **1970 House district 22:** James H. (Jim) McCutchan and Howard Adams have
  partially erased final total digits. Their totals remain null.
- **1974 House district 16:** S. J. Carlisle, Jack DeVault and Diane E. McCarthy
  have damaged totals. The bottom of the scan cuts off the final candidate row;
  no identity or total was invented. This contest remains incomplete.
- **1974 Attorney General:** Bruce Babbitt's printed county cells sum to
  **301,730**, while the printed statewide total is **302,230**. Both are retained
  and the contest is reported with a reconciliation note, rather than verified.
- **1986 U.S. Senate:** the supplied canvass explicitly prints David Zilly as
  **SWP**, while the prior transcription used NONE. The reviewed CSV, generator,
  provenance checksum, normalized record and reconciliation are corrected. His
  write-in flag and all **18 votes** remain unchanged.
- **1978 Senate district 11:** Emil S. Sasiadek is printed with `IW`, which is
  not expanded by the scan. The raw label and explanatory note are preserved;
  the importer does not silently recast it as a known party.

## Application and import changes

Secretary of State, State House and State Senate now have sections in the State
Elections catalog. Historical U.S. House years appear under Federal Elections.
District pages offer year and district selection, complete visible candidate
rosters and direct source-page links without requiring district polygons. Existing
modern House routes, special elections and statewide URLs remain available.

`scripts/historical_canvasses.py` validates source integrity and transactionally
imports the archive. It is integrated into `scripts/import_data.py`. Scoped
imports work for historical House and the new state offices without requiring
modern House source snapshots. Fresh statewide imports also initialize the retained
county geometry. Existing event-wide turnout and county vote evidence are preserved.

Examples (after database migration, with the intended local `DATABASE_URL`):

```powershell
.venv/Scripts/python.exe scripts/historical_canvasses.py
.venv/Scripts/python.exe scripts/import_data.py --year 1982 --office us-house
.venv/Scripts/python.exe scripts/import_data.py --office secretary-of-state
```

Normalized rebuild records and the detailed audit are retained under
`data/processed/historical-canvasses/`. Eleven pre-existing statewide contests
were audited and preserved during the integration check; 527 other contests were
inserted into a disposable database. Production and the user's default database
were not modified.

## Verification

- **11 backend tests passed** in `backend/tests/test_historical_canvasses.py`,
  including checks for altered source hashes, duplicate districts, missing votes,
  candidate-specific audit discrepancies, actual county/turnout preservation,
  modern and historical scoped CLI imports, and fresh 14/15-county geometry.
- **20 frontend tests passed**, and the production TypeScript/Vite build passed.
- **Browser test passed at 390px and 1440px:** new office sections, district
  selection, source-page links, no geography requests and no horizontal overflow.
  The rendered screenshots were visually inspected.
- **Disposable database/API checks passed twice:** 24 district overviews, 24
  executive detail pages and their county routes. Repeated import produced
  identical district API responses. Existing statewide totals and normalized
  candidate metadata agreed with the supplied-canvass audit after correction.
- Two independent implementation reviews found scoped-import and audit issues;
  regressions were added and the findings fixed before delivery.

The pre-existing full-import baseline still rejects a modern House calendar
snapshot (`data/raw/us-house/calendar/vacancies-114.html`) for a checksum mismatch.
This is separate from the supplied historical canvasses. No integrity check was
disabled to bypass it, and a passing full bootstrap/full backend suite is not
claimed. Ordinary full bootstrap remains subject to that existing blocker;
the standalone historical importer and scoped historical imports pass.
