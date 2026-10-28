import { Link, useNavigate } from "react-router-dom";
import type { RefObject } from "react";
import type { Activity, ActivityMetric, Election, Geography, Results } from "../types";
import CountyMap from "../Map";
import ActivityTable from "../ActivityTable";
import SnapshotNotice from "../SnapshotNotice";
import { Availability } from "../components";
import { activityValue, reportTime } from "../activity";
import { number } from "../results";

export default function EarlyVotingPage({
  election,
  years,
  activity,
  geo,
  counties,
  selected,
  onSelect,
  detailRef,
  refreshError = null,
}: {
  election: Election;
  years: Election[];
  activity: Activity;
  geo: Geography;
  counties: Results[];
  selected: string | null;
  onSelect: (id: string) => void;
  detailRef: RefObject<HTMLElement | null>;
  refreshError?: string | null;
}) {
  const navigate = useNavigate();
  const county = activity.counties.find((c) => c.geoid === selected);
  const compactDetails = election.id === "az-2026-early-voting";
  const countyMetrics = county?.metrics.filter((metric) => !compactDetails || metric.value != null) ?? [];
  const participation = activity.provider_participation;
  const provider = participation
    ? { provider: participation.provider, test_data: false }
    : activity.provider_report;
  const firstMetric = participation ? "ballots_requested" : "registered_voters";
  const returnedBreakdowns = participation?.reports.find((report) => report.category === "returned")?.breakdowns ?? {};
  const detailLabel = (metric: ActivityMetric) => compactDetails
    ? metric.label.replace(/\bcivicapi(?:['’]s)?\s*/gi, "").trim()
    : metric.label;
  function detailDescription(metric: ActivityMetric) {
    if (!compactDetails) return `${metric.definition} ${metric.coverage_note}`;
    const key = metric.key.split("__")[0];
    const action = key === "ballots_requested" ? "requested" : key === "ballots_received" ? "returned" : null;
    if (action) {
      const party = metric.label.split("·").slice(1).join("·").trim();
      return party
        ? `Early ballots ${action}, grouped by ${party} voter registration.`
        : `Early ballots ${action} in this county.`;
    }
    return `${metric.definition} ${metric.coverage_note}`.replace(/\bcivicapi(?:['’]s)?\s*/gi, "").trim();
  }
  return (
    <>
      <div className="breadcrumbs">
        <Link to="/">Election catalog</Link>
        <span>/</span>
        <span>{election.office}</span>
        <span>/</span>
        <span>{election.year}</span>
      </div>
      <section className="election-heading">
        <div>
          <p className="eyebrow">ARIZONA · GENERAL ELECTION</p>
          <h1>
            {election.office_id === "early-voting" ? (
              <><span>{election.year}</span> {election.office}</>
            ) : <>{election.office} <span>{election.year}</span></>}
          </h1>
          <div className="election-meta">
            <Availability status="pre_results" />
            <span>November 3, 2026</span>
          </div>
        </div>
        <label className="year-picker">
          Election year
          <select
            value={election.id}
            onChange={(e) => navigate(`/elections/${e.target.value}`)}
          >
            {years.map((e) => (
              <option key={e.id} value={e.id}>
                {e.year}
                {e.status === "pre_results"
                  ? " · voting in progress"
                  : e.status === "unofficial"
                    ? " · unofficial"
                    : e.status !== "verified"
                      ? " · incomplete"
                      : ""}
              </option>
            ))}
          </select>
        </label>
      </section>
      <div className="notice" role="status">
        <strong>
          {compactDetails
            ? "Early-voting participation reports."
            : participation
            ? `Early-voting participation reports · ${participation.provider}.`
            : provider?.test_data
            ? `${provider.provider} marks this race record as test data — live results unavailable.`
            : provider
            ? `${provider.provider} has not started reporting candidate results.`
            : activity.candidate_availability === "not_imported"
            ? "Candidate results have not been imported — refresh official sources."
            : "Voting in progress — candidate results not yet released."}
        </strong>
        <p>
          These figures describe participation in the November general election.
          Party categories indicate voter registration, not candidate choices or how anyone voted.
        </p>
        {!compactDetails && provider && !participation && <p>{activity.notes}</p>}
      </div>
      <section
        className="panel statewide"
        aria-label="Statewide participation availability"
      >
        <div className="panel-heading">
          <div>
            <p className="eyebrow">GENERAL-ELECTION PARTICIPATION</p>
            <h2>Early-voting activity</h2>
          </div>
          {!compactDetails && <span className="muted">{provider ? `${provider.provider} source records` : "Official source records"}</span>}
        </div>
        <div className="turnout-metrics statewide-activity">
          <div>
            <small>{participation ? "Requested" : provider ? "Provider registered voters" : "Official active registered voters"}</small>
            <strong>
              {number(activityValue(activity.statewide, firstMetric))}
            </strong>
          </div>
          <div>
            <small>{participation ? "Returned" : provider ? "Provider statewide early returns" : "Official statewide early returns"}</small>
            <strong>
              {number(activityValue(activity.statewide, "ballots_received"))}
            </strong>
          </div>
          <div>
            <small>Counties with a sourced return figure</small>
            <strong>
              {activity.coverage.ballots_received} / {activity.counties.length}
            </strong>
          </div>
        </div>
        <div className="statewide-foot">
          <span>{activity.statewide_policy}</span>
        </div>
      </section>
      {!compactDetails && <SnapshotNotice activity={activity} />}
      <section className="county-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">PARTICIPATION, COUNTY BY COUNTY</p>
            <h2>County reports</h2>
          </div>
          <span className="muted">Select a county for source definitions</span>
        </div>
        <div className="county-grid">
          <section
            className="panel map-panel"
            aria-label="Returned-ballot party-registration map"
          >
            <div className="panel-heading">
              <h3>Arizona</h3>
              <span className="muted">
                Returned-ballot party registration
              </span>
            </div>
            <CountyMap
              geography={geo}
              counties={counties}
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
              <h3>Early-voting activity</h3>
              <span className="muted">No candidate results</span>
            </div>
            <ActivityTable
              counties={activity.counties}
              selected={selected}
              onSelect={onSelect}
            />
            <p className="footnote table-note">
              {provider ? "N/A means the selected provider has not supplied this metric." : "N/A means no verified official figure imported."} * Partial source
              coverage. Requested, sent, received and accepted are different
              stages. Select a county for exact source labels, definitions and
              dates; county rows are not a statewide total.
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
                <h2>{county.name} County</h2>
              </div>
              <button
                className="close-button"
                onClick={() => onSelect("")}
                aria-label="Close county details"
              >
                ×
              </button>
            </div>
            <div className="activity-details">
              {countyMetrics.map((m) => (
                <div className="activity-metric" key={m.key}>
                  <div className="activity-value">
                    <strong>{detailLabel(m)}</strong>
                    <strong>
                      {number(m.value)}
                      {m.completeness === "partial" ? " *" : ""}
                    </strong>
                  </div>
                  <p className="footnote">
                    {detailDescription(m)}
                  </p>
                  {m.source_id && (
                    <p className="footnote">
                      {compactDetails ? "As of:" : "Source report / last edit:"}{" "}
                      {reportTime(m.reported_at, m.report_precision)} ·
                      Retrieved: {reportTime(m.retrieved_at)}
                      {m.stale ? " · Stale" : ""}
                      {!compactDetails && <>
                        <br />
                        {activity.sources.find((s) => s.id === m.source_id)?.title}
                      </>}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </>
        ) : (
          <div className="select-prompt">
            <span aria-hidden="true">⌖</span>
            <div>
              <h3>Explore a county’s participation</h3>
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
        <h2>Sources & coverage</h2>
        {compactDetails && (refreshError || activity.stale) && (
          <div className="notice" role="status">
            <strong>{refreshError ? "Update check failed" : activity.failures.length ? "Early-voting refresh delayed" : "Early-voting data may be outdated"}</strong>
            <p>{refreshError ?? "Showing the last successfully retrieved figures. A refresh failed or retrieval is more than 12 hours old."}</p>
          </div>
        )}
        <p>
          Active registration: {activity.coverage.registered_voters} /{" "}
          {activity.counties.length} counties. Requested: {activity.coverage.ballots_requested} / {activity.counties.length}. Returned:{" "}
          {activity.coverage.ballots_received} / {activity.counties.length}.
          Ballots accepted: {activity.coverage.ballots_accepted} /{" "}
          {activity.counties.length}. In-person early participation:{" "}
          {activity.coverage.in_person_early} / {activity.counties.length}.
          These coverage counts do not imply that unavailable values are zero.
        </p>
        {participation?.reports.map((report) => (
          <p key={report.snapshot_id}>
            <strong>{report.label} · statewide provider party breakdown: </strong>
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
              <small>{provider ? "PROVIDER REPORT ↗" : "OFFICIAL AGGREGATE SOURCE ↗"}</small>
              <strong>{s.title}</strong>
              <span>{s.notes}</span>
              {compactDetails && release && (
                <span>
                  Source report: {reportTime(release.reported_at, release.report_precision)}
                  <br />
                  Last successful retrieval: {reportTime(release.retrieved_at)}
                  {release.error && <><br />Latest refresh failed: {release.error}</>}
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
