# Historical results correction plan

The user explicitly requests full county results, restored county maps, actual presidential candidate names, and imported turnout from the official supplied canvasses. The implementation follows that requested behavior.

- Re-audit the affected source pages and fill readable county figures, including write-in supplements.
- Display known official county figures when another entry is unallocated; label partial denominators and infer a winner only when missing votes cannot change it.
- Restore county geography on early statewide pages. Preserve existing district-map handling.
- Present presidential nominee names using printed party totals or the highest statewide elector tally and the same county vector, preserving the raw returns.
- Import official ballots, registration, and percentages with source pages. Registration-only tables remain registration-only.
- Verify all named problem pages, source links, desktop/mobile behavior, and relevant regression suites, then update the local preview and commit.

Completed: see `docs/historical-results-corrections.md` for source corrections, 25 backend tests, 22 frontend tests, two browser regressions and 26 live page checks. Independent review found no remaining blockers after fixes. The existing branch and local preview remain in place for testing.
