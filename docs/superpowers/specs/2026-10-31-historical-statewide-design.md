# Historical statewide elections

Extend the general-election archive with Governor and Attorney General results for 1994, 1998, 2002, 2006 and 2010. Preserve existing contests, candidate identities, and event-wide turnout semantics.

Approach: extend the existing reviewed CSV transcription pipeline using official Arizona canvasses. Secondary datasets were considered but are insufficient as the authoritative reference. The user approved the official-canvass approach and native execution.

Retain every reported candidate and write-in, fifteen county cells and the independently published statewide total. Retain acquisition provenance and checksums. Missing values remain unavailable rather than becoming zero. Do not mark a contest verified unless its roster and county values reconcile. Downloaded PDF binaries are preferred; clearly label transcriptions when download access is denied.

No schema migration or new election-specific UI is expected. Add official turnout only when reviewed from the source; Attorney General must not overwrite event-wide turnout. No deployment is requested.
