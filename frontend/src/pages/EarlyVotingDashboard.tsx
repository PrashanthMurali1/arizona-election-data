import type { RefObject } from "react";
import type { Activity, ActivityMetric, Election, Geography } from "../types";
import CountyMap from "../Map";
import ActivityTable from "../ActivityTable";
import { Availability } from "../components";
import { reportTime } from "../activity";
import { number, percent } from "../results";
import Icon from "../Icon";
import EarlyVotingSources from "../EarlyVotingSources";

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
    label: "Registered Republicans",
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
  const timestamps = statewide
    ? [
        ...new Set(
          displayed.flatMap(({ metric }) =>
            metric?.source_id
              ? [`Retrieved: ${reportTime(metric.retrieved_at)}`]
              : [],
          ),
        ),
      ]
    : [];
  const returnedTotal = metrics.find(
    (metric) => metric.key === "ballots_received",
  )?.value;
  return (
    <>
      <div
        className={`activity-details ${statewide ? "statewide-participation" : "county-participation"}`}
      >
        {displayed.map(({ presentation, metric: m }) => {
          const isTotal = presentation.key === "ballots_received";
          const ballotCount = `${number(m?.value)}${m?.completeness === "partial" ? " *" : ""} ballots`;
          const share =
            returnedTotal != null && returnedTotal > 0 && m?.value != null
              ? (m?.value / returnedTotal) * 100
              : null;
          return (
            <div
              className={`activity-metric ${isTotal ? "returned-total" : "registration-stat"} ${presentation.color}`}
              key={presentation.key}
            >
              <div className="candidate-info">
                <span className={`party-chip ${presentation.color}`}>
                  {presentation.badge}
                </span>
                <div>
                  <strong>{presentation.label}</strong>
                </div>
                <div className="vote-value">
                  {isTotal ? (
                    <strong className="activity-count">
                      {number(m?.value)}
                      {m?.completeness === "partial" ? " *" : ""}
                      <span className="count-unit"> ballots</span>
                    </strong>
                  ) : (
                    <>
                      <strong>{percent(share)}</strong>
                      <small className="activity-count">{ballotCount}</small>
                    </>
                  )}
                </div>
              </div>
              {(!statewide || !isTotal) && (
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
              )}
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
  const returnedReport = participation?.reports.find(
    (report) => report.category === "returned",
  );
  const returnedBreakdowns = returnedReport?.breakdowns ?? {};
  const returnedSource = activity.sources.find(
    (source) => source.id === returnedReport?.source_id,
  );
  return (
    <>
      <section className="election-heading page-heading">
        <div>
          <h3 className="embedded-election-title">
            <span>{election.year}</span> {election.office}
          </h3>
          <div className="election-meta">
            <Availability status="pre_results" label="Participation only" />
            <span>November 3, 2026</span>
          </div>
        </div>
      </section>
      <div className="notice info participation-notice" role="status">
        <strong>Early-voting participation reports.</strong>
        <p>
          These figures describe participation in the November general election.
          Party categories indicate voter registration, not candidate choices or
          how anyone voted.
        </p>
      </div>
      <div id="participation-freshness">
        {(refreshError || activity.stale) && (
          <div
            className="notice freshness-notice participation-notice"
            role="status"
          >
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
      </div>
      <section
        className="statewide participation-overview"
        aria-label="Statewide participation availability"
      >
        <p className="footnote participation-source">
          Source:{" "}
          {returnedSource ? (
            <a href={returnedSource.url} target="_blank" rel="noreferrer">
              civicAPI
            </a>
          ) : (
            "civicAPI"
          )}{" "}
          · Returned-ballot participation
        </p>
        <div className="panel-heading sr-only">
          <div>
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
            <h4>County reports</h4>
          </div>
          <span className="muted">Select a county for source definitions</span>
        </div>
        <div className="county-grid explorer">
          <section
            className="panel map-panel"
            aria-label="Returned-ballot party-registration map"
          >
            <div className="panel-heading">
              <h5>Arizona</h5>
              <span className="muted">Returned-ballot registration</span>
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
            className="panel table-panel table-region"
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
          </section>
        </div>
      </section>
      <span className="sr-only" role="status">
        {county
          ? `${county.name} County selected. Participation and source details updated.`
          : ""}
      </span>
      {county && (
        <section
          className="panel county-detail selection-panel"
          data-selected={county.geoid}
          aria-label="Selected county details"
          ref={detailRef}
          tabIndex={-1}
        >
          <div className="panel-heading">
            <div>
              <h4>{county.name} County</h4>
            </div>
            <button
              className="close-button"
              onClick={() => onSelect("")}
              aria-label="Close county details"
            >
              <Icon name="close" />
            </button>
          </div>
          <ParticipationMetrics metrics={county.metrics} />
          <div className="county-context">
            <p>
              Party categories describe voter registration, not candidate
              support. Independents corresponds to the source’s “Other”
              category.
            </p>
          </div>
          <details className="county-definitions">
            <summary>Definitions, coverage & reporting dates</summary>
            {returnedMetrics.flatMap(({ key }) => {
              const metric = county.metrics.find(
                (metric) => metric.key === key,
              );
              return metric
                ? [
                    <section className="metric-definition" key={key}>
                      <h5>{metric.label}</h5>
                      <p>{metric.definition}</p>
                      <p>
                        {metric.coverage_note}
                        {metric.completeness === "partial"
                          ? " Partial source coverage."
                          : ""}
                      </p>
                      <dl>
                        <div>
                          <dt>Source report</dt>
                          <dd>
                            {reportTime(
                              metric.reported_at,
                              metric.report_precision,
                            )}
                          </dd>
                        </div>
                        <div>
                          <dt>Retrieved</dt>
                          <dd>
                            {reportTime(metric.retrieved_at)}
                            {metric.stale ? " · Stale" : ""}
                          </dd>
                        </div>
                      </dl>
                    </section>,
                  ]
                : [];
            })}
          </details>
        </section>
      )}
      <EarlyVotingSources />
    </>
  );
}
