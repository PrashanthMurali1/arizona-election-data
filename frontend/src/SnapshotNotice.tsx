import type { Activity } from "./types";
import { reportTime } from "./activity";
export default function SnapshotNotice({ activity }: { activity: Activity }) {
  return (
    <section
      className="panel snapshot-notice"
      aria-label="Reporting dates and source status"
    >
      <div className="panel-heading">
        <h3>Source snapshots</h3>
        <span className="muted">Manual refresh · America/Phoenix (MST)</span>
      </div>
      <div className="snapshot-body">
        <p className="footnote">
          These are retained source releases, not a live feed. Each source has
          its own reporting date; retrieval time is separate. A date-only source
          has no invented clock time.
        </p>
        {activity.provider_participation && (
          <p className="footnote">
            Early-voting participation reports from {activity.provider_participation.provider}.
            {" "}Requested and returned ballots retain their separate source dates.
          </p>
        )}
        {activity.provider_report && (
          <p className="footnote">
            {activity.provider_report.provider} report · {activity.provider_report.race_status.replaceAll("_", " ")}
            {" · "}Provider reporting: {activity.provider_report.percent_reporting == null ? "N/A" : `${activity.provider_report.percent_reporting}%`}
            {activity.provider_report.test_data ? " (test data; excluded from live results)" : ""}.
          </p>
        )}
        {activity.stale && (
          <div className="notice" role="status">
            <strong>Stale source data</strong>
            <p>
              A source refresh failed or the last retrieval is more than 24
              hours old. The last successful figures remain visible.
            </p>
          </div>
        )}
        {activity.releases.map((r) => (
          <div className="snapshot-row" key={r.id}>
            <strong>
              {activity.sources.find((s) => s.id === r.source_id)?.title ??
                r.stream}
            </strong>
            <p>
              Source report / last edit:{" "}
              {reportTime(r.reported_at, r.report_precision)}
              <br />
              Retrieved: {reportTime(r.retrieved_at)}
              {r.stale ? " · Stale" : ""}
            </p>
            {r.error && (
              <p className="footnote" role="status">
                Refresh failed: {r.error}
              </p>
            )}
            {r.kind === "results" && (
              <p className="footnote">
                {r.stage === "unofficial" ? "Unofficial" : "Certified"} ·{" "}
                {r.vote_scope === "early_only"
                  ? "Early-ballot-only candidate results"
                  : "Total reported candidate results; may include multiple voting methods"}
                . Release: {r.release_id}
              </p>
            )}
          </div>
        ))}
        {activity.failures
          .filter((f) => !activity.releases.some((r) => r.stream === f.stream))
          .map((f) => (
            <p className="footnote" role="status" key={f.stream}>
              {f.stream}: refresh failed at {reportTime(f.attempted_at)}. No
              successful snapshot is available. {f.error}
            </p>
          ))}
        {activity.warnings.length > 0 && (
          <details className="source-cautions">
            <summary>
              Source checks & cautions ({activity.warnings.length})
            </summary>
            {activity.warnings.map((w, i) => (
              <p key={i} className="footnote">
                {w}
              </p>
            ))}
          </details>
        )}
      </div>
    </section>
  );
}
