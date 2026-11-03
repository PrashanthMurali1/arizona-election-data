# Mason compilation corrections and coverage

Source: Bruce B. Mason, *Arizona General Election Results 1911-1960*, Bureau of Government Research, Arizona State University (1961), Research Study No. 3. Retained at `data/raw/early-canvasses/pdfs/1911-1960 compilation.pdf` (148 PDF pages; SHA-256 `cbbcafb08f34` prefix; the full digest is in each source declaration). PDF page references below are one-based; printed pages are seven lower.

The introduction (PDF pp3-4) describes a compilation principally from State Library/Archives and Secretary of State records. It acknowledges conflicting source figures. County tables group minor parties as Other and sometimes group multiple candidates of each major party. Individual candidate summaries precede those tables. Those distinctions are preserved.

## Changes

| Year | Results filled | County-table PDF pages |
| --- | --- | --- |
| 1911 | Three damaged Secretary of State Cochise entries and three statewide totals; Cameron Senate party identified as Republican | 74 (summary), 76 (counties); 17 (Senate party) |
| 1914 | U.S. Senate, U.S. House, Governor, Attorney General, Secretary of State | 19, 30, 46, 61, 76 |
| 1918 | Attorney General | 62 |
| 1942 | Two-seat at-large U.S. House, Governor, Attorney General, Secretary of State | 38, 53, 68, 83 |
| 1956 | President, U.S. Senate, both House districts, Governor, Attorney General, Secretary of State | 15, 26, 41, 57, 72, 87 |

Seventeen previously missing contests, 47 individual candidate totals, and 560 candidate or combined-group county cells were added. Existing 1956 legislative results remain present. No legislative tables occur in Mason, so it cannot fill legislative gaps. No Senate or presidential election is manufactured in a year without that office in the compilation. The 1914 source inventory is now a candidate election record with its original referendum excerpt retained alongside Mason.

Registration is filled for all 14 counties and the state for 1914, 1932, 1934, 1936, 1938, 1942 and 1956: 105 values. State totals reconcile to county sums: 69,927; 152,393; 147,474; 165,654; 179,840; 180,749; 367,661 respectively. Previously populated registration is preserved. Calculated Turnout uses contest votes divided by registration and remains explicitly distinct from ballots cast. Mason's per-office Total Vote and % Voting columns are not imported as election-wide ballots or published election-wide turnout. Its multi-seat House tables can exceed 100% because each voter could vote twice.

The 1932 Arizona Progressive Democratic presidential ballot line is now identified as Franklin D. Roosevelt from PDF p8, replacing the unidentified nominee. It retains its separate published nine-vote ballot line. The new 1956 presidential presentation uses actual presidential names directly from PDF p9, with county returns on p15.

## County aggregates and source discrepancies

Statewide results retain individual candidates. At county level, 1914 Senate and Governor Other totals remain combined; the 1942 House Democratic and Republican totals also remain combined. The API substitutes these explicit groups for their unallocated members only in county results. It never adds group totals to individual statewide votes, allocates combined votes to a candidate, or declares a combined group the winning candidate. Multi-seat House results have no single-winner or candidate-vote turnout inference.

Unresolved arithmetic in the source is retained and explained in the corresponding raw record:

- 1911 Cleveland: primary county cells plus the newly legible Cochise figure sum to 9,283; Mason statewide is 9,282.
- 1911 Morrison: original county sum 1,372 versus published 1,373 remains unchanged.
- 1914 Senate Other county cells sum to 13,482 versus individual statewide minor-party totals of 13,483.
- 1942 House Democratic county aggregates sum to 112,152; the two individual statewide totals sum to 112,182.
- 1956 Hayden: Mason county cells and county-table total are 170,780; candidate summary p18 prints 170,816. Both are retained with a reported status.

`data/processed/historical-canvasses/mason-summary-audit.json` compares 131 office-year summaries covering the six requested federal and executive offices through 1960. Of these, 117 match the retained statewide totals and 14 differ. Every differing original scan was visually rechecked. Legible primary figures were preserved, with both sets of numbers and source-page references recorded. For example, Mason's 1916 presidential summary misidentifies the Socialist nominee and combines Socialist and Prohibition votes; it does not supersede the clearer 1917 official report. This audit compares statewide totals; it is not a claim that every pre-existing county cell was re-transcribed.

1911 remains a documented turnout limitation: each relevant Mason county table explicitly prints Registration Not Available. Its zero percentages do not establish zero turnout, and contest totals cannot establish election-wide ballots cast. The UI carries that explanation. No registration is invented or borrowed from 1912.

## Import and verification

The importer now allows a retained supplementary source to replace rows owned by the same source document; independently reviewed datasets keep their existing evidence. County groups are validated against candidate indexes and cannot overlap or duplicate individual county cells. Corrections are imported into the existing preview database after a SQLite backup at `backend/local/before-mason-compilation.db`.

Historical JSON changes now invalidate the frontend's API cache version, including in the local preview. This prevents a data correction from continuing to display yesterday's cached response.

Verification: 43 focused backend tests, 22 frontend unit tests, two cache-version tests, the production frontend build, and three browser regression tests passed. Twelve additional live desktop/mobile checks verified 1911 Secretary of State, 1914 Governor, 1942 Attorney General, 1956 President and House, and 1932 Governor; no page errors or horizontal overflow occurred. County maps were present on all tested statewide pages. Live API checks confirmed 14 counties with winners for the 1914 and 1942 Governor elections.

Ten broader governor integration checks could not initialize because the existing full bootstrap rejects `data/raw/us-house/calendar/vacancies-114.html` with a House source checksum mismatch. An isolated full bootstrap reproduced this unrelated source-integrity failure. Scoped historical imports and the running preview were verified independently. No checksum gate was bypassed.

Preview: http://127.0.0.1:5173/ . Work remains on `feature/historical-canvasses-1966-1994`; no merge, push or public deployment.
