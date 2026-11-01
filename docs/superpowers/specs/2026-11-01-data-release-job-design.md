# Versioned data release implementation

This design supersedes the earlier separate Relay data-job proposal. The approved
implementation belongs inside `scripts/deploy_worker.py` at the former manual
data gate, before image builds and candidate tests. Relay continues to own the
same deployment and refresh schedules; no new job or scheduling authority is added.

The contract is `data/data-release.json`; SQLite user_version and an atomic
release-history ledger record completion. A pending fingerprint records interrupted
imports. Backups precede imports; the deployed image runs candidate scripts with
writable candidate data under both deployment and refresh locks. Unknown paths
and schema/runtime-incompatible combined releases fail closed. Imports do not
repeat after successful data application followed by failed image builds/tests.

Version 1 anchors the already-imported c237d04 Governor release. Installation must
verify that baseline and back up before recording its version. Future supported
data releases require only a version bump and merge. The pre-merge checker and
GitHub Actions workflow reject unbumped substantive inputs.

See [automatic deployment](../../automatic-deployment.md#automatic-versioned-data-releases)
for recovery, the emergency acknowledgement override, and operational limitations.
Implementation validation includes mocked orchestration, disposable SQLite failure
and retry tests, the Linux production suite, and catalog/explorer/House browser
checks against the existing development instance. Production installation and
release status are reported separately; source changes do not self-install the
privileged worker or authorize their own trust hash.
