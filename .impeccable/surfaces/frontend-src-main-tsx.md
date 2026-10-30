---
version: 1
slug: "frontend-src-main-tsx"
primary_target: "frontend/src/main.tsx"
related_targets: ["frontend/src/pages/Home.tsx","frontend/src/pages/ElectionPage.tsx","frontend/src/pages/HouseElectionPage.tsx","frontend/src/pages/EarlyVotingDashboard.tsx","frontend/src/pages/Methodology.tsx"]
---

# Arizona Election Explorer frontend

Mode: Operate; methodology content: Read. Audience: election enthusiasts and informed members of the public.

## Visual authority

Use DESIGN.md and the implemented components/styles in frontend/src/. Signal uses coordinated light/dark themes, Manrope headings, DM Sans data, party blue/red, nonpartisan lime selection, violet focus and amber warnings.

## Current workflows

Choose an office/year, inspect statewide or district results, select geography through the map or sortable table, and inspect source context. Early voting describes participation and voter registration, never candidate support.

County participation details appear only after selection and retain definitions, coverage and full reporting dates in a native disclosure. The summary timestamp shows retrieval only. Sources & coverage uses the approved concise provider attribution; the existing footer preserves the independent/unofficial disclaimer.

## Preservation requirements

Preserve accurate source data, reporting precision, missing/zero/partial semantics, geographic boundaries, keyboard focus and return, theme continuity, and the existing API/cache/live-update lifecycle. Product facts and constraints remain in PRODUCT.md.
