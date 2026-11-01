# Data methodology

## Coverage

| Year | Office | Candidate records | Counties | Status | Official turnout |
| --- | --- | ---: | ---: | --- | --- |
| 2026 | Arizona Early Voting, general election | None; pre-results | 15 | One civicAPI participation catalog entry | Requested/returned: statewide and all 15 counties; all-empty table columns hidden |
| 2024 | Arizona U.S. Senate, regular | 10 (7 named write-ins) | 15 | Verified against official statewide candidate totals | All counties and statewide |
| 2022 | Arizona U.S. Senate, regular | 11 (8 named write-ins) | 15 | Verified against official statewide candidate totals | Existing event turnout shared |
| 2022 | Arizona Governor, general | 9 (7 named write-ins) | 15 | Verified against official statewide candidate totals | All counties and statewide |
| 2022 | Arizona Attorney General, general | 3 (1 named write-in) | 15 | Verified against official statewide candidate totals | Event-level official turnout shared with Governor |
| 2020 | Arizona U.S. Senate, special | 19 (17 named write-ins) | 15 | Verified against final canvass; official XML county results | All counties and statewide |
| 2018 | Arizona U.S. Senate, regular | 10 (7 named write-ins) | 15 | Verified against official statewide candidate totals | Existing event turnout shared |
| 2018 | Arizona Governor, general | 8 (5 named write-ins) | 15 | Verified against official statewide candidate totals; alternative inputs documented below | All counties and statewide |
| 2018 | Arizona Attorney General, general | 3 (1 named write-in) | 15 | Verified against official statewide candidate totals | Event-level official turnout shared with Governor |
| 2016 | Arizona U.S. Senate, regular | 11 (8 named write-ins) | 15 | Verified against signed official canvass | All counties and statewide |
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

Boundary version `county-2022` stores vintage 2022 explicitly. Imported statewide contests use that common county visualization layer. Future district elections require separate vintage-correct geometry and identifiers; this map must not be assumed appropriate for historical congressional or legislative districts.

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

The existing `normalize_transcription.py` and `bootstrap.py` also invoke the 2018 adapter. The old top-level availability placeholder has been archived, preventing it from overwriting the completed normalized dataset. The year-scoped importer preserves other election years' contest records and imports the selected 2018 contests into `data/processed/reconciliation.json`; repeat imports replace result cells without duplicating contests, candidates, vote records or turnout. Source discrepancies cause nonzero failure instead of vote adjustment.

The completed import has **zero outstanding certified-candidate discrepancies**. The separate VEST aggregate mismatch remains visible as a documented excluded category. API, clean-database/repeat-import checks and browser interactions are recorded in [the 2018 import report](2018-import-report.md). All 2014 and 2022 normalized file hashes and API payload hashes were unchanged by the scoped update.

## 2026 participation extension

The shared 2026 Early Voting page uses event-level participation from civicAPI's `/api/v2/early-vote/AZ/requested` and `/returned` feeds. The October 27 reports supply statewide and all 15 counties' Requested/Returned counts, including Democratic, Other and Republican provider categories. In these feeds, `votes` means ballot participation counts, not candidate votes. Display totals use each response's own statewide/county party buckets; county totals are never summed to produce or reconcile the statewide figure, and requested/returned stages are never added together. All supplied party counts are retained as metrics; missing values remain null and explicit zeros remain zero. The in-person feed returns 404, while registration, mailed/issued and accepted figures are not supplied. No state/county websites, candidate races, polling or forecasts are queried by the current refresh. There is no independent corroboration, arithmetic reconciliation or write-in investigation. See the [2026 early-voting report](2026-import-report.md) for exact endpoints, snapshots, timestamps, commands and technical checks. Historical source reconciliation above remains applicable to historical results.

The homepage’s Live Elections tab displays the dashboard directly. The standalone Early Voting and two old office browser URLs are removed, with no redirects. Backend API endpoints and their storage aliases are unchanged. County colors use the largest returned-ballot party-registration group: Democratic blue, Republican red, and Other/ties/missing gray. Registration does not indicate candidate choices. Only wholly missing metric columns are hidden; explicit zero values and partially populated columns remain visible.

## U.S. Senate coverage (October 27, 2026)

The regular Arizona U.S. Senate elections in **1986, 1988, 1992, 1994, 1998, 2000, 2004, 2006, 2010, 2012, 2016, 2018, 2022 and 2024**, plus the **November 3, 2020 special election**, are imported and reconciled for all 15 counties. There was no Arizona U.S. Senate election in 2014 or 2026; neither appears in the application. The 2018 election has one Senate contest. Calendar references include the [U.S. Senate's Arizona history](https://www.senate.gov/states/AZ/senators.htm), [official 2022 canvass](https://apps.azsos.gov/election/2022/General/canvass/2022dec05_general_election_canvass_web.pdf), and [Congressional Directory documenting the 2020 special election](https://www.govinfo.gov/content/pkg/CDIR-2022-10-26/html/CDIR-2022-10-26-AZ.htm).

The import covers **61 candidate records, 47 named write-ins, and 915 candidate/county cells**. Every candidate county sum equals the independently printed official statewide TOTAL. The complete official canvass rosters contain named write-ins without an additional aggregate write-in row. Broader county-report write-in aggregates are not added to these certified candidate totals. Shares use the complete certified contest-vote denominator.

The original official 2016 signed PDF and 2020 detailed-results XML ZIP are retained from a pinned public mirror after direct official requests returned HTTP 403. Indexed official canvass tables are retained for 2018, 2020, 2022 and 2024. The 2016 scan was visually reviewed, including eleven visible one-vote cells omitted from its hidden text layer. All 2020 XML county cells, statewide totals, parties and write-in flags independently agree with the final canvass; its Mathew Haupt label is displayed as Matthew Haupt following the final canvass. A missing Jeff Pearce/Mohave row in the older 2018 OpenElections file is documented; the official canvass explicitly supplies one vote. No missing secondary record is treated as zero.

`data/raw/us-senate/*-provenance.json` records report/retrieval dates, acquisition URLs, methods and checksums for each retained file. SHA256 values distinguish original PDF/ZIP bytes, indexed text, and reviewed CSV transcriptions. They do not claim a hash of an inaccessible original PDF. Normalization checks the hashes and independently compares the reviewed CSVs against retained official indexed tables; 2020 also compares the original XML cell by cell. Original PDF binaries remain unavailable for 2018, 2020, 2022 and 2024, although the official 2020 XML is retained. These retention limitations are documented in the [Senate import report](us-senate-import-report.md), with full candidate reconciliation tables and executed checks.

### Senate 1986–2012 additions

Ten earlier Senate elections were added from the official Arizona Secretary of State canvass PDFs, supplied by the project maintainer (the 1986, 1988 and 1992 canvasses are hosted under `apps.azsos.gov/election/files/hist/canvass<year>ge.pdf`) and transcribed in `scripts/transcribe_historical_senate.py`. The PDFs are retained in `data/raw/us-senate/pdfs/` and their SHA-256 values are recorded in each provenance file. Every county sum was checked against the printed statewide total, and OpenElections county rows (2000–2012, including 2004) were compared cell by cell with zero mismatches. The Clerk of the House *Statistics of the Congressional Election* PDFs agree with the 1986, 1988 and 1992 statewide totals.

- **1986, 1992, 1994, 1998, 2000, 2004, 2006, 2010, 2012** are *verified* for all 15 counties, including named write-ins that appear on the canvass. 2000 had no Democratic nominee. Turnout comes from the official canvass (the Governor event for 1994, 1998, 2006 and 2010; new events for 1986, 1992, 2000, 2004 and 2012). The 1986 canvass prints turnout as a fraction, stored here as a percentage.
- **1988** is *verified* with a secondary county source. The Secretary of State canvass scan is too degraded to read every county cell, so county results come from [RightDataUSA](https://www.rightdatausa.com/election_results?y=1988&t=S1&r=N&s=AZ&d=all&WhichMap=vs), a secondary compilation (a saved copy of the page is retained). Each candidate's 15 county cells sum exactly to the official statewide total printed on the canvass, and every legible scan cell agrees. Statewide totals, registration and ballots cast are the official canvass figures; county turnout percentages are computed from them because the printed percentages are illegible. The write-in total is one aggregate row.
- The 2004 canvass was compared with OpenElections (zero mismatches across 45 county cells) and the FEC's statewide totals, which agree.

Official turnout/registration covers all counties and statewide for each Senate election. The 2018 and 2022 contests reuse the existing election-event turnout records. New event records for 2016, 2020 and 2024 retain source percentages and definitions. Repeated imports update the same event/unit records and never duplicate them. The 2020 contest ID is `az-2020-us-senate-special`, its normalized `contest_kind` and API `kind` identify a special election, and its source notes record the term expiring January 2023. Its shared November election event remains `az-2020-general` with event kind `general`. The existing schema supports this convention without a migration. The existing catalog, page heading and selector show the special-election wording using their existing text positions.

Run `.venv/bin/python scripts/normalize_us_senate.py` followed by `.venv/bin/python scripts/import_data.py --office us-senate` for an offline Senate-only refresh of the retained historical data. Add `--year YEAR` to scope an import further. Bootstrap invokes the same normalizer. Existing Governor and Attorney General API payload hashes remain unchanged.
### Governor 1966–1990 additions

Governor elections for **1966, 1970, 1974, 1978, 1982, 1986 and 1990** are **verified** against the official Secretary of State canvass PDFs, supplied by the maintainer and retained as `data/raw/governor-historical/pdfs/canvass<year>ge.pdf` with SHA-256 in each provenance file (the `apps.azsos.gov/election/files/hist/canvass<year>ge.pdf` URL pattern is assumed from the other historical canvasses). `scripts/transcribe_historical_governor.py` rebuilds the data. Each year was first transcribed from saved copies of [RightDataUSA's county pages](https://www.rightdatausa.com/) (also retained) and then checked cell by cell against the canvass; Wikipedia's results tables agree with the statewide totals.

- **Differences found.** Only one: RightDataUSA's 1990 Terry Goddard cell for Gila read 7,693 and the canvass prints 7,893, which closes the 200-vote gap in that source. 1974's canvass itemizes the write-ins (Wonderful Russ Shaw 149, Harold Bates 4) that RightDataUSA reported as one total; the county cells agree.
- **Write-ins.** Named write-ins (1974, 1982, 1990) are shown as named rows with the canvass's county cells. Max Hawkins (Stop Abortion, 1990) is flagged a write-in as printed.
- **Turnout.** Official election-wide registration, ballots cast and turnout (canvass page 1) are imported for every year (1986 shares the figures imported with its Senate contest). County registration and ballots sum to the printed statewide totals. Three printed percentages disagree with their own counts and are kept as published: 1970 Mohave (57.59% printed, 64.20% computed), 1974 Coconino (62.28%, 60.77%) and 1978 Navajo (57.79%, 58.05%).
- **1990 runoff.** The canvass notes a runoff because no candidate won a majority; the runoff is not part of this contest.
- **Counties before 1983.** La Paz County was created in 1983 from northern Yuma County. 1966–1982 results therefore cover 14 counties, and Yuma is the larger pre-1983 county. These contests use the boundary version `county-1966-1982` (`data/geography/az-counties-1966-1982.geojson`), built by `scripts/build_pre1983_county_geography.py` by dissolving today's Yuma and La Paz polygons from the retained Census file; other counties are unchanged and no geometry is hand-drawn.
- **Status ceiling.** The importer supports a `status_ceiling` in provenance (used for secondary sources); none of these years needs one now.
- A Governor import without turnout no longer replaces the turnout of a shared election.

Rebuild with `python scripts/transcribe_historical_governor.py` then `python scripts/normalize_governor_historical.py`, and import with `python scripts/import_data.py --office governor`.

## U.S. House district archive

House elections use independent district contests grouped by election event in
the existing catalog and selector. Six regular elections (2014–2024) contain
all nine districts, with 160 candidate records including 45 named write-ins.
Each regular candidate's actual county records reconcile with an independent
official House Clerk district total, except the explicitly superseded 2014 CD2
pre-recount totals. Final court-certified recount counts are retained.

The 2012 and 2022 boundary plans use retained Census congressional polygons,
native NAD83 geographic coordinates, and plan-qualified district IDs. House
maps, tables and selection panels use district-specific candidates, shares and
winners; no statewide House candidate roster or winner is created. Specials
are separate events; their eight nonparticipating districts are Not contested,
not missing returns or zero-vote contests.

The April 24, 2018 CD8 and September 23, 2025 CD7 special views use civicAPI
race reports directly. Their source panel labels them civicAPI reports, not
official canvass results. Candidate totals are imported as provided; no
separate canvass reconciliation or write-in results are represented. The
retained responses are `data/raw/us-house/civicapi/race-29426.json` and
`race-6240.json`, retrieved October 28, 2026. Their manifest checksums cover
those exact JSON response files. Provider `last_updated` timestamps and
reported percentages appear in the in-app report details. County-level values
and turnout are unavailable in these special-election views; no county
allocations or turnout values are inferred. No House district-turnout records
are currently exposed in these views.

Special elections remain distinct events from regular general elections.
Repeated imports preserve result and turnout identities.

See the [House import report](us-house-import-report.md) for exact source URLs,
retained file/checksum bindings, extraction and recount methods, candidate-level
tables, civicAPI reports, commands, verification results and limitations.
The machine-readable registry is `data/raw/us-house/manifest.json`.
# Historical statewide expansion (October 31, 2026)

Governor results now additionally cover 1994, 1998, 2002, 2006 and 2010; Attorney General results additionally cover 1994, 1998, 2002, 2006 and 2010. The 1994 Governor contest was checked against the official canvass PDF (retained at `data/raw/historical-statewide/canvass1994ge.pdf`); that check found one omitted cell (Charles M. Crawford write-in, Yavapai, 1), which had caused a one-vote county/state difference, and the contest is now verified with no reviewed differences. These additions use retained indexed official canvass excerpts rather than downloaded PDFs. See [historical import report](historical-statewide-import-report.md) for provenance, verification and limitations.
