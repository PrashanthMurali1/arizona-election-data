# 1911 result corrections and Turnout wording

All product wording now uses Turnout, retaining the registered-voter denominator for calculated rates. The phrase previously used for calculated rates was removed from the application and related documentation.

The supplied 1911 returns have a clipped statewide column. Complete county vectors now supply derived statewide totals instead of leaving them null. The raw records mark these totals as sum_of_official_counties and preserve the source limitation.

| Office | Candidate | Statewide votes |
|---|---|---:|
| us-senate | H. F. Ashurst | 10872 |
| us-senate | M. A. Smith | 10598 |
| us-senate | R. H. Cameron | 9640 |
| us-senate | H. A. Smith | 9228 |
| us-senate | E. Johnson | 1234 |
| us-senate | E. R. Simonton | 1221 |
| us-house | Carl Hayden | 11556 |
| us-house | J. S. Williams | 8485 |
| us-house | John Halberg | 1252 |
| us-house | E. W. Chafin | 88 |
| governor | Geo. W. P. Hunt | 11123 |
| governor | E. W. Wells | 9166 |
| governor | P. W. Gallentine | 1247 |
| governor | T. W. Otis | 79 |
| secretary-of-state | Sidney P. Osborn | 10476 |
| secretary-of-state | J. F. Cleveland | 9282 |
| secretary-of-state | G. H. Newsholme | 1294 |
| secretary-of-state | Roy Sibley | 78 |
| attorney-general | G. P. Bullard | 10650 |
| attorney-general | G. D. Christy | 9000 |
| attorney-general | J. N. Morrison | 1373 |
| attorney-general | Ostora Gibson | 90 |

House county returns were omitted previously and are now filled. Secretary of State county returns are filled for every legible cell. Governor Otis Cochise is 13 (previously misread as 3); Christy attorney-general Cochise is 1,381 (previously 1,581), reconciling his printed statewide 9,000. Morrison county sum 1,372 versus printed 1,373 remains recorded as a source discrepancy.

Three Secretary of State Cochise cells have damaged final digits; their clipped statewide columns cannot resolve them. These remain null rather than guessed. The state library and Library of Congress copies were sought but their relevant item/download endpoints returned HTTP 403 or unavailable responses. The supplied three-page source contains no voter registration or election-wide ballots-cast table, so no 1911 turnout percentage is invented. The two-seat Senate advisory vote remains a multiple-member contest without a single-winner inference.

Verification: 29 backend historical/cache tests, 22 frontend unit tests, 3 browser regression tests, and production build passed. Ten live desktop/mobile checks verified 1911 totals and Turnout labels. Preview remains http://127.0.0.1:5173/.

## Mason compilation supplement (November 3, 2026)

The earlier null-cell limitation above is superseded. Retained `1911-1960 compilation.pdf`, Mason (ASU, 1961), PDF pp74 and76 (printed pp67 and69), supplies Secretary of State totals 10,476 / 9,282 / 1,294 / 78. Cochise Osborn is 1,938 and Cleveland 1,433. Mason groups minor parties as Other 263; subtracting the original canvass Sibley 14 yields Newsholme 249, explicitly marked as derived. All candidate statewide totals and all 14 county vectors are now populated. The original legible Cleveland county figures sum to 9,283 after filling Cochise, one above Mason's statewide 9,282; the discrepancy is retained. Morrison's prior one-vote discrepancy is also retained.

Mason PDF p17 identifies R. H. Cameron as Republican. PDF pp19,30,46,61,76 explicitly state Registration Not Available for 1911. Their zero percentages accompany a missing denominator and are not real 0% turnout. Total Vote is per-office candidate votes (including two votes per voter in the Senate table), not election-wide ballots cast. The UI now explains this source limitation directly. No later-year registration denominator is substituted.

See `docs/mason-compilation-corrections.md` and `data/processed/historical-canvasses/mason-summary-audit.json` for the full 1911-1960 gap audit.
