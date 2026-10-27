# Data methodology

## Coverage

| Year | Office | Candidate records | Counties | Status | Official turnout |
| --- | --- | ---: | ---: | --- | --- |
| 2026 | Arizona Governor, general | No candidate results released/imported as of October 27 | 15 | Pre-results participation; source-checked metrics with separate coverage | Registration all counties; early returns 2 counties; no derived turnout |
| 2026 | Arizona Attorney General, general | No candidate results released/imported as of October 27 | 15 | Pre-results participation shared with Governor event | Same event-level metrics; no AG vote records |
| 2022 | Arizona Governor, general | 9 (7 named write-ins) | 15 | Verified against official statewide candidate totals | All counties and statewide |
| 2022 | Arizona Attorney General, general | 3 (1 named write-in) | 15 | Verified against official statewide candidate totals | Event-level official turnout shared with Governor |
| 2018 | Arizona Governor, general | 8 (5 named write-ins) | 15 | Verified against official statewide candidate totals; alternative inputs documented below | All counties and statewide |
| 2018 | Arizona Attorney General, general | 3 (1 named write-in) | 15 | Verified against official statewide candidate totals | Event-level official turnout shared with Governor |
| 2014 | Arizona Governor, general | 10 (6 named write-ins) | 15 | Verified against official statewide candidate totals | All counties and statewide |
| 2014 | Arizona Attorney General, general | 3 (1 named write-in) | 15 | Verified against official statewide candidate totals | Event-level official turnout shared with Governor |

The county geometry always has 15 features, including when a selected election has no verified results. Geographic coverage is distinct from result completeness.

## Authoritative election sources

- [2022 official canvass landing page](https://azsos.gov/elections/results-data/election-information/2022-election-information/2022-general-election-canvass).
- [2022 statewide canvass PDF, December 5, 2022](https://apps.azsos.gov/election/2022/General/canvass/2022dec05_general_election_canvass_web.pdf): page 2, governor; page 1, turnout. Its county columns run Apache, Cochise, Coconino, Gila, Graham, **Greenlee, La Paz**, Maricopa, Mohave, Navajo, Pima, Pinal, Santa Cruz, Yavapai, Yuma, then TOTAL. The extracted header wraps Greenlee, but the numeric column position is retained. The 2022 landing page lists an amended Navajo county document received December 2, before the December 5 statewide certification.
- [2022 official recount information](https://azsos.gov/elections/results-data/election-information/2022-election-information/2022-general-elections): attorney general, superintendent of public instruction and legislative district 13 were recounted; governor was not listed. Those recounts do not replace the governor table used here.
- [2014 general election information](https://apps.azsos.gov/election/2014/general/electioninformation.htm) and [official canvass PDF, December 1, 2014](https://apps.azsos.gov/election/2014/general/Canvass2014GE.pdf): page 2, governor; page 1, turnout. The linked congressional district 2 recount does not concern the governor contest.
- [2018 election information](https://azsos.gov/elections/election-information/2018-election-information) and [official canvass PDF](https://apps.azsos.gov/election/2018/2018_1203_signed_official_statewide_canvass.pdf). Governor results on printed page 2 and official registration/turnout on printed page 1. Its indexed tables were recovered during the 2018 update; an ambiguous write-in row was audited using actual OpenElections county records, as described below.

All sources were investigated on **October 27, 2026**. No election-night totals were substituted. For 2018, VEST and OpenElections provide documented secondary input records checked against official statewide totals and county references.

## Source acquisition limitation and retained snapshots

Direct local requests for the Arizona official PDFs returned Cloudflare HTTP 403, including an alternate `azsos.gov` 2018 URL. The web-reading tool could extract readable 2022 and 2014 tables. Their governor and turnout rows were transcribed into the versioned `data/raw/*-transcription.csv` files, preserving published integers, candidate names/affiliations, genuine zeros, and reported turnout. The transcriptions were reviewed against the readable official tables. This is a reviewed intermediate-data workflow, not a claim that an original PDF binary was downloaded or checked in.

`data/raw/source-manifest.json` records source URLs, table pages, acquisition method and separate SHA256 checksums for the vote and turnout CSV snapshots. `Source.sha256` identifies the vote CSV snapshot; it does **not** identify the inaccessible source PDF. The Census provenance checksum identifies the downloaded Census archive. The optional downloader exits nonzero on failed requests and never replaces source data with fabricated values.

The 2018 direct PDF download remains blocked, but indexed canvass tables and public VEST/OpenElections inputs were obtained. The prior availability record is retained only as historical context at `data/raw/2018/prior-availability.json`. The complete 2018 input and reconciliation procedure is documented below.

## Reproducible transformations

1. `download_sources.py` optionally acquires missing original public files with bounded request timeouts; existing snapshots are preserved. It may fail on official server access restrictions.
2. `normalize_transcription.py` reads the retained CSVs and writes year JSON; for 2018 it delegates to the source-specific `normalize_2018.py` adapter. County identifiers remain five-character strings. Blank numeric fields become JSON `null`; explicit `0` remains integer zero. Original candidate names and affiliation codes remain source labels.
3. `geography.py` reads the retained official Census ZIP, filters `STATEFP == "04"`, retains the 15 polygons and emits GeoJSON/provenance. It does not draw approximate shapes or join by names.
4. `import_data.py` independently reads the authoritative-reference statewide totals and candidate roster from the raw vote CSV, validates normalized results, loads them transactionally, and records reconciliation. Existing contest result cells are replaced rather than accumulated. Repeated imports retain one event/contest/participation/result cell while appending an import audit record.
5. `bootstrap.py` executes migrations and these source-snapshot steps in order. It requires no current source-server access.

The optional `normalize.py` extracts text from locally available PDFs. Its automatic parser is restricted to the known nine-candidate 2022 layout; historical extraction requires review and is not used as an unreviewed fallback. Unexpected layouts are reported rather than silently imported. A newly acquired PDF should be audited against the retained CSVs before replacing the reviewed source snapshots.

## Strict reconciliation

A verified contest must have the complete authoritative candidate roster, the expected 15 geographic identifiers, integer nonnegative values for every candidate/county cell, and an exact match between each county sum and the independently read published statewide candidate total. The normalized statewide value must also equal that reference. Each non-null county cell and each candidate affiliation/write-in flag is also compared with the retained source CSV; a mismatch prevents verification and the affected values are marked unverified. Turnout counts and percentages are type/range validated. Missing candidates, unexpected candidates, missing/null county cells and numerical discrepancies prevent verification. Type errors, duplicate candidates and unknown identifiers fail validation.

`data/processed/reconciliation.json` includes each candidate's county sum, official reference total, normalized statewide total, exact difference, missing counties, county source-cell mismatches, candidate metadata/roster discrepancies, coverage, source URL and reference snapshot checksum. Missing statewide reference values cannot yield verification. Dataset status and the report are stored in `ImportRun`; every value links to a `Source`.

For 2022 the authoritative statewide reference totals and verified county sums are:

| Candidate | Votes | County sum minus official |
| --- | ---: | ---: |
| Katie Hobbs | 1,287,891 | 0 |
| Kari Lake | 1,270,774 | 0 |
| Liana West (write-in) | 254 | 0 |
| Mikaela “Mikki” Shonnie Lutes-Burton (write-in) | 213 | 0 |
| William Josué Pounds IV (write-in) | 139 | 0 |
| Steph “Steph” Noelle Denny (write-in) | 74 | 0 |
| Alice Novoa (write-in) | 55 | 0 |
| RayShawn “Shawn” D'Anthony Merrill (write-in) | 44 | 0 |
| Anthony Camboni (write-in) | 41 | 0 |

The 2022 contest denominator is **2,559,485** reported candidate votes, including all seven named write-ins. It is not total ballots cast. 2014 also reconciles individually for all ten candidates; the full machine-readable report is retained. Counts were not changed to force any reconciliation.

The reference totals and county cells share the official canvass as their authoritative source. Verification establishes agreement with that published record; it does not independently recount ballots. The reviewed CSV is the source snapshot, so independent re-auditing of its transcription against an original browser-downloaded PDF remains possible and useful. The app's `verified` label means source-reconciled within this documented scope.

## Missing values, candidates and party shares

- Source zero → integer `0`, displayed as zero.
- Unavailable/unverified value → `null` plus availability status, displayed as `N/A`.
- An incomplete or failed import → explicit report/status or nonzero command exit; not an all-zero election.
- An incomplete contest → no established statewide/county winner, denominator or percentage. Individual imported values can remain visible with their status.
- A tie, zero valid votes, or unknown winner → neutral map color.
- Named write-ins retain individual records. No unattributed vote is assigned to a named person. None of the three certified governor tables contains an additional aggregate write-in row. The 2018 VEST aggregate is an alternative-source audit field, not an additional certified candidate. The participation model reserves `aggregate_write_in` for a source that reports one.
- Candidate percentages use the sum of all verified contest candidate votes. Display rounding is two decimals; positive shares below 0.01% appear as `<0.01%`. Rounded shares need not add to exactly 100.00%.
- Compact Democratic/Republican columns sum all affiliated candidates, including affiliated write-ins. They are party shares, while the county winner is the highest individual candidate total.

## Official turnout

Stored values retain **total ballots cast**, **total eligible registration**, **reported voter turnout percentage**, the source ID and the definition. The reported definition is ballots cast divided by eligible registration, rounded by the official source. The importer does not replace the source percentage with a recalculated rate.

For example, 2022 Maricopa reports 1,562,758 ballots, 2,435,397 eligible registrations and **64.17%** turnout, while its governor contest contains **1,543,535** reported candidate votes. These are distinct quantities. Statewide 2022 turnout is **62.56%** (2,592,313 ballots; 4,143,929 eligible registrations). Turnout is election-wide and attached to the event, not candidate votes. 2018 official turnout is populated statewide and for all 15 counties: statewide ballots 2,409,910; eligible registration 3,716,263; reported turnout 64.85%. Its contest denominator is separately 2,376,441.

## Geography

- [U.S. Census Bureau 2022 cartographic boundaries](https://www.census.gov/geographies/mapping-files/time-series/geo/cartographic-boundary.2022.html).
- [Official 2022 national county shapefile, 1:500,000](https://www2.census.gov/geo/tiger/GENZ2022/shp/cb_2022_us_county_500k.zip).

The downloaded ZIP is retained under `data/raw/counties.zip`; the Arizona-only GeoJSON and checksum metadata are under `data/geography`. These are official Census generalized cartographic boundaries, not full-resolution TIGER/Line road/administrative extracts. Their scale is suitable for this fixed, statewide no-zoom display. No additional simplification is performed. Stable five-digit GEOIDs connect results to geography; names are labels only.

Boundary version `county-2022` stores vintage 2022 explicitly. Both imported historical governor contests use that common county visualization layer. Future district elections require separate vintage-correct geometry and identifiers; this map must not be assumed appropriate for historical congressional or legislative districts.

## Known limitations

2018 certified candidate totals now reconcile fully; VEST’s broader aggregate write-in field remains excluded and separately documented. Original Arizona PDFs were unavailable to direct local downloads, making retained reviewed transcriptions the reproducible numerical source snapshots. Automated statewide reconciliation cannot detect an equal-and-opposite county transcription error, so source review matters. No precinct/district results, race-level ballots/overvotes/undervotes, or historical boundary vintages beyond county-2022 have been imported. These limitations are exposed/documented rather than filled with estimates.

## 2018 source acquisition, normalization and validation

The 2018 general election is now available with **15 counties, eight candidates and five named write-ins**, all reconciled to the separately published official statewide totals. The import does not use the statewide validation targets as county data.

### Retained inputs and provenance

- Authority: [official statewide canvass](https://apps.azsos.gov/election/2018/2018_1203_signed_official_statewide_canvass.pdf), printed page 2 (governor) and page 1 (registration, ballots, turnout). Direct requests returned Cloudflare HTTP 403. Indexed official tables were available through search extraction. Governor and turnout references are retained in `data/raw/2018-governor-transcription.csv` and `data/raw/2018-turnout-transcription.csv`. See the write-in extraction correction below: the governor reference is reviewed against actual OpenElections records rather than trusting the indexed table's column reconstruction.
- Independent official statewide check: [Arizona Secretary of State new-party guide](https://azsos.gov/sites/default/files/2023-11/new_party_guide_final_202108.pdf), section IV, lists all eight 2018 governor candidate totals and the 2,376,441 contest total.
- Ballot-candidate input: [UF Election Lab Arizona 2018 dataset page](https://election.lab.ufl.edu/dataset/az-2018-precinct-level-election-results/), produced by VEST; [public ZIP](https://election.lab.ufl.edu/data-downloads/resultsdata/2018/precinct/az_2018.zip), retained at `data/raw/2018/az_2018.zip`. Citation: [VEST 2018 precinct results, Harvard Dataverse](https://doi.org/10.7910/DVN/UBKYRU); the Arizona file was updated June 2, 2021. The UF public ZIP was accessible even though direct Harvard API requests returned HTTP 403. The pipeline uses the public original archive; it requires no UF login or fee-for-service product.
- VEST [source/field documentation](https://election.lab.ufl.edu/data-downloads/resultsdata/2018/precinct/documentation.txt) is retained locally. It identifies `G18GOVRDUC` (Ducey), `G18GOVDGAR` (Garcia), `G18GOVGTOR` (Torres) and `G18GOVOWRI` (aggregate write-ins).
- Named write-in input and cross-check: [OpenElections county CSV at pinned revision 5675ad1dbf77ce24fdd320127215f81b17e1a866](https://github.com/openelections/openelections-data-az/blob/5675ad1dbf77ce24fdd320127215f81b17e1a866/2018/20181106__az__general__county.csv), retained as `data/raw/2018/openelections-county.csv`. Its governor records preserve each named candidate across all 15 counties and a separate TOTAL record. No missing county record is synthesized.
- [State Library archive reference](https://azmemory.azlibrary.gov/nodes/view/102727) was investigated; its direct page/PDF downloads remained blocked. Its indexed OCR corroborates the official source, but that OCR is not used to guess missing digits or allocations.
- MEDSL's [2018 repository](https://github.com/MEDSL/2018-elections-official) was investigated. Its Arizona precinct file uses a general `WRITEIN` category, so it cannot establish the five named write-in allocations and was not selected as an input.

`data/raw/source-manifest.json` records all input checksums, acquisition failures, source URLs and the pinned OpenElections revision. SHA256 for a retained CSV means that CSV's bytes, not the official PDF. `scripts/download_2018.py` validates existing inputs or reacquires missing public files, refusing to overwrite a snapshot with a different hash. Optional `--try-official` checks for a local PDF under `data/raw/2018/` before retrying the official URL. Normalization is offline and checks the retained snapshot hashes first.

### Extraction correction: Dolego

The indexed governor table initially reconstructed Dolego's row with Navajo **2** and Pinal **0**, yielding 14 county votes against the official statewide **13**. The validator rejected that extraction. The unreviewed extraction is retained at `data/raw/2018/indexed-governor-unreviewed.csv` for audit, and is **not** an election input.

Actual OpenElections records at the pinned revision give Navajo **0** and Pinal **1**, with all other Dolego county cells unchanged. These actual records sum to the official 13. The reference CSV was corrected from those records; no value was inferred by distributing a residual. Every other governor candidate/county cell in the retained official-reference table matches the OpenElections source as retrieved. The official [Yavapai named write-in result PDF](https://www.yavapaivotes.gov/files/assets/elections/v/1/documents/results/2018/november-6-2018-election-generalgeneral_2018_write-in_ballot_results.pdf), downloaded locally, also corroborates Yavapai's zero for Dolego. This separates an extraction/column-placement error from a change to certified election results.

### Aggregation and the VEST aggregate discrepancy

`normalize_2018.py` reads the ZIP's DBF directly using the existing PyShp dependency. It validates **1,489 unique precinct records**, explicit source county codes mapped to Census GEOIDs, integer nonnegative votes and all 15 counties. A null, duplicate precinct, unknown code or missing candidate/unit record raises an error; absent values never become zero.

All **45 ballot-candidate county cells** (three candidates × 15 counties) agree exactly with the official county reference and OpenElections. VEST supplies those county values. The five named write-in candidates use the actual OpenElections county rows; their independent statewide totals match the official canvass. All eight statewide result cells and turnout records cite the official canvass; the 45 VEST and 75 OpenElections county cells carry their respective source IDs in SQLite. The existing API exposes all four source references, including Census geography.

VEST's `G18GOVOWRI` sums to **3,203**, which is **2,928 more** than the official **275 named write-in** votes. It is a broader reporting category, not the five certified candidate totals. Investigation of Maricopa's [final official county summary](https://elections.maricopa.gov/asset/jcr%3A097c22c0-1af9-4570-8257-1af35576f9e5/11-06-2018%20Canvass%20BOS%20SUMMARY%20NOV%202018.pdf) confirms the same **1,935** general write-ins as VEST, whereas its separately reported named candidates total **178**. The county's official named write-in appendix lists the individual candidate counts.

The VEST aggregate is retained **unchanged** in `data/processed/2018/vest-comparison.json`, including the exact discrepancy for every county. It is excluded from certified result records and the percentage denominator. It is not reduced by 2,928, assigned to named candidates, or added on top of the named candidates. This does not assert the legal validity of every vote in that broader aggregate; it records the category mismatch and the evidence for its exclusion.

### Candidate reconciliation and turnout

| Candidate | Official statewide | Sum across 15 counties | Difference |
| --- | ---: | ---: | ---: |
| Doug Ducey (REP) | 1,330,863 | 1,330,863 | 0 |
| David Garcia (DEM) | 994,341 | 994,341 | 0 |
| Angel Torres (GRN) | 50,962 | 50,962 | 0 |
| Patrick Masoya (NONE, write-in) | 177 | 177 | 0 |
| Christian Komor (NONE, write-in) | 66 | 66 | 0 |
| Cary D. Dolego (GRN, write-in) | 13 | 13 | 0 |
| Arthur Ray “RT” Arvizu (RTO, write-in) | 12 | 12 | 0 |
| James “MarvelMan” Gibson II (HUM, write-in) | 7 | 7 | 0 |
| **Total** | **2,376,441** | **2,376,441** | **0** |

RTO/HUM affiliations retain their source codes; the UI labels them “as reported” rather than guessing expanded party names. Named write-ins total **275**. All 120 candidate/county cells are present, including genuine zeroes.

Official registration, ballots and reported turnout percentages cover all 15 counties and statewide. County registration sums to **3,716,263**, and ballots sum to **2,409,910**, matching the official statewide figures. Statewide turnout is the source's **64.85%**. Source percentages are preserved rather than recomputed. For example, Maricopa reports 2,254,596 eligible registrations, 1,454,103 ballots and 64.50% turnout; those ballots are distinct from its **1,432,938** certified governor candidate votes.

### Reproduction and outcomes

```sh
python scripts/normalize_2018.py
python scripts/import_data.py --year 2018
```

The existing `normalize_transcription.py` and `bootstrap.py` also invoke the 2018 adapter. The old top-level availability placeholder has been archived, preventing it from overwriting the completed normalized dataset. The year-scoped importer preserves other election years' contest records and imports both 2018 statewide contests into `data/processed/reconciliation.json`; repeat imports replace result cells without duplicating contests, candidates, vote records or turnout. Source discrepancies cause nonzero failure instead of vote adjustment.

The completed import has **zero outstanding certified-candidate discrepancies**. The separate VEST aggregate mismatch remains visible as a documented excluded category. API, clean-database/repeat-import checks and browser interactions are recorded in [the 2018 import report](2018-import-report.md). All 2014 and 2022 normalized file hashes and API payload hashes were unchanged by the scoped update.

## 2026 participation extension

The current 2026 general-election page reports official participation rather than candidate votes before results are released. See the [2026 source and validation report](2026-import-report.md) for source URLs, exact definitions, report/retrieval timestamps, county coverage, preserved source discrepancies, manual refresh commands and future result-certification requirements. The historical methodology above remains applicable to certified historical results.

## U.S. Senate coverage status (October 27, 2026)

Arizona U.S. Senate elections held since 2014 were the regular elections in **2016, 2018, 2022 and 2024**, plus the **November 3, 2020 special election**. There was no Arizona U.S. Senate election in 2014 or 2026, and 2018 had one Senate contest. The earlier coverage description incorrectly identified those years and has been corrected. See the [U.S. Senate's Arizona senator history](https://www.senate.gov/states/AZ/senators.htm), [official 2022 statewide canvass](https://apps.azsos.gov/election/2022/General/canvass/2022dec05_general_election_canvass_web.pdf), and [Congressional Directory documenting the 2020 special election](https://www.govinfo.gov/content/pkg/CDIR-2022-10-26/html/CDIR-2022-10-26-AZ.htm).

The invalid 2026 Senate contest has been removed from the local database and the current-election lifecycle. The existing 2026 general-election event and Governor/Attorney General participation records remain available. Historical Senate results have not yet been imported or reconciled. The existing 2018 OpenElections file may be evaluated against the single official 2018 Senate contest; its single race label is not evidence of merged contests.

The historical Senate import prompt is documented in [us-senate-import-prompt.md](us-senate-import-prompt.md). Historical county results require source acquisition, complete candidate/write-in rosters and candidate-level reconciliation before verification can be claimed.
