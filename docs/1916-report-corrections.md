# 1916 corrections from the 1917 Secretary of State report

The newly supplied `1917Report.pdf` is retained verbatim alongside the earlier scan. It is dated January 2, 1917. Its candidate-return tables cover November 7, 1916, on PDF pages 24-29 (printed pages 26-31); the certification on the last page is dated December 6, 1916.

All six existing requested-office contests were re-transcribed from PDF pages 24-27. Their 28 candidate/elector entries now have complete totals and all 14 county cells. All 392 county cells reconcile exactly to their separately printed totals. This resolves all 13 previously null totals and the prior AG county discrepancies. No legislative return tables are supplied.

The report is now the primary source for these contests. The degraded `1916.pdf` remains a supplementary source; its unreadability notes no longer apply to the corrected records. Individual elector tallies remain separate, with no inferred presidential ticket vote or winner. The governor figures are the printed canvass, not an inference about subsequent adjudication.

## Changes to names or printed totals

| Office | Previous label / total | Corrected label / total |
|---|---|---|
| president | [Illegible presidential elector, printed row 1]: unavailable | Lamar Cobb: 33,170 |
| president | [Illegible presidential elector, printed row 2]: unavailable | Harry E. Pickett: 33,150 |
| president | [Illegible presidential elector, printed row 3]: unavailable | Homer R. Wood: 33,157 |
| president | [Illegible presidential elector, printed row 4]: unavailable | W. W. Cook: 20,522 |
| president | [Illegible presidential elector, printed row 5]: unavailable | John C. Greenway: 20,520 |
| president | [Illegible presidential elector, printed row 6]: unavailable | J. L. Hubbell: 20,524 |
| president | [Illegible presidential elector, printed row 7]: unavailable | Beverly Blunt: 3,174 |
| president | [Illegible presidential elector, printed row 8]: unavailable | James E. Pawley: 3,172 |
| president | [Illegible presidential elector, printed row 9]: unavailable | T. C. Pruett: 3,172 |
| president | [Illegible presidential elector, printed row 10]: unavailable | Eugene W. Chafin: 1,153 |
| president | [Illegible presidential elector, printed row 11]: unavailable | O. Gibson: 1,145 |
| president | [Illegible presidential elector, printed row 12]: unavailable | J. Stanley Howard: 1,148 |
| us-house | Carl Hayden: 34577 | Carl Hayden: 34,377 |
| us-house | J. R. Barnette: 3080 | J. R. Barnette: 3,060 |
| governor | Thos. E. Campbell: 27976 | Thomas E. Campbell: 27,976 |
| governor | Peter T. Robertson: 1875 | Peter T. Robertson: 1,975 |
| governor | R. E. Dunlap: 596 | R. E. Dunlap: 396 |
| secretary-of-state | Sidney P. Osborn: unavailable | Sidney P. Osborn: 33,075 |
| secretary-of-state | Joe V. Prochaska: 18152 | Joe V. Prochaska: 18,182 |
| attorney-general | Frederick C. Struckmeyer: 21297 | John L. Gust: 21,297 |

361 county cells were corrected or filled from the new report. All other supplied election years remain unchanged.

## Verification

- 21 historical backend tests passed, including replacement of uncertain imported rows without duplicate candidates and preservation of elector semantics.
- All six corrected contests verify against their 14-county sums; 28 candidate entries and 392 county cells are populated.
- Source digest and PDF page references checked. The original report is served through the checked local source endpoint.
- Live API checks passed for all six contests; the source endpoint returns the exact retained report bytes.
- Eight live desktop/mobile page checks passed without browser errors or overflow. All other event vote cells match the pre-correction SQLite backup.
