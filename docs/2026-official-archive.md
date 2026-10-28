# Archived October 27, 2026 source report

This is the prior official-source acquisition log. The current Governor/Attorney General provider policy and displayed data are documented in [2026-import-report.md](2026-import-report.md). No links in this archive were revisited for the October 28 provider update. The instructions below are historical context, not the current refresh workflow.

# 2026 general-election participation and results lifecycle

Verified locally on October 27, 2026. This is a manual snapshot feature, not a live feed. No deployment was performed.

## Official availability

The [Secretary of State's 2026 election page](https://azsos.gov/elections/election-information/2026-election-info) identifies November 3 as the general election, October 7 as the start of early voting, and November 23 as the scheduled statewide canvass. The [election information page](https://azsos.gov/elections/election-information) says initial candidate results are released after 8 p.m. on election night. The general-election release gate is therefore November 3, 2026, 20:00 America/Phoenix (November 4, 03:00 UTC). General-election candidate results were not available at acquisition. The July 21 primary reports linked from the 2026 page and older canvasses embedded in Pima's PDF were excluded.

The current database has no 2026 candidate vote records. All 15 counties appear with neutral coloring and N/A where no verified metric was obtained. After the release gate, an unrefreshed installation says results have not been imported rather than continuing to assert that officials have not released results.

## Obtained metrics

| Metric | County coverage | Published values retained |
| --- | --- | --- |
| Active registered voters | 15/15 | Official statewide 4,374,827; county sum agrees exactly |
| Requests | 1/15 | Maricopa 1,978,119 |
| Early returns received/in hand | 2/15 | Maricopa 660,040; Pima 190,232 |
| Ballots Sent, latest issue | 1/15 | Pima 494,284 |
| Verified and ready for turnover | 1/15 | Pima 8,413 |
| Turned over to Elections | 1/15 | Pima 155,299 |
| Mail-only issuance | 0/15 | N/A |
| Overall accepted ballots | 0/15 | N/A |
| In-person early participation | 0/15 | N/A |

These are general-election participation records, not governor votes. No candidate shares, leaders, winners, participation percentages or derived statewide ballot totals are displayed before results. Registration is the only imported directly published statewide metric. No party-registration breakdown was imported.

### Secretary of State active registration

- [Official PDF](https://apps.azsos.gov/election/VoterReg/2026/State-Voter-Registration-November-2026.pdf), page 1, Active / GE 2026 total column.
- [Official October 20 publication](https://azsos.gov/news/1079) independently confirms the statewide active total.
- Reporting/publication date: October 20, 2026; clock time unavailable.
- Retrieved/reviewed: October 27, 2026, 08:24:45 MST (15:24:45 UTC).
- Method: reviewed transcription of the indexed official PDF into `data/raw/2026/registration-reviewed.csv`, with provenance in `registration-provenance.json`. Direct binary PDF retrieval returned HTTP 403; the retained CSV checksum identifies the reviewed transcription, not the inaccessible original PDF. APR/primary, inactive and federal-only sections were excluded. All 15 county totals sum exactly to the separately printed 4,374,827 statewide figure.

### Maricopa County Elections

- [Official ArcGIS item and publisher metadata](https://www.arcgis.com/sharing/rest/content/items/4f442e13c5514ce7b719844c90a5efe5?f=json), owner `MaricopaElectionsGIS`.
- [Official Early Voting Returns In Hand layer](https://services.arcgis.com/ykpntM6e3tHvzKRJ/arcgis/rest/services/Maricopa_County_Early_Voting_Returns_In_Hand/FeatureServer/0).
- Source last edit: October 27, 2026, 08:03:13.005 MST (15:03:13.005 UTC). This is a layer edit time, not an invented ballot cutoff.
- Retrieved: October 27, 2026, 08:39:46.838 MST (15:39:46.838 UTC).
- Method: public server-side aggregate sums and non-null counts grouped by election labels, with geometry disabled. No voter records were acquired. Publisher, layer metadata, aggregate response and post-query metadata are archived together. A source edit during acquisition causes refresh failure.
- Only `NOV 3 2026 GENERAL ELECTION` is eligible. The 944 labelled records all have Requests/Returns counts. Another 12 layer records lack election labels and counts; they are excluded, never converted to zeros. Both metrics are explicitly marked partial source coverage (944 of 956 layer records). The layer's Returns definition includes all signature-review dispositions; it does not establish accepted ballots.

### Pima County Recorder

- [Official Ballot Processing Reports](https://recorder.pima.gov/BallotProcessingReports).
- Source report: end of day October 26, 2026, date only; no source clock time was supplied.
- Retrieved: October 27, 2026, 08:39:27.335 MST (15:39:27.335 UTC).
- Method: download the PDF through its public form, retain the original bytes, extract exactly the page headed `Early Ballot Status Report`, `2026 GENERAL ELECTION`, and `Status as of end of day`. Other election pages are ignored; ambiguous/missing general-election pages fail validation.
- `Ballots Sent` includes only the latest issued ballot when more than one was sent to a voter. It is not mail-only issuance. `Verified and Ready` excludes ballots already turned over; turnover does not mean tabulation. Neither is substituted for an overall accepted count. Early-voting site ballots issued are not treated as in-person votes cast.
- Outstanding source arithmetic caution: returned 190,232 + not yet returned 304,160 = 494,392, which exceeds Ballots Sent 494,284 by **108**. Source values remain unchanged, with the caution visible in the application. These categories must not be assumed to form a synchronized accounting identity. No official explanation was obtained; the difference remains unresolved.

Other counties have registration but no verified early-activity figures in this import. This is an import coverage limitation, not a claim that those counties publish no records. No polling, forecasts, third-party estimates or historical candidate data were used as current metrics.

## Storage, provenance and refresh

Migration `0002_publication_snapshots` adds publication state, immutable snapshots, current-stream pointers, event-level metric observations and refresh-attempt history. Publication stage, numerical completeness and source verification are separate fields. Metrics attach to the election event and remain separate from candidate vote records.

Raw files are content-addressed under `data/raw/2026/snapshots/`; reviewed manifests under `data/raw/2026/manifests/` retain URLs, SHA-256, definitions, geography, reporting precision and retrieval times. Every import verifies the raw checksum and official source URL. Date-only reports retain date precision. Offset timestamps are normalized to UTC in storage and displayed in America/Phoenix.

From the project root, using the virtual environment:

```sh
# Apply migrations, then replay retained releases offline; never implies a new retrieval.
.venv/bin/python -m alembic -c backend/alembic.ini upgrade head
.venv/bin/python scripts/refresh_2026.py

# Explicitly acquire both currently supported county sources.
.venv/bin/python scripts/refresh_2026.py --fetch all

# Or refresh one source.
.venv/bin/python scripts/refresh_2026.py --fetch maricopa
.venv/bin/python scripts/refresh_2026.py --fetch pima

# Import a reviewed future official aggregate/candidate release.
.venv/bin/python scripts/refresh_2026.py --manifest data/raw/2026/manifests/REVIEWED-RELEASE.json
```

`scripts/bootstrap.py` also migrates and replays retained 2026 inputs. Registration refresh requires a new reviewed transcription/provenance and manifest; there is no automatic registration PDF extractor. Review its actual election period, official total and source date, then use `registration()` and `save_manifest()` in `scripts/refresh_2026.py` to retain the newly reviewed manifest before replaying it. Do not change the old immutable snapshot files.

Repeated identical inputs create no duplicate snapshots, observations or votes; refresh attempts are retained for audit. New cumulative releases replace current figures rather than adding to them. Older reports remain archived without replacing newer ones. Decreases and changed definitions trigger cautions. A failed county fetch exits nonzero, records the failure and leaves the last successful figures visible. Failed refreshes or retrievals older than 24 hours mark data stale. Replaying an old file does not clear failure staleness. This 24-hour rule concerns retrieval age, not a claim that registration changes daily.

API: the normal catalog/detail/county routes expose 2026. `/api/elections/az-2026-governor/activity` exposes metric coverage, sources, report/retrieval dates, source failures and availability. `/api/elections/az-2026-governor/snapshots` exposes retained release payloads for audit. Historical activity responses are null.

## Future candidate releases

The strict reviewed-manifest schema is `backend/app/publication_input.py`. It requires the November 3 general election, an official retained raw source with checksum, a single `results` stream, an explicit `total` or `early_only` scope, the full source candidate/write-in roster, GEOID-keyed vote cells, and explicit roster/unit completeness. Missing cells remain null; true zeros remain zero. Results imports are gated until the official release time. The application does not infer completeness from positive numbers.

One publisher's results snapshot replaces the active 2026 candidate release atomically; county snapshots are not mixed into a purported synchronized statewide release. Shares use the reported contest-vote sum only when the source roster and reporting unit are complete. Unofficial leaders are labelled current reported leaders, and the winner field remains null. Complete county/state candidate disagreements are flagged without adjustments. Certification additionally requires a retained final-canvass source, an independently reviewed statewide/county reference CSV and the existing full candidate/15-county reconciliation. A certified release cannot be replaced by an unofficial release.

No automatic election-night feed parser, automatic refresh scheduler or actual 2026 candidate/canvass release has been added. Future official result formats must be reviewed and converted into this contract. Certification logic was verified with isolated, explicitly synthetic test releases; those fixtures are never imported into the working database.

## Executed verification

- Clean temporary-database migrations, historical imports and retained 2026 imports: backend suite, **13 passed**.
- Actual registration statewide reconciliation: all 15 counties, exact match 4,374,827.
- All 15 GEOIDs, no pre-release candidates/shares/winners, no manufactured statewide returns, real metric coverage and source cautions: API assertions passed.
- Idempotence, zero versus missing, downward correction history, older-release preservation, checksum tampering, failed-refresh staleness, primary rejection, timestamp precision, unofficial denominator/leader rules and certified reconciliation gates: passed in isolated tests.
- Frontend unit checks: **5 passed**. Production TypeScript/Vite build: passed.
- Browser checks: **5 passed**, including historical navigation, 2026 county map/table selection, keyboard use, null-last sorting, neutral colors, source dates/cautions and mobile overflow.
- Ordinary local bootstrap/replay succeeded. Alembic model/migration drift check passed.
- Historical detail/county API SHA-256 fingerprints for 2014, 2018 and 2022 match `data/processed/2026/historical-baseline.json`; historical numerical values and behavior remain unchanged.

Candidate-level 2026 reconciliation is not applicable before publication. This implementation does not claim certified or fully reconciled 2026 candidate results. The Pima arithmetic caution, Maricopa partial layer coverage, original registration PDF download restriction and incomplete county activity coverage remain explicit limitations.
