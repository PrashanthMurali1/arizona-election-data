# Extending the archive

The database and frontend do not reserve columns or components for particular candidates. New sources still require a trustworthy adapter and explicit verification; the current importer is a governor-by-county adapter, not a universal PDF extractor.

## Add another gubernatorial year

1. Locate the final certified statewide canvass and investigate amendments/recounts affecting **that contest**. Record its official URL, reporting date and relevant pages. Do not assume an election-night export equals certification.
2. Acquire the original document or create a reviewed transcription. Follow the existing `data/raw/{year}-governor-transcription.csv` format: source party, full source name, write-in flag, fifteen five-character GEOID columns, and the independently published `official_statewide` total. Include every candidate/category, not just the major parties. Blank means unavailable, while `0` means a genuine zero.
3. Add officially reported election-wide turnout to `{year}-turnout-transcription.csv` when available. Preserve ballots, eligible registration, reported percentage and source definition. If unavailable, omit the record; never substitute contest votes for ballots.
4. Add the URL/date to `scripts/normalize.py` (`URLS`) and the date mapping in `scripts/normalize_transcription.py`. Add provenance, acquisition method and snapshot checksums to `data/raw/source-manifest.json`. The initial normalizer supplies default governor metadata; dates and source layout require explicit review.
5. Run `python scripts/normalize_transcription.py` and inspect the normalized JSON. For 2018, the existing normalizer delegates to `normalize_2018.py`; its previous metadata-only placeholder is archived under `data/raw/2018/prior-availability.json` and is no longer an active input.
6. Run `python scripts/import_data.py`. It reads reference totals and candidate roster independently from the raw CSV. Inspect every difference, missing county/candidate and availability status in `data/processed/reconciliation.json`. Never adjust values simply to make the check pass. Nonempty incomplete data results in a nonzero exit, while preserving its explicit incomplete status.
7. Verify the catalog, same-office year selector, all candidates, 15 county details, turnout, provenance and browser interaction. Update coverage documentation and static methodology copy to match the newly verified coverage.

No frontend election card needs to be added: the homepage and year selector derive their records from the API. No candidate component needs to be changed when the number of participants changes.

## Add another statewide office

No database migration is required for ordinary single-winner statewide offices. Create an `Office`, reuse the same `ElectionEvent`, add a `Contest` for jurisdiction `04` and the selected county boundary version, create participations, and supply candidate/geo result records. Store authoritative statewide cells separately from county cells and share election-event turnout where appropriate.

The supplied importer currently builds `az-{year}-governor` contest IDs and reads governor-named source CSVs. Extend this adapter before importing another office:

- Introduce normalized `office_id`, `office_name`, `contest_id`, `event_id`, `jurisdiction_id` and reference snapshot path fields.
- Replace the governor-specific default office/contest/source identifiers in `scripts/import_data.py` with those fields. Preserve transaction boundaries, uniqueness, per-contest vote replacement and reference reconciliation.
- Let `reconcile` read the new official-reference CSV instead of constructing the governor filename. Define the required unit/candidate roster from that source's contest scope.
- Associate source references with the new contest and add a reviewed parser/normalizer for its actual table structure.
- If processing several contests in one event, upsert event-wide turnout by `(event_id, unit_id)` rather than repeatedly replacing it from different source definitions. Reuse `Candidate` IDs for the same person across contests when identity is established; party affiliation belongs to participation.

The catalog automatically groups by the returned office identity; `/elections/:id` uses the same candidate summary/map/table/detail components, and the year selector stays within the selected office. The `Governor` title is metadata, not a hardcoded results-page heading. Single-candidate, many-candidate and write-in records use the same result shape. Multi-seat contests/ranked-choice elections would need explicit voting-rule semantics and winner logic; the MVP should not be reused for those without that work.

## Add an election with district boundaries

1. Download official Census or appropriate official redistricting geometry for the exact boundary vintage applicable to the contest. Retain acquisition provenance and stable identifiers.
2. Add a `BoundaryVersion` and geographic units with a district kind. Store geometry with the `(unit_id, boundary_id)` pair; never overwrite old vintages in place.
3. Add a contest whose jurisdiction/scope and selected boundary version match the source. Decide whether reporting is by whole districts, county portions, or precincts. Do not invent county allocations from district totals.
4. Extend the adapter's required reporting-unit roster and reconciliation scope. A district race may cover only part of Arizona; all-15-counties validation is inappropriate for that contest. Preserve separately reported official jurisdiction totals.
5. Generalize the current `/counties` routes into reporting-unit routes (keeping county routes for compatibility) and replace the county-kind filter with the contest's reporting level. Label county-specific table/panel copy according to the reporting unit. The `VoteResult` and geometry tables already accept generic unit IDs, so this does not require candidate-specific schema changes.
6. Pass the appropriate geometry feature collection to the existing map renderer. It already joins by `properties.geoid`. Verify projection, accessible names, table alternatives and winner semantics for the new reporting geography.

Separate election results from boundaries: an election year is not a reliable proxy for the correct district vintage.

## Add candidates, affiliations or result categories

Candidate totals are records, not columns. Add a `Candidate`, a source-preserved `Party` and a `Participation`, then a `VoteResult` for each required unit and the official jurisdiction total. The initial normalizer produces year-scoped candidate IDs; a future identity resolver can deliberately reuse known person IDs rather than inferring identity from a name alone.

Preserve named write-ins as named participants. For a reported unattributed write-in category, use the published category name and `category="aggregate_write_in"`, without assigning votes to a person. The normalizer recognizes `Unattributed write-ins`; use an explicit category field if a new source uses another label. Add an unknown affiliation code to the importer's source-name mapping instead of guessing a political party. The API and frontend accept arbitrary party codes and render non-Democratic/Republican winners neutrally.

Any new election should carry its own source-reference candidate roster. A sum of only the two leading candidates is not proof of a complete contest. Test nulls, zeros, a discrepancy, a missing candidate, a tie and repeated imports when changing reconciliation or result semantics.
