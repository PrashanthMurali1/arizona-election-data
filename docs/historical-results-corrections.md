# Historical results corrections

The previous import omitted readable county tables and turnout tables, and the display required every county entry to be complete before showing percentages or a map winner. The corrections restore the published results and county maps. Presidential pages now show presidential nominees.

Added **2,769 previously missing county cells**, corrected **19 county cells**, and corrected or derived **7 candidate totals** against the retained official documents. Official turnout or registration data is now imported for **28 historical event documents / 423 reporting units**.

## Corrected totals

| Year | Office | Candidate | Previous | Corrected |
|---|---|---|---:|---:|
| 1918 | governor | Geo. D. Smith | 442 | 444 |
| 1920 | governor | Thos. E. Campbell | Unavailable | 37,060 |
| 1920 | attorney-general | Wiley E. Jones | 28114 | 28,814 |
| 1920 | attorney-general | W. H. Galbraith | 34533 | 34,333 |
| 1924 | secretary-of-state | James H. Kerby | 42735 | 42,635 |
| 1930 | attorney-general | K. Berry Peterson | 61913 | 61,813 |
| 1964 | us-house | William E. Kimble | 60732 | 60,782 |

1920 Campbell?s total is the sum of all 14 legible official county figures, explicitly marked as derived; the obscured printed statewide cell remains documented. Source arithmetic discrepancies remain explicit.

## Display and import changes

- All early statewide election pages now load the retained county geometry, including the presidential pages.
- A statewide-only write-in no longer suppresses all known county votes. Partial county percentages use reported tallies and are labeled. County winners are shown only when the missing candidates? entire statewide vote bound cannot reverse the county lead; otherwise the result remains undecided.
- All 1944 write-in county allocations were transcribed from the supplemental table. The 1932 and 1922 statewide-only write-ins remain explicitly unallocated by county.
- Presidential names are sourced in `presidential-tickets.json`. Printed party totals are used directly. For individual elector tables, the highest statewide elector tally and that same county vector represent the ticket. Elector votes are never added together. The raw returns remain intact. Unassignable elector write-ins are retained in the source, without inventing presidential identities.
- Turnout records carry actual registration, ballots cast, printed percentages, source IDs and PDF pages. Registration-only years display registration and do not invent a ballot count or rate. The supplied 1932 source has no turnout table; the 1938 registration table is explicitly unofficial and was not relabeled as official turnout.
- Additional source discrepancies are retained, including 1946 Cochise?s printed turnout percentage and 1964 registration totals.

## Verification

- 25 backend historical/cache tests passed, including partial county results, official turnout import, presidential aggregation and source routes.
- Frontend production build passed; 22 frontend unit tests and 2 browser regression tests passed.
- 26 live desktop/mobile page checks passed with populated county maps and numeric county shares, including every named problem page. Screenshots were visually inspected.
- All 13 presidential elections now return 14 county datasets with numeric totals; ten early election turnout APIs were checked against the imported records.
- Independent code review findings were fixed: missing presidential IDs return 404, presidential endpoint presentation is consistent, multi-seat House contests suppress a single-winner inference, and turnout updates do not misattribute retained fields.

The updated preview is running at http://127.0.0.1:5173/ on the existing feature branch. No public deployment or merge was requested.
