import { Link } from "react-router-dom";
import type { RefObject } from "react";
import type { Activity, ActivityMetric, Election, Geography } from "../types";
import CountyMap from "../Map";
import ActivityTable from "../ActivityTable";
import { Availability } from "../components";
import { reportTime } from "../activity";
import { number, percent } from "../results";

const returnedMetrics = [
  {
    key: "ballots_received",
    label: "Total Early Votes",
    badge: "ALL",
    color: "other",
  },
  {
    key: "ballots_received__democratic",
    label: "Registered Democrats",
    badge: "DEM",
    color: "dem",
  },
  {
    key: "ballots_received__republican",
    label: "Registered Republican",
    badge: "REP",
    color: "rep",
  },
  {
    key: "ballots_received__other",
    label: "Registered Independents",
    badge: "IND",
    color: "independent",
  },
];

function ParticipationMetrics({
  metrics,
  statewide = false,
}: {
  metrics: ActivityMetric[];
  statewide?: boolean;
}) {
  const displayed = returnedMetrics.flatMap((presentation) => {
    const metric = metrics.find((metric) => metric.key === presentation.key);
    return statewide || metric?.value != null ? [{ presentation, metric }] : [];
  });
  const timestamps = [
    ...new Set(
      displayed.flatMap(({ metric }) =>
        metric?.source_id
          ? [
              `As of: ${reportTime(metric.reported_at, metric.report_precision)} · Retrieved: ${reportTime(metric.retrieved_at)}${metric.stale ? " · Stale" : ""}`,
            ]
          : [],
      ),
    ),
  ];
  const returnedTotal = metrics.find(
    (metric) => metric.key === "ballots_received",
  )?.value;
  function detailDescription(key: string) {
    const party = {
      ballots_received__democratic: "Democratic",
      ballots_received__republican: "Republican",
      ballots_received__other: "Independent",
    }[key];
    if (!party)
      return statewide
        ? "Early ballots returned statewide."
        : "Early ballots returned in this county.";
    return `Early ballots returned by registered ${party} voters. They do not show which candidates voters selected or how they voted.${party === "Independent" ? " The source categorizes this group as ‘Other’." : ""}`;
  }
  return (
    <>
      <div className="activity-details">
        {displayed.map(({ presentation, metric: m }) => {
          const isTotal = presentation.key === "ballots_received";
          const ballotCount = `${number(m?.value)}${m?.completeness === "partial" ? " *" : ""} ballots`;
          const share =
            returnedTotal != null && returnedTotal > 0 && m?.value != null
              ? (m?.value / returnedTotal) * 100
              : null;
          return (
            <div className="activity-metric" key={presentation.key}>
              <div className="candidate-info">
                <span className={`party-chip ${presentation.color}`}>
                  {presentation.badge}
                </span>
                <div>
                  <strong>{presentation.label}</strong>
                </div>
                <div className="vote-value">
                  {isTotal ? (
                    <strong className="activity-count">{ballotCount}</strong>
                  ) : (
                    <>
                      <strong>{percent(share)}</strong>
                      <small className="activity-count">{ballotCount}</small>
                    </>
                  )}
                </div>
              </div>
              <div
                className="vote-track"
                role="img"
                aria-label={`${presentation.label}: ${isTotal ? ballotCount : share == null ? "share unavailable" : `${percent(share)} of total early votes`}`}
              >
                <div
                  className={presentation.color}
                  style={{
                    width: `${Math.min(100, Math.max(0, share ?? 0))}%`,
                  }}
                />
              </div>
              <p className="footnote">{detailDescription(presentation.key)}</p>
            </div>
          );
        })}
      </div>
      {timestamps.length > 0 && (
        <p className="footnote county-timestamps">{timestamps.join(" | ")}</p>
      )}
    </>
  );
}

export default function EarlyVotingDashboard({
  election,
  activity,
  geo,
  selected,
  onSelect,
  detailRef,
  refreshError = null,
}: {
  election: Election;
  activity: Activity;
  geo: Geography;
  selected: string | null;
  onSelect: (id: string) => void;
  detailRef: RefObject<HTMLElement | null>;
  refreshError?: string | null;
}) {
  const county = activity.counties.find((c) => c.geoid === selected);
  const participation = activity.provider_participation;
  const provider = participation
    ? { provider: participation.provider, test_data: false }
    : activity.provider_report;
  const returnedBreakdowns =
    participation?.reports.find((report) => report.category === "returned")
      ?.breakdowns ?? {};
  return (
    <>
      <section className="election-heading">
        <div>
          <p className="eyebrow">ARIZONA · GENERAL ELECTION</p>
          <h3 className="embedded-election-title">
            <span>{election.year}</span> {election.office}
          </h3>
          <div className="election-meta">
            <Availability status="pre_results" />
            <span>November 3, 2026</span>
          </div>
        </div>
      </section>
      <div className="notice" role="status">
        <strong>Early-voting participation reports.</strong>
        <p>
          These figures describe participation in the November general election.
          Party categories indicate voter registration, not candidate choices or
          how anyone voted.
        </p>
      </div>
      <section
        className="panel statewide"
        aria-label="Statewide participation availability"
      >
        <div className="panel-heading">
          <div>
            <p className="eyebrow">GENERAL-ELECTION PARTICIPATION</p>
            <h4>Early-voting activity</h4>
          </div>
        </div>
        <ParticipationMetrics metrics={activity.statewide.metrics} statewide />
        <div className="statewide-foot">
          <span>{activity.statewide_policy}</span>
        </div>
      </section>
      <section className="county-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">PARTICIPATION, COUNTY BY COUNTY</p>
            <h4>County reports</h4>
          </div>
          <span className="muted">Select a county for source definitions</span>
        </div>
        <div className="county-grid">
          <section
            className="panel map-panel"
            aria-label="Returned-ballot party-registration map"
          >
            <div className="panel-heading">
              <h5>Arizona</h5>
              <span className="muted">Returned-ballot party registration</span>
            </div>
            <CountyMap
              geography={geo}
              counties={[]}
              selected={selected}
              onSelect={onSelect}
              mode="registration"
              registrationBreakdowns={returnedBreakdowns}
            />
          </section>
          <section
            className="panel table-panel"
            aria-label="County participation table"
          >
            <div className="panel-heading">
              <h5>Early-voting activity</h5>
              <span className="muted">No candidate results</span>
            </div>
            <ActivityTable
              counties={activity.counties}
              selected={selected}
              onSelect={onSelect}
            />
            <p className="footnote table-note">
              {provider
                ? "N/A means the selected provider has not supplied this metric."
                : "N/A means no verified official figure imported."}{" "}
              * Partial source coverage. Party columns count returned ballots by
              voter registration; they do not indicate candidate choices or how
              anyone voted. Independents corresponds to the source’s “Other”
              category. Select a county for definitions and dates; county rows
              are not a statewide total.
            </p>
          </section>
        </div>
      </section>
      <section
        className="panel county-detail"
        aria-label="Selected county details"
        ref={detailRef}
        tabIndex={-1}
        aria-live="polite"
      >
        {county ? (
          <>
            <div className="panel-heading">
              <div>
                <p className="eyebrow">
                  COUNTY PARTICIPATION · FIPS {county.geoid}
                </p>
                <h4>{county.name} County</h4>
              </div>
              <button
                className="close-button"
                onClick={() => onSelect("")}
                aria-label="Close county details"
              >
                ×
              </button>
            </div>
            <ParticipationMetrics metrics={county.metrics} />
          </>
        ) : (
          <div className="select-prompt">
            <span aria-hidden="true">⌖</span>
            <div>
              <h5>Explore a county’s participation</h5>
              <p>
                Select any county on the map or in the table to see sourced
                aggregate figures, source dates and unavailable metrics.
              </p>
            </div>
          </div>
        )}
      </section>
      <section className="sources">
        <p className="eyebrow">TRANSPARENT BY DESIGN</p>
        <h4>Sources & coverage</h4>
        {(refreshError || activity.stale) && (
          <div className="notice" role="status">
            <strong>
              {refreshError
                ? "Update check failed"
                : activity.failures.length
                  ? "Early-voting refresh delayed"
                  : "Early-voting data may be outdated"}
            </strong>
            <p>
              {refreshError ??
                "Showing the last successfully retrieved figures. A refresh failed or retrieval is more than 12 hours old."}
            </p>
          </div>
        )}
        <p>
          Active registration: {activity.coverage.registered_voters} /{" "}
          {activity.counties.length} counties. Requested:{" "}
          {activity.coverage.ballots_requested} / {activity.counties.length}.
          Returned: {activity.coverage.ballots_received} /{" "}
          {activity.counties.length}. Ballots accepted:{" "}
          {activity.coverage.ballots_accepted} / {activity.counties.length}.
          In-person early participation: {activity.coverage.in_person_early} /{" "}
          {activity.counties.length}. These coverage counts do not imply that
          unavailable values are zero.
        </p>
        {participation?.reports.map((report) => (
          <p key={report.snapshot_id}>
            <strong>
              {report.label} · statewide provider party breakdown:{" "}
            </strong>
            {Object.entries(report.breakdowns["04"] ?? {})
              .map(([party, value]) => `${party}: ${number(value)}`)
              .join(" · ")}
          </p>
        ))}
        <div className="sources-grid">
          {activity.sources.map((s) => {
            const release = activity.releases.find((r) => r.source_id === s.id);
            return (
              <a key={s.id} href={s.url} target="_blank" rel="noreferrer">
                <small>
                  {provider
                    ? "PROVIDER REPORT ↗"
                    : "OFFICIAL AGGREGATE SOURCE ↗"}
                </small>
                <strong>{s.title}</strong>
                <span>{s.notes}</span>
                {release && (
                  <span>
                    Source report:{" "}
                    {reportTime(release.reported_at, release.report_precision)}
                    <br />
                    Last successful retrieval:{" "}
                    {reportTime(release.retrieved_at)}
                    {release.error && (
                      <>
                        <br />
                        Latest refresh failed: {release.error}
                      </>
                    )}
                  </span>
                )}
              </a>
            );
          })}
        </div>
        <Link to="/methodology">Read the data methodology ↗</Link>
      </section>
    </>
  );
}
