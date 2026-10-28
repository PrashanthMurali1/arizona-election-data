# Automatic 2026 early-voting refresh

**Current production workflow:** the Docker Compose cron worker now owns the six-hour schedule. The macOS LaunchAgent was disabled after timed cron checks passed. Use the [production hosting guide](production-hosting.md) for production refreshes, status and logs; do not reinstall the LaunchAgent while the container scheduler is active. The original host database remains retained separately.

The legacy local workflow below uses the application's Python virtual environment and SQLite database in this checkout. `scripts/manage_early_vote_schedule.py` manages its user LaunchAgent rather than a web-worker or browser timer. Activation details below describe the earlier setup, before the production cutover.

## Legacy schedule and activation

From the repository root:

```sh
# Generate the local configuration without activating it.
.venv/bin/python scripts/manage_early_vote_schedule.py prepare

# Install and start the persistent user job (also refreshes immediately).
.venv/bin/python scripts/manage_early_vote_schedule.py install

# Inspect activation, next calendar slot, last job status and log paths.
.venv/bin/python scripts/manage_early_vote_schedule.py status

# Disable and remove the user's schedule; retained data/logs remain.
.venv/bin/python scripts/manage_early_vote_schedule.py remove

# Change interval by reinstalling; positive divisors of 24 are supported.
.venv/bin/python scripts/manage_early_vote_schedule.py install --interval-hours 6
```

Default calendar slots are **00:00, 06:00, 12:00 and 18:00 in the Mac's system timezone**, currently **Asia/Kolkata (IST, UTC+05:30)**. The source dates are independent; the application continues displaying reporting/retrieval timestamps in America/Phoenix. `status` calculates the next calendar slot when loaded, not a guarantee that a sleeping/offline host will execute at that instant.

LaunchAgent label: `org.arizona-election-explorer.early-voting`. Installed file: `~/Library/LaunchAgents/org.arizona-election-explorer.early-voting.plist`. It survives application restarts and loads at user login. macOS coalesces missed calendar slots during sleep into one run upon waking; a powered-off or logged-out Mac cannot fetch data. RunAtLoad performs a refresh at the next login/load. This local schedule does not provide an always-on hosting service. Inspect status/logs after installation: a loaded agent alone does not prove its refresh succeeded, and macOS privacy permissions may restrict access to a checkout in Documents.

**Activated October 28, 2026.** The agent is installed and loaded, with the next calendar slot at **18:00 IST on October 28**. Its initial run was blocked by macOS Documents-folder access during Python startup. After the user granted access, the agent was reloaded and completed a real scheduled-process refresh successfully at `2026-10-28T08:37:21.976899+00:00` (14:07:21 IST), exit 0. Both feeds reused their existing snapshot records and advanced retrieval times. The acquisition index is `data/raw/2026/providers/early-vote-acquisition-20261028T083721879082Z.json`. Two foreground manual refreshes also succeeded. `last_job` in the status command refers to the last importer invocation, including manual runs; inspect the separate launchd `last_exit_code` and scheduler logs to assess unattended execution. If Documents access is later revoked or Python is upgraded, restore permission for that interpreter and reinstall the agent to retry; the application does not change OS privacy controls.

The installer embeds absolute runtime, script, working-directory and database paths in a private (0600) plist. Its default database is `backend/local/elections.db`; a supplied `DATABASE_URL` is captured at installation, with relative SQLite paths resolved against the checkout. Reinstall with the correct environment after changing database configuration or moving the checkout. Keep credentials in the local environment/private plist, outside source control. The generated workspace copy under `backend/local/launchd/` is ignored.

## Manual refresh and logs

The scheduled command is also available manually:

```sh
"/Users/prashanth/Documents/LLM Projects/election-data/.venv/bin/python" \
  "/Users/prashanth/Documents/LLM Projects/election-data/scripts/refresh_2026.py" --early-voting
```

The importer resolves local files against the repository root. Set `DATABASE_URL` explicitly when using a non-default database, matching the scheduler environment.

```sh
tail -n 50 backend/local/logs/early-voting-refresh.log
tail -n 50 backend/local/logs/early-voting-scheduler.stdout.log
tail -n 50 backend/local/logs/early-voting-scheduler.stderr.log
cat backend/local/early-voting-refresh-status.json
```

The main log rotates at 1 MiB with three backups and records starts, success/failure and overlapping-run skips. Scheduler stdout contains per-feed import outcomes/errors; stderr captures launch/runtime exceptions. The private status JSON includes UTC start/finish times and the last wholly successful job. Per-source attempts and successful retrieval times remain in the database. Scheduler stdout/stderr are local diagnostic files and can be cleared or archived when the job is stopped.

## Refresh and display behavior

Only these civicAPI endpoints are fetched, with 5-second connection and 25-second read timeouts and no redirects:

- `https://civicapi.org/api/v2/early-vote/AZ/requested`
- `https://civicapi.org/api/v2/early-vote/AZ/returned`
- `https://civicapi.org/api/v2/early-vote/AZ/inperson`

The optional in-person endpoint currently returns 404, which is retained as unavailable rather than a job failure. A missing Requested/Returned feed, network failure, invalid/empty payload or import error records a failed attempt and preserves that feed's previous data. Other successful feeds may still advance. Explicit zero is valid; missing counts stay missing. Transactions, existing snapshot identities and report-date ordering prevent partial writes, duplicates and rollback to older reports. Raw responses, checksums, URLs and timestamps continue through the existing retention pipeline. A shared `flock` lock skips overlapping scheduled/manual live refreshes without overwriting the active job's status.

The shared page loads current data on entry, then opens one server-sent events connection to `/api/elections/az-2026-early-voting/updates`. The API observes the existing local job-status file once per second while a connection is open, without querying civicAPI. A finished marker is written after import transactions have committed; only then does the API check the database revision and emit a changed revision. Idle connections do not repeatedly query the database. Keep-alive comments every 15 seconds maintain the connection without triggering data requests. This uses the existing shared filesystem and database across the importer/API processes, with no external service or new scheduler.

The initial SSE event and every reconnect announce the current database revision, covering commits missed while disconnected. A revision includes current release IDs, successful retrieval timestamps and failure attempts, so unchanged counts can still update source dates/status. The browser fetches the existing detail/counties/activity endpoints once per unseen revision. Duplicate notifications are ignored, concurrent notifications coalesce without overlapping fetch groups, and tab resumption reconnects to catch suspended updates. Leaving the page closes the stream and aborts pending requests. Native EventSource retries broken connections; failed requests keep the last loaded view and can retry on reconnection/resumption. There is no recurring one-minute browser polling and no browser-triggered civicAPI import.

Successful updates retain county selection, sorting and layout. Sources & coverage keeps attribution and separate reporting/retrieval timestamps; existing notices show connection failures, source failures or stale retrievals when data is loaded. No Source snapshots section is restored. No candidate feeds, other providers, government sources, election-data reconciliation or independent verification are involved. Offline manifest replay does not write the scheduled-job audit; a page opened or reconnected after replay still reads the current database revision.
