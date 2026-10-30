# Candidate-test failure: 95aedc0

Investigated October 31, 2026 (Asia/Kolkata).

## Cause and impact

Commit `95aedc0af3a2bc6501169880a6cf72b130248582` failed frontend candidate
checks before production activation. The deployment engine retained the previous
working images and suppressed repeat attempts at the same failed commit. There
was no pending activation/migration journal and no rollback was required.

The theme/source-layout redesign keeps provider attribution in the early-voting
**Sources & coverage** region, and places **Sources & methodology** in the global
footer. The catalog regression test still required a methodology link inside
`.sources` within the Live Elections tab panel. That locator no longer exists.

Reproduction against the unchanged failed frontend image and a candidate backend
using a copied SQLite backup produced **3 failures and 26 passes**. All failures
were the same assertion at the three viewport widths: 1440, 390 and 320 pixels.
The UI rendered correctly; this was an outdated test contract rather than a
browser crash, provider outage, missing election data or Docker sleep issue.

## Why the diagnostic list looked larger

The structural parser previously collected every reviewed test location appearing
in command output, including successful progress lines, then assigned one global
assertion operator to every entry. Its twelve-entry limit explains the list of
catalog locations followed by `explorer.spec.ts:5`; those were not twelve
independent failures. The location `catalog.spec.ts:111` identified the test
declaration; the failing assertion was at line 287 in that release.

## Fixes

- Catalog tests verify the civicAPI attribution link in the sources region and
  the visible methodology link in the global footer, at every tested width.
- Structural diagnostics read only numbered Playwright failure sections and
  explicit pytest FAILED summaries. Each failure has its own operator/category;
  the assertion stack location is preferred over the test declaration line.
- Redaction, reviewed-suite allowlisting, bounded records and best-effort logging
  behavior remain enforced.
- The matching authoritative parser source is updated in the Relay repository
  on `fix/deployment-diagnostics-parsing`. The election changes are on
  `fix/catalog-deployment-diagnostics`.

## Validation

- **39 browser tests passed** against the original candidate image, including the
  29 deployment-reviewed checks plus source-layout and theme regressions.
- **60 election tests passed** for deployment behavior and diagnostics parsing.
- **17 Relay parser/log-store tests passed** against disposable databases.
- Candidate containers/network and the copied database were removed afterward.
  No test used production data mounts, credentials or forced refresh jobs.

## Deployment next step

Changes remain local and uncommitted. Merge the corrected catalog test into
`main`; Relay will consider that new commit automatically. Retrying the unchanged
failed commit would execute its old assertion again and is not a fix. There is
no need to clear its failed-commit record or weaken the candidate gate.

Parser source changes do not automatically update the installed host worker.
Install the reviewed parser companion through the existing locked update
procedure after review, keeping the election and Relay copies synchronized.
Existing stored diagnostics are historical and are not rewritten by this fix.
