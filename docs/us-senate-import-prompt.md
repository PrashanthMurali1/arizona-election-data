# Prompt: Arizona U.S. Senate historical results

Extend the existing Arizona Election Explorer to display every Arizona U.S. Senate election held from 2014 through the present, using the same ingestion, database, API and results interface already used for Governor and Attorney General.

Keep the UI exactly the same. Reuse the existing catalog, office grouping, year selector, county map, results table, county details, sorting, keyboard navigation, source panels and responsive layout. Add the Senate election data through these existing components. Do not redesign the frontend, introduce infrastructure or deploy.

## Establish the election calendar first

Verify the calendar against official Arizona Secretary of State records and U.S. Senate history. The expected elections are:

| Election date | Contest |
| --- | --- |
| November 8, 2016 | Regular U.S. Senate election |
| November 6, 2018 | Regular U.S. Senate election |
| November 3, 2020 | Special U.S. Senate election |
| November 8, 2022 | Regular U.S. Senate election |
| November 5, 2024 | Regular U.S. Senate election |

There was no Arizona U.S. Senate election in 2014 or 2026. There was one Senate contest in 2018; the special election was in 2020. Do not recreate the invalid 2026 Senate entry or add 2026 Senate participation/results. Identify the 2020 special contest correctly in the data and existing textual labels. Do not confuse U.S. Senate with Arizona State Senate, appointments or primary elections.

## Inspect and obtain sources

1. Inspect the existing schema, migrations, import/normalization scripts, Senate scaffold, provenance records, API and verification procedures before editing.
2. Prefer official Arizona Secretary of State statewide canvasses and official county canvasses. Starting sources:
   - 2016: https://apps.azsos.gov/election/2016/General/Official%20Signed%20State%20Canvass.pdf
   - 2018: https://apps.azsos.gov/election/2018/2018_1203_signed_official_statewide_canvass.pdf
   - 2020: https://apps.azsos.gov/election/2020/2020_general_state_canvass.pdf
   - 2022: https://apps.azsos.gov/election/2022/General/canvass/2022dec05_general_election_canvass_web.pdf
   - 2024: https://apps.azsos.gov/election/2024/ge/canvass/20241105_GeneralCanvass_Signed.pdf
   - Senator history: https://www.senate.gov/states/AZ/senators.htm
3. Check for existing local source copies before downloading. If a URL is inaccessible, investigate official alternate links, county records, archives and reliable research datasets. A shell/network failure alone does not establish that all source routes are unavailable.
4. Preserve actual raw snapshots, source URLs, retrieval dates, published report dates, extraction methods and SHA256 checksums. State exactly which retained file each checksum identifies. Never claim to have downloaded a PDF when only a transcription was obtained.

## Import and reconcile

- Import actual county records for all 15 Arizona counties, using their existing GEOIDs.
- Include every officially reported candidate, named write-in and applicable aggregate write-in category. Avoid double-counting broader write-in aggregates alongside their component candidates.
- Reconcile every candidate's county sum with the independently obtained official statewide canvass total. Verify the complete roster and contest total. Validation targets cannot substitute for county records.
- Preserve explicit zero votes separately from missing or unavailable values. Never distribute residuals, infer missing county allocations or silently adjust source figures to force reconciliation. Investigate and document discrepancies.
- Verify the actual county column order, wrapped PDF headers and sparse write-in rows. Check ambiguous extraction against another authoritative record.
- Attach candidate results to the correct Senate contest and turnout/registration to the election event. Reuse existing event-level turnout for 2018 and 2022 without duplicating or altering it. Import turnout for other years only when official figures and definitions are clear; otherwise retain N/A.
- Use stable event, contest and candidate identities. Make normalization and imports reproducible and idempotent. Use versioned migrations only if required by a schema change.
- Preserve existing Governor and Attorney General data and behavior. Mark a Senate contest verified/certified only after all required source and reconciliation checks pass.

## Verify and document

Verify all five elections in the database and API, complete candidate/write-in rosters, all 15 counties per election, county and statewide totals, vote shares, missing-versus-zero behavior and repeat-import behavior. Check that 2014 and 2026 Senate entries are absent.

Verify the existing catalog/year selector, county map, county selection, detail panel, table sorting, keyboard navigation and responsive layout for Senate results. Run appropriate backend/frontend checks and the production build. Compare existing Governor and Attorney General data before and after the import. Report any browser or source-acquisition check that cannot run.

Update the methodology and import report with sources, extraction methods, candidate-level reconciliation tables, turnout coverage, discrepancies and exact local import/refresh commands. Report which elections are available in the application, the number of counties and candidates imported for each, tests passed and any remaining limitations. Do not claim full completion if any required election or validation remains outstanding.

Implement the historical imports autonomously within the existing architecture. Do not stop after creating placeholders or adding an office label.
