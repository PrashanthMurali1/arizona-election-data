# Arizona U.S. House import report

Implementation review: October 28, 2026. **54 regular contests are verified; both special-election views display civicAPI reports.** All eight election views are available locally. No deployment occurred.

| Election | Contested districts | Entries | Named write-ins / unresolved aggregates | Verification |
| --- | ---: | ---: | --- | --- |
| November 4, 2014 | 9 | 29 | 7 named | Verified, final CD2 recount applied |
| November 8, 2016 | 9 | 26 | 8 named | Verified |
| November 6, 2018 | 9 | 24 | 5 named | Verified |
| November 3, 2020 | 9 | 29 | 11 named | Verified, regular House election |
| November 8, 2022 | 9 | 26 | 9 named | Verified |
| November 5, 2024 | 9 | 26 | 5 named | Verified |
| April 24, 2018 special, CD8 | 1 | 2 | CivicAPI candidate report | civicAPI report |
| September 23, 2025 special, CD7 | 1 | 4 | CivicAPI candidate report | civicAPI report |

The six regular elections contain 160 candidate records, including 45 named write-ins. The 2018 and 2025 special views expose the candidate records in their retained civicAPI responses. The special results are not described as official canvass results, and no write-in results or county allocations are included.

## Calendar and boundary review

The [official House Vacancies & Successors archive](https://history.house.gov/Institution/Vacancies-Successors/Vacancies-Successors/) was reviewed for Congresses 113–119 using its read-only Congress selection form (`POST htmlContentID`). The retained HTML and request parameters are in `data/raw/us-house/calendar/`. Only the Franks–Lesko and Raúl Grijalva–Adelita Grijalva successions identify Arizona special elections during the requested period. No additional completed Arizona House special election was found through October 28, 2026. Primaries and 2026 regular elections are excluded.

The map uses original Census polygons and multipart polygons at 1:500,000 cartographic scale. The retained ZIPs include their original projection files; generated geography identifies native NAD83 geographic longitude/latitude (EPSG:4269). District identities include the plan year, e.g. `az-cd-2012-01` and `az-cd-2022-01`.

| Elections | Plan | Census product | Boundary ID |
| --- | --- | --- | --- |
| 2014–2020 regular; 2018 special | First used in 2012 | [2014 / 114th Congress](https://www2.census.gov/geo/tiger/GENZ2014/shp/cb_2014_us_cd114_500k.zip) | `congressional-2012` |
| 2022, 2024 regular; 2025 special | First used in 2022 | [2022 / 118th Congress](https://www2.census.gov/geo/tiger/GENZ2022/shp/cb_2022_us_cd118_500k.zip) | `congressional-2022` |

The [IRC published plans](https://irc.az.gov/index.php/plans/irc-published-plans) identify congressional version 14.0 as adopted January 18, 2022 and reaffirmed January 21. The [Secretary of State redistricting page](https://azsos.gov/elections/about-elections/elections-procedures/pre-election-procedures/irc) identifies these maps for the 2022 election cycle. The reviewed official maps and election records did not identify an intervening congressional amendment requiring another plan for the requested elections. The 2014 recount changes votes, not geography. A Congress number denotes the term elected, not the election year.

## Sources and extraction

`data/raw/us-house/manifest.json` lists every election date, source URL, available report date, retrieval date and precision, retained snapshot path and SHA-256. Each displayed source note identifies the exact retained file its checksum covers. A hash of an indexed text extract or reviewed CSV is explicitly distinguished from an original PDF hash. Original Senate-task snapshots are reused without altering their data. Indexed extracts retain their official source attribution; they are not represented as downloaded PDF binaries.

- **2014:** reviewed official indexed county tables for all nine districts, plus the [final court-certified CD2 recount](https://apps.azsos.gov/election/2014/General/CourtOrderedRecountResults.pdf). Barber's Cochise/Pima counts become 14,677/94,870 (109,547); McSally's become 21,737/87,977 (109,714). The original canvass/Clerk totals were 109,543 and 109,704. Both original records and the court extract are retained. Other candidates remain unchanged.
- **2016:** original signed statewide PDF, pages 11–12, reused from the retained public-copy acquisition. The sparse transcription in `scripts/house_records.py` was visually checked against rendered pages. Two one-vote glyphs absent from its text layer are explicitly preserved: Jaime Vasquez/Pinal and Federico A. Sanchez/Santa Cruz. These were read from the page images, not calculated from residuals.
- **2018:** official indexed canvass tables, with districts 1–4 reused from the Senate snapshot and districts 5–9 retained separately.
- **2020:** original official results-detail XML ZIP. Each House contest's participating-jurisdiction list and actual candidate county records are parsed independently; the XML State record is checked against its district total. This is a regular House election even though the Senate contest on that event is special.
- **2022:** official indexed canvass tables, including Independent Clint William Smith and every named write-in.
- **2024:** official indexed tables, with an actual county-record correction for District 9. The indexed layout shifted La Paz/Maricopa/Mohave cells into neighboring columns. All fifteen county CSVs from OpenElections commit `bf14331521f62f74cb17848ab11ca3dfd27f4f82` are retained in `2024-openelections.zip`; member URLs and hashes appear in `2024-openelections-provenance.json`. Only candidate `votes` fields are summed, without adding voting-method subtotals. Gosar's actual county counts are La Paz 5,260, Maricopa 137,529, Mohave 82,372, Yuma 24,422; Quacy Smith's are 2,065, 97,093, 22,998, 10,484. Both total independently to the official district targets. The original indexed cells and correction reviews are retained. No county allocation was inferred from a district remainder.

For every regular contest, the independently downloaded [House Clerk election statistics](https://clerk.house.gov/Members/ViewElectionInformation) supply the complete candidate roster and district totals. The normalizer re-extracts county records from retained originals and rejects even offsetting county errors that leave a candidate total unchanged. The Clerk's two pre-recount 2014 CD2 totals are explicitly superseded by the court order; they are not silently adjusted.

## Special-election civicAPI reports

The special-election views display results from civicAPI race records and label them as civicAPI reports, not official canvass results. No separate canvass reconciliation is performed, and write-in results are out of scope. Each source card links to its race endpoint and identifies the exact retained response snapshot whose SHA-256 is recorded in `data/raw/us-house/manifest.json`.

| Election | Endpoint | Candidate | Party | civicAPI votes | civicAPI share | Provider last updated |
| --- | --- | --- | --- | ---: | ---: | --- |
| April 24, 2018, CD8 special | [Race 29426](https://civicapi.org/api/v2/race/29426) | Debbie Lesko | Republican | 96,012 | 52.37% | 2026-01-10 00:48:49 UTC |
| April 24, 2018, CD8 special | [Race 29426](https://civicapi.org/api/v2/race/29426) | Hiral Vyas Tipirneni | Democratic | 87,331 | 47.63% | 2026-01-10 00:48:49 UTC |
| September 23, 2025, CD7 special | [Race 6240](https://civicapi.org/api/v2/race/6240) | Adelita Grijalva | Democratic | 70,043 | 68.95% | 2026-01-14 03:20:12 UTC |
| September 23, 2025, CD7 special | [Race 6240](https://civicapi.org/api/v2/race/6240) | Daniel Butierez | Republican | 29,893 | 29.43% | 2026-01-14 03:20:12 UTC |
| September 23, 2025, CD7 special | [Race 6240](https://civicapi.org/api/v2/race/6240) | Eduardo Quintana | Green | 1,116 | 1.10% | 2026-01-14 03:20:12 UTC |
| September 23, 2025, CD7 special | [Race 6240](https://civicapi.org/api/v2/race/6240) | Richard Grayson | No Labels | 536 | 0.53% | 2026-01-14 03:20:12 UTC |

The two JSON responses are retained at `data/raw/us-house/civicapi/race-29426.json` and `data/raw/us-house/civicapi/race-6240.json`. Both were retrieved on 2026-10-28 (date precision); the manifest stores their endpoint URLs, retrieval date, provider update timestamp and the SHA-256 of each exact JSON response file. The companion reviewed input CSVs preserve those same reported candidate totals and leave county cells blank because the endpoint totals are district-level. Missing county values are not converted to zero. No special-election turnout values are imported.

The reproducible, idempotent import scoped to the two specials is:

```sh
.venv/bin/python scripts/import_house.py --specials-only
```

This command normalizes the retained snapshots and replaces the same special-election result records. It does not reimport other House elections, other offices or turnout. The ordinary district map, candidate summary, table, source panel and election selector are reused unchanged in design.

## Turnout and data behavior

The civicAPI special-election views do not include turnout or county allocations. No statewide or whole-county turnout is relabeled as district turnout.

For regular-election county data, CSV integers include explicit zero; an empty cell is unavailable; `NA` means the county does not participate geographically in that district. The two special-election candidates results are district totals only; no county result rows are created for them. Their map retains all nine historical polygons, with eight `not_contested` polygons and the contested district selectable.

## Reproduction and checks

The versioned snapshots support offline imports. From the repository root:

```sh
.venv/bin/python scripts/bootstrap.py
.venv/bin/python scripts/house_geography.py
.venv/bin/python scripts/normalize_house.py
.venv/bin/python scripts/import_data.py --office us-house
.venv/bin/python scripts/import_house.py --specials-only
.venv/bin/python -m pytest backend/tests -q
.venv/bin/python -m alembic -c backend/alembic.ini check
```

The scoped civicAPI command imports only the two House special events and leaves all other House elections and offices untouched. There is no schema change; the existing event, contest, unit and boundary models represent these records. Repeated imports replace the same result/participation keys.

From `frontend/`:

```sh
npm test
npm run build
npm run test:e2e
```

Validation performed: backend House/API tests, frontend unit tests, browser checks for both special result pages, production build, full offline bootstrap, Alembic schema check and repeat scoped import. Browser checks cover special-event date/district labeling, civicAPI attribution, district selection through map/table/keyboard, sorting and responsive overflow. The UI design and CSS are unchanged.

API payloads for all **13 existing Governor, Attorney General and Senate entries** match the pre-import baseline after the complete bootstrap. A pre-existing checkout issue was corrected with narrow `.gitattributes` CRLF rules for the already-hashed Senate and Attorney General CSVs, plus the new House CSVs. Restoring those exact bytes preserves prior source hashes and votes; checksums are not weakened or bypassed.

The calendar, map joins, regular candidate reconciliation, repeat imports and application checks pass. The two special-election views present the retained civicAPI records; their data are explicitly attributed to the provider and are not represented as official canvass results.

## Candidate-level reconciliation

The tables below compare each regular-election reporting-county sum with the independent official district reference. Special-election civicAPI reports are listed separately above; they are not part of these official-source reconciliation tables.

### 2014 General

| District | Candidate | Party | Write-in/category | County sum | Official district | Difference | Missing county GEOIDs |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Ann Kirkpatrick | DEM | Ballot | 97,391 | 97,391 | 0 | None |
| 1 | Andy Tobin | REP | Ballot | 87,723 | 87,723 | 0 | None |
| 2 | Ron Barber | DEM | Ballot | 109,547 | 109,547 | 0 | None |
| 2 | Sampson U. Ramirez | NONE | Named write-in | 56 | 56 | 0 | None |
| 2 | Sydney Dudikoff | REP | Named write-in | 48 | 48 | 0 | None |
| 2 | Martha McSally | REP | Ballot | 109,714 | 109,714 | 0 | None |
| 3 | Raul Grijalva | DEM | Ballot | 58,192 | 58,192 | 0 | None |
| 3 | F. Sanchez | IND | Named write-in | 43 | 43 | 0 | None |
| 3 | Gabby Saucedo Mercer | REP | Ballot | 46,185 | 46,185 | 0 | None |
| 3 | Lee Thompson | MRK | Named write-in | 8 | 8 | 0 | None |
| 4 | Mike Weisser | DEM | Ballot | 45,179 | 45,179 | 0 | None |
| 4 | Chris Rike | LBT | Ballot | 7,440 | 7,440 | 0 | None |
| 4 | Paul Gosar | REP | Ballot | 122,560 | 122,560 | 0 | None |
| 5 | James Woods | DEM | Ballot | 54,596 | 54,596 | 0 | None |
| 5 | Matt Salmon | REP | Ballot | 124,867 | 124,867 | 0 | None |
| 6 | W. John Williamson | DEM | Ballot | 70,198 | 70,198 | 0 | None |
| 6 | David Schweikert | REP | Ballot | 129,578 | 129,578 | 0 | None |
| 7 | Rebecca DeWitt | AEL | Ballot | 3,858 | 3,858 | 0 | None |
| 7 | Ruben Gallego | DEM | Ballot | 54,235 | 54,235 | 0 | None |
| 7 | Gustavo Ortega | DEM | Named write-in | 17 | 17 | 0 | None |
| 7 | Samuel Esquivel | IND | Named write-in | 4 | 4 | 0 | None |
| 7 | José Peñalosa | JOS | Ballot | 3,496 | 3,496 | 0 | None |
| 7 | Joe Cobb | LBT | Ballot | 10,715 | 10,715 | 0 | None |
| 7 | Gary Dunn | REP | Named write-in | 129 | 129 | 0 | None |
| 8 | Stephen Dolgos | AEL | Ballot | 41,066 | 41,066 | 0 | None |
| 8 | Trent Franks | REP | Ballot | 128,710 | 128,710 | 0 | None |
| 9 | Kyrsten Sinema | DEM | Ballot | 88,609 | 88,609 | 0 | None |
| 9 | Powell Gammill | LBT | Ballot | 5,612 | 5,612 | 0 | None |
| 9 | Wendy Rogers | REP | Ballot | 67,841 | 67,841 | 0 | None |

### 2016 General

| District | Candidate | Party | Write-in/category | County sum | Official district | Difference | Missing county GEOIDs |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Tom O'Halleran | DEM | Ballot | 142,219 | 142,219 | 0 | None |
| 1 | Ray Parrish | GRN | Ballot | 16,746 | 16,746 | 0 | None |
| 1 | Paul Babeu | REP | Ballot | 121,745 | 121,745 | 0 | None |
| 2 | Matt Heinz | DEM | Ballot | 135,873 | 135,873 | 0 | None |
| 2 | Martha McSally | REP | Ballot | 179,806 | 179,806 | 0 | None |
| 3 | Raul Grijalva | DEM | Ballot | 148,973 | 148,973 | 0 | None |
| 3 | Harvey Martin | DEM | Named write-in | 283 | 283 | 0 | None |
| 3 | Bill Abatecola | REP | Named write-in | 1,303 | 1,303 | 0 | None |
| 3 | Jaime Vasquez | REP | Named write-in | 332 | 332 | 0 | None |
| 3 | Federico A. Sanchez | IND | Named write-in | 144 | 144 | 0 | None |
| 4 | Mikel Weisser | DEM | Ballot | 81,296 | 81,296 | 0 | None |
| 4 | Paul Gosar | REP | Ballot | 203,487 | 203,487 | 0 | None |
| 5 | Talia Fuentes | DEM | Ballot | 114,940 | 114,940 | 0 | None |
| 5 | Andy Biggs | REP | Ballot | 205,184 | 205,184 | 0 | None |
| 6 | W. John Williamson | DEM | Ballot | 122,866 | 122,866 | 0 | None |
| 6 | David Schweikert | REP | Ballot | 201,578 | 201,578 | 0 | None |
| 7 | Ruben Gallego | DEM | Ballot | 119,465 | 119,465 | 0 | None |
| 7 | Neil B. Westbrooks | GRN | Named write-in | 60 | 60 | 0 | None |
| 7 | Eve Nunez | REP | Ballot | 39,286 | 39,286 | 0 | None |
| 8 | Mark Salazar | GRN | Ballot | 93,954 | 93,954 | 0 | None |
| 8 | Trent Franks | REP | Ballot | 204,942 | 204,942 | 0 | None |
| 8 | Hayden Keener III | REP | Named write-in | 75 | 75 | 0 | None |
| 9 | Kyrsten Sinema | DEM | Ballot | 169,055 | 169,055 | 0 | None |
| 9 | Cary Dolego | GRN | Named write-in | 56 | 56 | 0 | None |
| 9 | Dave Giles | REP | Ballot | 108,350 | 108,350 | 0 | None |
| 9 | Axel Bello | IND | Named write-in | 46 | 46 | 0 | None |

### 2018 General

| District | Candidate | Party | Write-in/category | County sum | Official district | Difference | Missing county GEOIDs |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Wendy Rogers | REP | Ballot | 122,784 | 122,784 | 0 | None |
| 1 | Tom O'Halleran | DEM | Ballot | 143,240 | 143,240 | 0 | None |
| 1 | David Shock | IND | Named write-in | 65 | 65 | 0 | None |
| 2 | Melissa Grable | REP | Named write-in | 19 | 19 | 0 | None |
| 2 | Lea Marquez Peterson | REP | Ballot | 133,083 | 133,083 | 0 | None |
| 2 | Ann Kirkpatrick | DEM | Ballot | 161,000 | 161,000 | 0 | None |
| 2 | Jordan Flayer | IND | Named write-in | 50 | 50 | 0 | None |
| 3 | Nicolas "Nick" Pierson | REP | Ballot | 64,868 | 64,868 | 0 | None |
| 3 | Raúl Grijalva | DEM | Ballot | 114,650 | 114,650 | 0 | None |
| 4 | Paul Gosar | REP | Ballot | 188,842 | 188,842 | 0 | None |
| 4 | David Brill | DEM | Ballot | 84,521 | 84,521 | 0 | None |
| 4 | Haryaksha Gregor Knauer | GRN | Ballot | 3,672 | 3,672 | 0 | None |
| 5 | Andy Biggs | REP | Ballot | 186,037 | 186,037 | 0 | None |
| 5 | Joan Greene | DEM | Ballot | 127,027 | 127,027 | 0 | None |
| 6 | David Schweikert | REP | Ballot | 173,140 | 173,140 | 0 | None |
| 6 | Anita Malik | DEM | Ballot | 140,559 | 140,559 | 0 | None |
| 7 | James "007" Bond IV | REP | Named write-in | 301 | 301 | 0 | None |
| 7 | Ruben Gallego | DEM | Ballot | 113,044 | 113,044 | 0 | None |
| 7 | Gary Swing | GRN | Ballot | 18,706 | 18,706 | 0 | None |
| 8 | Debbie Lesko | REP | Ballot | 168,835 | 168,835 | 0 | None |
| 8 | Hiral Tipirneni | DEM | Ballot | 135,569 | 135,569 | 0 | None |
| 8 | Steven Hummel | NPP | Named write-in | 13 | 13 | 0 | None |
| 9 | Stephen L Ferrara | REP | Ballot | 101,662 | 101,662 | 0 | None |
| 9 | Greg Stanton | DEM | Ballot | 159,583 | 159,583 | 0 | None |

### 2020 General

| District | Candidate | Party | Write-in/category | County sum | Official district | Difference | Missing county GEOIDs |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | Tom O'Halleran | DEM | Ballot | 188,469 | 188,469 | 0 | None |
| 1 | Tiffany Shedd | REP | Ballot | 176,709 | 176,709 | 0 | None |
| 2 | Iman Bah | IND | Named write-in | 99 | 99 | 0 | None |
| 2 | Ann Kirkpatrick | DEM | Ballot | 209,945 | 209,945 | 0 | None |
| 2 | Brandon Martin | REP | Ballot | 170,975 | 170,975 | 0 | None |
| 2 | Brandon Schlass | CSM | Named write-in | 35 | 35 | 0 | None |
| 3 | Raúl Grijalva | DEM | Ballot | 174,243 | 174,243 | 0 | None |
| 3 | Daniel Wood | REP | Ballot | 95,594 | 95,594 | 0 | None |
| 4 | Brett Brennan | LBT | Named write-in | 67 | 67 | 0 | None |
| 4 | Delina DiSanto | DEM | Ballot | 120,484 | 120,484 | 0 | None |
| 4 | Paul Gosar | REP | Ballot | 278,002 | 278,002 | 0 | None |
| 4 | Miko Jones | DEM | Named write-in | 19 | 19 | 0 | None |
| 4 | Don Overholser | REP | Named write-in | 5 | 5 | 0 | None |
| 4 | Ana Perez Gissy | IND | Named write-in | 39 | 39 | 0 | None |
| 4 | Emily Robinson | IND | Named write-in | 7 | 7 | 0 | None |
| 5 | Andy Biggs | REP | Ballot | 262,414 | 262,414 | 0 | None |
| 5 | Joan Greene | DEM | Ballot | 183,171 | 183,171 | 0 | None |
| 5 | Karen Stephens | REP | Named write-in | 72 | 72 | 0 | None |
| 6 | David Schweikert | REP | Ballot | 217,783 | 217,783 | 0 | None |
| 6 | Hiral Tipirneni | DEM | Ballot | 199,644 | 199,644 | 0 | None |
| 7 | Joshua Barnett | REP | Ballot | 50,226 | 50,226 | 0 | None |
| 7 | Ruben Gallego | DEM | Ballot | 165,452 | 165,452 | 0 | None |
| 7 | J.Travis Kirkham | REP | Named write-in | 3 | 3 | 0 | None |
| 7 | Roxanne Rodriguez | LBT | Named write-in | 51 | 51 | 0 | None |
| 8 | Taliban Hendrix | IND | Named write-in | 18 | 18 | 0 | None |
| 8 | Debbie Lesko | REP | Ballot | 251,633 | 251,633 | 0 | None |
| 8 | Michael Muscato | DEM | Ballot | 170,816 | 170,816 | 0 | None |
| 9 | Dave Giles | REP | Ballot | 135,180 | 135,180 | 0 | None |
| 9 | Greg Stanton | DEM | Ballot | 217,094 | 217,094 | 0 | None |

### 2022 General

| District | Candidate | Party | Write-in/category | County sum | Official district | Difference | Missing county GEOIDs |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | David Schweikert | REP | Ballot | 182,336 | 182,336 | 0 | None |
| 1 | Jevin D. Hodge | DEM | Ballot | 179,141 | 179,141 | 0 | None |
| 2 | Eli Crane | REP | Ballot | 174,169 | 174,169 | 0 | None |
| 2 | Tom O'Halleran | DEM | Ballot | 149,151 | 149,151 | 0 | None |
| 2 | Chris Sarappo | IND | Named write-in | 76 | 76 | 0 | None |
| 3 | Jeff Nelson Zink | REP | Ballot | 32,475 | 32,475 | 0 | None |
| 3 | Ruben Gallego | DEM | Ballot | 108,599 | 108,599 | 0 | None |
| 4 | Kelly Cooper | REP | Ballot | 116,521 | 116,521 | 0 | None |
| 4 | Greg Stanton | DEM | Ballot | 148,941 | 148,941 | 0 | None |
| 4 | Stephan "Steve" Jones | IND | Named write-in | 36 | 36 | 0 | None |
| 5 | Andy Biggs | REP | Ballot | 182,464 | 182,464 | 0 | None |
| 5 | Javier Garcia Ramos | DEM | Ballot | 120,243 | 120,243 | 0 | None |
| 5 | Clint William Smith | IND | Ballot | 18,851 | 18,851 | 0 | None |
| 5 | Debra Jo "D-Jo" Borden | DEM | Named write-in | 32 | 32 | 0 | None |
| 6 | Juan Ciscomani | REP | Ballot | 177,201 | 177,201 | 0 | None |
| 6 | Kirsten Engel | DEM | Ballot | 171,969 | 171,969 | 0 | None |
| 6 | Avery Alexander Thornton | DEM | Named write-in | 71 | 71 | 0 | None |
| 6 | Frank Bertone | NON | Named write-in | 42 | 42 | 0 | None |
| 7 | Luis Pozzolo | REP | Ballot | 69,444 | 69,444 | 0 | None |
| 7 | Raúl Grijalva | DEM | Ballot | 126,418 | 126,418 | 0 | None |
| 8 | Debbie Lesko | REP | Ballot | 197,555 | 197,555 | 0 | None |
| 8 | Alixandria Guzman | DEM | Named write-in | 2,013 | 2,013 | 0 | None |
| 8 | Jeremy Spreitzer | DEM | Named write-in | 5,145 | 5,145 | 0 | None |
| 9 | Paul Gosar | REP | Ballot | 192,796 | 192,796 | 0 | None |
| 9 | Richard Grayson | DEM | Named write-in | 3,531 | 3,531 | 0 | None |
| 9 | Tom T. | DEM | Named write-in | 858 | 858 | 0 | None |

### 2024 General

| District | Candidate | Party | Write-in/category | County sum | Official district | Difference | Missing county GEOIDs |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | David Schweikert | REP | Ballot | 225,538 | 225,538 | 0 | None |
| 1 | Amish Shah | DEM | Ballot | 208,966 | 208,966 | 0 | None |
| 2 | Eli Crane | REP | Ballot | 221,413 | 221,413 | 0 | None |
| 2 | Jonathan Nez | DEM | Ballot | 184,963 | 184,963 | 0 | None |
| 2 | David Alexander | DEM | Named write-in | 22 | 22 | 0 | None |
| 2 | Richard William Ester | IND | Named write-in | 28 | 28 | 0 | None |
| 2 | Charles "Charlie" Everette Holt Jr. | NON | Named write-in | 5 | 5 | 0 | None |
| 3 | Jeff Zink | REP | Ballot | 53,705 | 53,705 | 0 | None |
| 3 | Yassamin Ansari | DEM | Ballot | 143,336 | 143,336 | 0 | None |
| 3 | Alan Aversa | GRN | Ballot | 5,008 | 5,008 | 0 | None |
| 3 | Candace Cunningham | GRN | Named write-in | 16 | 16 | 0 | None |
| 4 | Kelly Cooper | REP | Ballot | 152,052 | 152,052 | 0 | None |
| 4 | Greg Stanton | DEM | Ballot | 176,428 | 176,428 | 0 | None |
| 4 | Vincent Beck-Jones | GRN | Ballot | 6,065 | 6,065 | 0 | None |
| 5 | Andy Biggs | REP | Ballot | 255,628 | 255,628 | 0 | None |
| 5 | Katrina Schaffner | DEM | Ballot | 167,680 | 167,680 | 0 | None |
| 6 | Juan Ciscomani | REP | Ballot | 215,596 | 215,596 | 0 | None |
| 6 | Kirsten Engel | DEM | Ballot | 204,774 | 204,774 | 0 | None |
| 6 | Athena Eastwood | GRN | Ballot | 10,759 | 10,759 | 0 | None |
| 6 | Luis Pozzolo | IND | Named write-in | 91 | 91 | 0 | None |
| 7 | Daniel Francis Butierez Sr. | REP | Ballot | 99,057 | 99,057 | 0 | None |
| 7 | Raúl M. Grijalva | DEM | Ballot | 171,954 | 171,954 | 0 | None |
| 8 | Abraham "Abe" Hamadeh | REP | Ballot | 208,269 | 208,269 | 0 | None |
| 8 | Gregory Whitten | DEM | Ballot | 160,344 | 160,344 | 0 | None |
| 9 | Paul Gosar | REP | Ballot | 249,583 | 249,583 | 0 | None |
| 9 | Quacy Smith | DEM | Ballot | 132,640 | 132,640 | 0 | None |
