# 2018 Arizona governor import report

Completed October 27, 2026. **2018 is now available and verified in the existing application**, with no redesign, schema migration, new infrastructure or changes to 2014/2022 election values.

## Coverage and reconciliation

15 counties, eight candidates, five named write-ins, 120 county/candidate cells and eight independent official statewide result cells. All source-reported zeros are preserved. No county vote was allocated from a statewide residual.

| Candidate | County sum | Official statewide | Difference |
| --- | ---: | ---: | ---: |
| Doug Ducey | 1,330,863 | 1,330,863 | 0 |
| David Garcia | 994,341 | 994,341 | 0 |
| Angel Torres | 50,962 | 50,962 | 0 |
| Patrick Masoya, write-in | 177 | 177 | 0 |
| Christian Komor, write-in | 66 | 66 | 0 |
| Cary D. Dolego, write-in | 13 | 13 | 0 |
| Arthur Ray “RT” Arvizu, write-in | 12 | 12 | 0 |
| James “MarvelMan” Gibson II, write-in | 7 | 7 | 0 |
| **Total** | **2,376,441** | **2,376,441** | **0** |

Combined named write-ins: **275**. No certified candidate discrepancy remains.

## Actual source records

Direct official PDF and State Library downloads remained blocked. The public [VEST/UF Arizona ZIP](https://election.lab.ufl.edu/data-downloads/resultsdata/2018/precinct/az_2018.zip) downloaded successfully and contains **1,489 precincts**. Its three ballot-candidate fields aggregate exactly to all 45 official county reference cells and statewide totals.

The five named write-ins come from an actual [OpenElections county CSV at immutable revision 5675ad1](https://github.com/openelections/openelections-data-az/blob/5675ad1dbf77ce24fdd320127215f81b17e1a866/2018/20181106__az__general__county.csv). All 15 counties and the separately reported statewide record are represented per candidate. Statewide references were obtained from the [official canvass](https://apps.azsos.gov/election/2018/2018_1203_signed_official_statewide_canvass.pdf) and independently corroborated in the [Secretary of State's new-party guide, section IV](https://azsos.gov/sites/default/files/2023-11/new_party_guide_final_202108.pdf).

An indexed-table reconstruction misplaced two Dolego cells, producing 14 rather than 13 votes. Validation caught it. Actual OpenElections records establish **Navajo 0, Pinal 1**, resolving the extraction error. The unreviewed extraction is retained separately for audit; it is not used as input. No change was made by subtracting a residual merely to reach the target.

VEST's aggregate `G18GOVOWRI` contains **3,203** votes, **+2,928** relative to the certified named write-ins. Maricopa's final official county summary corroborates its broader 1,935 aggregate versus 178 votes for named candidates. The VEST aggregate is preserved unchanged and excluded from the candidate dataset/denominator. Its per-county differences remain in `data/processed/2018/vest-comparison.json` and the API reconciliation report. It has not been assigned to individuals or silently adjusted.

All files, URLs, hashes, retrieval limitations and methods are in `data/raw/source-manifest.json` and [data methodology](data-methodology.md#2018-source-acquisition-normalization-and-validation). County vote records in SQLite retain either `vest-2018` (45 cells) or `openelections-2018` (75 cells) provenance; statewide and turnout records retain `canvass-2018`. The API exposes these sources alongside Census geometry.

## Turnout

Official turnout, ballots and eligible registration cover **all 15 counties and statewide**. County totals reconcile to **2,409,910 ballots** and **3,716,263 eligible registrations**. The source reports **64.85%** statewide turnout. The **2,376,441** governor votes are a separate measure. Percentages are preserved as officially reported, not replaced with a derived methodology.

## Implementation and reproduction

- Added a focused `normalize_2018.py` adapter and a checksum-validating `download_2018.py` helper, using existing dependencies.
- Existing normalization/bootstrap now invokes the 2018 adapter. The obsolete availability placeholder is archived so it cannot overwrite verified data.
- `import_data.py --year 2018` updates 2018 Governor and Attorney General contests and retains other years' result records and reconciliation reports.
- Added supplemental input provenance through existing Source/VoteResult relationships and the source-reference endpoint. No schema changes were required.
- Updated methodology text and generic source labels; no CSS, layout or result interaction redesign.

From the root with the existing virtual environment active:

```sh
python scripts/download_2018.py
python scripts/normalize_2018.py
python scripts/import_data.py --year 2018
```

The download helper uses/checks retained files first and only downloads missing sources. Add `--try-official` to retry acquisition or recognize a locally saved original canvass. Normal rebuilding is offline using the retained snapshots. Standard `python scripts/bootstrap.py` also rebuilds all three years from a migrated database.

The existing application then serves `/elections/az-2018-governor` at the Vite address; API metadata/results are under `/api/elections/az-2018-governor`.

## Executed checks

- **8 backend/pipeline tests passed**: clean temporary SQLite migrations/import; all eight candidate sums and official totals; 15 individual county-detail responses; source lineage; county turnout/registration sums; null/zero behavior; repeat-import uniqueness; deterministic normalization and source comparisons. Existing 2014/2022 regression checks pass.
- **4 Chromium browser tests passed**, including the new 2018 workflow: verified catalog card, eight candidates, 15 county paths, 11 Republican/4 Democratic county winners, map and keyboard/table selection, ascending/descending contest sorting, correct Dolego zero/one values, turnout panel, all source links and 390px mobile overflow check. Existing year-navigation, desktop and 2022 workflows pass.
- **3 frontend utility tests passed** for sorting/null handling.
- **Frontend production build passed**.
- **Alembic drift check passed**: no new upgrade operations.
- Retained public input **checksum checks passed**; the OpenElections file was independently fetched at its pinned revision and matched the retained bytes.
- A final ordinary bootstrap/import was executed successfully after the update; the normalized 2018 output remained deterministic.

Before/after SHA256 checks established that the scoped import preserved the 2014/2022 normalized files and API metadata/results/source/reconciliation payloads:

| Year | Normalized JSON SHA256 | API payload SHA256 |
| --- | --- | --- |
| 2014 | `3e252d328de8bf5913d78f66d21df129c5f1c3c373f200ff9668574a3fc41cfc` | `fd7ae728b9a149a9ab98b59c8c14ea283bdef776fa9a6febecc2cb8818b63fe1` |
| 2022 | `b6b1ef2cc6a26d335b07e3cbeb35bf45f471a6afbef4b26fd746fd71638a5f72` | `8eb2e77a351f5ea510558e8befe93239e39a2d72d08615e1e01c59e53491a0e9` |

The current Python TestClient still emits its existing non-failing `httpx` deprecation warning. No dependency version or infrastructure change was required. Original 2018 statewide PDF binaries remain unavailable locally; the documented reviewed authoritative references and retained alternative source records are the reproducible inputs. Verification means exact agreement with published candidate totals under that provenance scope, not an independent recount of ballots.
