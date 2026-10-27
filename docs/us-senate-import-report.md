# Arizona U.S. Senate import and verification report

Completed locally on October 27, 2026. No deployment was performed. The five Senate elections are available in the existing application catalog, API, map, table, county details and year selector.

## Coverage and outcomes

| Year | Contest | Counties | Candidates | Named write-ins | Certified contest votes | Candidate discrepancies |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 2016 | Regular | 15 | 11 | 8 | 2,530,730 | 0 |
| 2018 | Regular | 15 | 10 | 7 | 2,384,308 | 0 |
| 2020 | Special | 15 | 19 | 17 | 3,355,317 | 0 |
| 2022 | Regular | 15 | 11 | 8 | 2,572,294 | 0 |
| 2024 | Regular | 15 | 10 | 7 | 3,348,814 | 0 |

All **61 candidate records and 915 candidate/county vote cells** are present. All 47 officially reported named write-ins are included. Every candidate's county sum matches the official printed statewide total; roster, county and metadata checks pass. The total across candidates is the certified contest-vote denominator, distinct from ballots cast. Explicit zeros remain integers; missing values remain null and cause incomplete reconciliation. No candidate county values were allocated from statewide residuals.

There was no Arizona U.S. Senate election in 2014 or 2026. The 2018 contest is a single regular election; the special election occurred November 3, 2020 for the term expiring January 2023. The 2020 contest uses ID `az-2020-us-senate-special`; the general-election event remains `az-2020-general`, and the API returns contest kind `special`. The existing schema supports these identities without a migration. Catalog/page labels and the year selector use existing text positions; CSS, layout and visual design are unchanged.

## Official sources and retained records

Direct requests to the official PDF host returned Cloudflare HTTP 403. Rejected responses were HTML challenges, not usable PDFs. The acquisition failures are recorded at `data/raw/us-senate/acquisition-failures.json`. Official indexed tables were inspected and retained as text; they are identified as extracts rather than original PDF binaries.

| Year | Official canvass | Published report time (America/Phoenix) | Senate page | Retained input and extraction |
| --- | --- | --- | ---: | --- |
| 2016 | [Official PDF](https://apps.azsos.gov/election/2016/General/Official%20Signed%20State%20Canvass.pdf) | 2016-11-29T15:03:33-07:00 | 11 | Original signed PDF from pinned mirror; visually reviewed CSV |
| 2018 | [Official PDF](https://apps.azsos.gov/election/2018/2018_1203_signed_official_statewide_canvass.pdf) | 2018-11-30T08:11:45-07:00 | 1 | Indexed official canvass table text and reviewed CSV |
| 2020 | [Official PDF](https://apps.azsos.gov/election/2020/2020_general_state_canvass.pdf) | 2020-11-24T13:35:33-07:00 | 5 | Original official XML ZIP from pinned mirror; independent final-canvass indexed table and reviewed CSV |
| 2022 | [Official PDF](https://apps.azsos.gov/election/2022/General/canvass/2022dec05_general_election_canvass_web.pdf) | 2022-12-05T10:00:00-07:00 | 1 | Indexed official canvass table text and reviewed CSV |
| 2024 | [Official PDF](https://apps.azsos.gov/election/2024/ge/canvass/20241105_GeneralCanvass_Signed.pdf) | 2024-11-22T19:04:17-07:00 | 5 | Indexed official canvass table text and reviewed CSV |

All indexed extracts were retrieved October 27, 2026; retrieval precision is date only. Original-document mirror retrieval instants and pinned URLs are in `data/raw/us-senate/mirror-acquisition.json`. Both original files were fetched again at public repository commit **5195a57d913c839106ce1d2de32e3510d9ef3d3a** and their bytes compared with the retained copies:

- [2016 original official signed PDF, mirrored copy](https://raw.githubusercontent.com/Camreyn/civicresultmaps/5195a57d913c839106ce1d2de32e3510d9ef3d3a/data/az-2016-general-official-signed-state-canvass.pdf): SHA256 `a765b3d03bcbdcaba4e3e869bd24cbb6dc2288841d7848eaa18b46e099ccaada`.
- [2020 original official detailed-results XML ZIP, mirrored copy](https://raw.githubusercontent.com/Camreyn/civicresultmaps/5195a57d913c839106ce1d2de32e3510d9ef3d3a/data/az-2020-general-results-detail.xml.zip): SHA256 `542f2e4d60463d6ad23b78e2de0f73759806945c6bcaedc6c0a7dd7aec422c06`. Original publisher URL: [Arizona Secretary of State XML](https://apps.azsos.gov/election/2020/resultsdetail_2020generalxml.zip).

The mirror is the acquisition route; the original documents identify Arizona Secretary of State as publisher. Every 2020 XML Senate county cell, state total, candidate party and write-in flag is independently compared against the final canvass. The XML report timestamp is **November 24, 2020, 12:58:30.96 MST**; the final canvass report is **13:35:33 MST** the same day, and the Senate numbers agree completely. The source-name difference `Mathew Haupt` in XML versus `Matthew Haupt` in the final canvass is documented and mapped explicitly, without changing votes or affiliation.

Each `data/raw/us-senate/YEAR-provenance.json` lists SHA256 hashes for the actual retained PDF/ZIP, indexed text and reviewed CSV files. Main canvass `Source.sha256` values identify the reviewed candidate CSV, while the supplementary 2020 XML source identifies the ZIP binary and is attached to actual county vote and turnout records. No checksum is represented as the hash of an original PDF that was not obtained. Normalization and direct imports validate retained snapshot checksums; a changed source is rejected.

### Extraction review and secondary-source discrepancies

- **2016:** The PDF's hidden text layer omits eleven visible one-vote cells in the Senate table: Sheila Bilyeu (Coconino, Pinal, Yuma); Gene Scott II (Yuma); Sydney Dudikoff (Santa Cruz); Anthony Camboni (Apache, Coconino, Yuma); Leonard Clark (Pinal, Yuma); Selena Lopez (Coconino). These values were read directly from rendered page 11, including their county positions. The entire candidate table and page-1 turnout were visually reviewed. Missing text-layer glyphs were not interpreted as zero or solved from statewide differences.
- **2018:** The retained [OpenElections county source](https://github.com/openelections/openelections-data-az/blob/5675ad1dbf77ce24fdd320127215f81b17e1a866/2018/20181106__az__general__county.csv) has 159 of the expected 160 candidate/unit records. It omits **Jeff Pearce in Mohave**; its present county rows sum to **28**, versus its statewide record and official canvass total **29**. The official canvass explicitly reports **1 in Mohave**. The Senate import uses official table records for every cell and preserves the discrepancy in `data/processed/us-senate/validation/2018-openelections-comparison.json`. All other present vote cells agree. Michael DeCarlo's explicit official `NONE` affiliation is used; the blank secondary field remains unchanged in the source. There is no inference from absence and no change to the retained secondary source.
- **2024:** All county totals independently match the retained secondary comparison CSV's Democratic, Republican and combined-other buckets. That secondary aggregation is corroboration only; the complete official 10-candidate roster supplies the actual imported values. See `validation/2024-secondary-comparison.json`. Source codes ATP, TOR, IRP, UPA and UAT are displayed as reported without guessed party expansions.
- **Write-in scope:** These statewide canvasses report named candidates. Broader county write-in aggregates can include unassigned/scattered marks and are not added alongside the named candidates. No aggregate category appearing in the statewide Senate canvass was omitted.

Original PDF binaries remain unavailable for 2018, 2020, 2022 and 2024; retained official indexed text supplies their final-canvass reference. The 2020 official XML and 2016 signed PDF are available as original document bytes. Reviewed transcriptions are part of the reproducible input workflow; the pipeline is not advertised as an automatic general-purpose PDF/OCR extractor.

## Candidate-level statewide reconciliation

Every difference below is the sum of the 15 county records minus the independently printed official statewide TOTAL.

### 2016 regular election

| Candidate | Party | Write-in | Official statewide | County sum | Difference |
| --- | --- | --- | ---: | ---: | ---: |
| Sheila Bilyeu | DEM | Yes | 34 | 34 | 0 |
| Ann Kirkpatrick | DEM | No | 1,031,245 | 1,031,245 | 0 |
| Gene Scott II | DEM | Yes | 7 | 7 | 0 |
| Gary Swing | GRN | No | 138,634 | 138,634 | 0 |
| Sydney Dudikoff | REP | Yes | 494 | 494 | 0 |
| John McCain | REP | No | 1,359,267 | 1,359,267 | 0 |
| Anthony Camboni | NONE | Yes | 45 | 45 | 0 |
| Santos Chavez | NONE | Yes | 4 | 4 | 0 |
| Leonard Clark | IND | Yes | 83 | 83 | 0 |
| Selena Lopez | IND | Yes | 223 | 223 | 0 |
| Pat Quinn | IND | Yes | 694 | 694 | 0 |

### 2018 regular election

| Candidate | Party | Write-in | Official statewide | County sum | Difference |
| --- | --- | --- | ---: | ---: | ---: |
| Robert Kay | REP | Yes | 37 | 37 | 0 |
| Martha McSally | REP | No | 1,135,200 | 1,135,200 | 0 |
| Sheila Bilyeu | DEM | Yes | 42 | 42 | 0 |
| Kyrsten Sinema | DEM | No | 1,191,100 | 1,191,100 | 0 |
| Barry Hess | LBT | Yes | 365 | 365 | 0 |
| Angela Green | GRN | No | 57,442 | 57,442 | 0 |
| Edward Davida | ATP | Yes | 2 | 2 | 0 |
| Michael DeCarlo | NONE | Yes | 45 | 45 | 0 |
| Jeff Pearce | IND | Yes | 29 | 29 | 0 |
| Jonathan Ringham B | TOR | Yes | 46 | 46 | 0 |

### 2020 special election

| Candidate | Party | Write-in | Official statewide | County sum | Difference |
| --- | --- | --- | ---: | ---: | ---: |
| Edward Davida | REP | Yes | 28 | 28 | 0 |
| Martha McSally | REP | No | 1,637,661 | 1,637,661 | 0 |
| John Schiess | REP | Yes | 92 | 92 | 0 |
| Debbie Simmons | REP | Yes | 98 | 98 | 0 |
| Patrick "Pat" Thomas | REP | Yes | 29 | 29 | 0 |
| Mohammad "Mike Obama" Arif | DEM | Yes | 68 | 68 | 0 |
| Adam Chilton | DEM | Yes | 19 | 19 | 0 |
| Perry Kapadia | DEM | Yes | 58 | 58 | 0 |
| Mark Kelly | DEM | No | 1,716,467 | 1,716,467 | 0 |
| Buzz Stewart | DEM | Yes | 22 | 22 | 0 |
| Matthew "Doc" Dorchester | LBT | Yes | 379 | 379 | 0 |
| Christopher Beckett | IND | Yes | 69 | 69 | 0 |
| William "Will" Decker | IND | Yes | 21 | 21 | 0 |
| Nicholas N. Glenn | IRP | Yes | 152 | 152 | 0 |
| Matthew Haupt | IND | Yes | 37 | 37 | 0 |
| Benjamin Rodriguez | IND | Yes | 17 | 17 | 0 |
| Joshua Rodriguez | UPA | Yes | 69 | 69 | 0 |
| Frank Saenz | IND | Yes | 8 | 8 | 0 |
| Jim Stevens | NONE | Yes | 23 | 23 | 0 |

### 2022 regular election

| Candidate | Party | Write-in | Official statewide | County sum | Difference |
| --- | --- | --- | ---: | ---: | ---: |
| Blake Masters | REP | No | 1,196,308 | 1,196,308 | 0 |
| Mark Kelly | DEM | No | 1,322,027 | 1,322,027 | 0 |
| Marc J. Victor | LBT | No | 53,762 | 53,762 | 0 |
| Sherrise Bordes | REP | Yes | 17 | 17 | 0 |
| Christopher Bullock | REP | Yes | 27 | 27 | 0 |
| Edward Davida | REP | Yes | 3 | 3 | 0 |
| Roxanne Renee Rodriguez | REP | Yes | 20 | 20 | 0 |
| Ty Richard McLean Jr. | DEM | Yes | 21 | 21 | 0 |
| Todd James Smeltzer | DEM | Yes | 6 | 6 | 0 |
| William "Will" Michael Taylor | DEM | Yes | 8 | 8 | 0 |
| Lester "Skip" Maul | IND | Yes | 95 | 95 | 0 |

### 2024 regular election

| Candidate | Party | Write-in | Official statewide | County sum | Difference |
| --- | --- | --- | ---: | ---: | ---: |
| Kari Lake | REP | No | 1,595,761 | 1,595,761 | 0 |
| Ruben Gallego | DEM | No | 1,676,335 | 1,676,335 | 0 |
| Eduardo Quintana | GRN | No | 75,868 | 75,868 | 0 |
| Jannie "Jannie" Prosser | REP | Yes | 82 | 82 | 0 |
| Sarah Williams | LBT | Yes | 535 | 535 | 0 |
| Christopher Beckett | IND | Yes | 103 | 103 | 0 |
| David Bozic | NON | Yes | 12 | 12 | 0 |
| Shawn Petty | NON | Yes | 24 | 24 | 0 |
| Benjamin Rodriguez | UAT | Yes | 2 | 2 | 0 |
| Steven Cavin Sanders | IND | Yes | 92 | 92 | 0 |

## Event turnout and registration

| Election | County coverage | Eligible/registered voters | Ballots cast | Published statewide percent | Treatment |
| --- | --- | ---: | ---: | ---: | --- |
| 2016 | 15/15 plus statewide | 3,588,466 | 2,661,497 | 74.17% | Official canvass page 1 |
| 2018 | 15/15 plus statewide | 3,716,263 | 2,409,910 | 64.85% | Existing event record shared with Governor and Attorney General |
| 2020 | 15/15 plus statewide | 4,281,152 | 3,420,565 | 79.90% | Official XML voterTurnout fields |
| 2022 | 15/15 plus statewide | 4,143,929 | 2,592,313 | 62.56% | Existing event record shared with Governor and Attorney General |
| 2024 | 15/15 plus statewide | 4,367,593 | 3,428,011 | 78.49% | Official canvass page 1 |

County registration and ballots each sum exactly to their official statewide figure. Published percentages are retained, with original rounding. The 2020 XML fields are `ballotsCast`, `totalVoters` and `voterTurnout`; the stored definition identifies them explicitly. Turnout remains attached to each November election event rather than to the Senate contest. Existing 2018/2022 records and their source IDs were not modified. Turnout is complete official event turnout, not a candidate denominator or early-vote subset.

## Executed verification

- Backend: **23 tests passed**, covering all five election identities, 61 candidates, all county cells, shares, missing/zero handling, checksum rejection, official-source comparisons, absent 2014/2026 Senate entries, scoped-import idempotence and existing-office isolation.
- Frontend: **5 unit tests passed**; TypeScript and the Vite production build passed.
- Browser: **7 Playwright tests passed**, including the new Senate flow through all five years, 2020 special labels, county map clicks, table sorting, keyboard selection, details, mobile overflow and existing Governor/Attorney General regressions. A real Chromium browser was installed temporarily under `/tmp/az-election-playwright`; no browser dependency was added to the application.
- Clean migration/bootstrap and a second full offline bootstrap passed on a fresh temporary SQLite database. Repeated counts were identical: **13 contests, 97 candidate participations, 1,552 vote records, 96 event-turnout rows, 3 publication snapshots and 22 metric observations**. Import-run audit history may grow on replay; result/snapshot/turnout records do not duplicate.
- All **8 existing Governor/Attorney General detail and county API payload hashes** match the pre-import baseline. Source files and values for those offices were not changed. Their 2026 participation behavior remains covered by browser/backend regression tests.
- Direct local API reads expose all five Senate elections as verified. All 15 county endpoints return complete candidates and official turnout. The 2014 and 2026 Senate endpoints return 404.

No unresolved Senate candidate-vote discrepancies remain. The missing secondary 2018 row, 2016 text-layer omissions, 2020 source-name alias and original-PDF retention limitations remain explicitly documented above. No deployment or automatic data refresh was introduced.

## Reproduce and import

From the repository root, using the existing environment:

```sh
# Verify retained source hashes and regenerate the five normalized datasets offline.
.venv/bin/python scripts/normalize_us_senate.py

# Import only Senate contests, preserving other offices.
.venv/bin/python scripts/import_data.py --office us-senate

# Optional narrower import.
.venv/bin/python scripts/import_data.py --office us-senate --year 2020

# Full documented offline bootstrap (migrations, normalization, imports and retained 2026 activity).
.venv/bin/python scripts/bootstrap.py

.venv/bin/pytest -q backend/tests
npm test --prefix frontend
npm run build --prefix frontend

# Browser checks, using a temporary browser location.
cd frontend
PLAYWRIGHT_BROWSERS_PATH=/tmp/az-election-playwright npx playwright install chromium
PLAYWRIGHT_BROWSERS_PATH=/tmp/az-election-playwright npm run test:e2e
```

These historical imports use retained reviewed inputs. A source correction requires review of the actual authoritative replacement, a new source snapshot/provenance checksum and re-normalization before import. Successive cumulative election-night reports are not involved. The existing explicit 2026 refresh remains limited to Governor and Attorney General; it cannot recreate a 2026 Senate contest.
