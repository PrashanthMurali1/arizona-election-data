import { Link, useNavigate } from "react-router-dom";
import type { RefObject } from "react";
import type { Activity, Election, Geography, Results } from "../types";
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
}: {
  election: Election;
  years: Election[];
  activity: Activity;
  geo: Geography;
  counties: Results[];
  selected: string | null;
  onSelect: (id: string) => void;
  detailRef: RefObject<HTMLElement | null>;
}) {
  const navigate = useNavigate();
  const county = activity.counties.find((c) => c.geoid === selected);
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
            {election.office} <span>{election.year}</span>
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
          {activity.candidate_availability === "not_imported"
            ? "Candidate results have not been imported — refresh official sources."
            : "Voting in progress — candidate results not yet released."}
        </strong>
        <p>
          These figures describe participation in the November general election.
          They are not votes cast specifically for {election.office}, candidate
          support, or a forecast.
        </p>
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
          <span className="muted">Official source records</span>
        </div>
        <div className="turnout-metrics statewide-activity">
          <div>
            <small>Official active registered voters</small>
            <strong>
              {number(activityValue(activity.statewide, "registered_voters"))}
            </strong>
          </div>
          <div>
            <small>Official statewide early returns</small>
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
      <SnapshotNotice activity={activity} />
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
            aria-label="County participation map"
          >
            <div className="panel-heading">
              <h3>Arizona</h3>
              <span className="muted">
                All {activity.counties.length} counties
              </span>
            </div>
            <CountyMap
              geography={geo}
              counties={counties}
              selected={selected}
              onSelect={onSelect}
              mode="activity"
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
              N/A means no verified official figure imported. * Partial source
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
              {county.metrics.map((m) => (
                <div className="activity-metric" key={m.key}>
                  <div className="activity-value">
                    <strong>{m.label}</strong>
                    <strong>
                      {number(m.value)}
                      {m.completeness === "partial" ? " *" : ""}
                    </strong>
                  </div>
                  <p className="footnote">
                    {m.definition} {m.coverage_note}
                  </p>
                  {m.source_id && (
                    <p className="footnote">
                      Source report / last edit:{" "}
                      {reportTime(m.reported_at, m.report_precision)} ·
                      Retrieved: {reportTime(m.retrieved_at)}
                      {m.stale ? " · Stale" : ""}
                      <br />
                      {
                        activity.sources.find((s) => s.id === m.source_id)
                          ?.title
                      }
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
                Select any county on the map or in the table to see official
                aggregate figures, source dates and unavailable metrics.
              </p>
            </div>
          </div>
        )}
      </section>
      <section className="sources">
        <p className="eyebrow">TRANSPARENT BY DESIGN</p>
        <h2>Sources & coverage</h2>
        <p>
          Active registration: {activity.coverage.registered_voters} /{" "}
          {activity.counties.length} counties. Returns:{" "}
          {activity.coverage.ballots_received} / {activity.counties.length}.
          Ballots accepted: {activity.coverage.ballots_accepted} /{" "}
          {activity.counties.length}. In-person early participation:{" "}
          {activity.coverage.in_person_early} / {activity.counties.length}.
          These coverage counts do not imply that unavailable values are zero.
        </p>
        <div className="sources-grid">
          {activity.sources.map((s) => (
            <a key={s.id} href={s.url} target="_blank" rel="noreferrer">
              <small>OFFICIAL AGGREGATE SOURCE ↗</small>
              <strong>{s.title}</strong>
              <span>{s.notes}</span>
            </a>
          ))}
        </div>
        <Link to="/methodology">Read the data methodology ↗</Link>
      </section>
    </>
  );
}
