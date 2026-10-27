import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import type { Activity, Detail, Election, Geography, Results } from "../types";
import EarlyVotingPage from "./EarlyVotingPage";
import SnapshotNotice from "../SnapshotNotice";
import { get, useResource } from "../api";
import {
  Availability,
  CandidateSummary,
  ErrorState,
  Loading,
  TurnoutMetrics,
} from "../components";
import { number } from "../results";
import CountyMap from "../Map";
import CountyTable from "../CountyTable";
export default function ElectionPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const catalog = useResource<Election[]>("/api/elections");
  const [state, setState] = useState<{
    detail: Detail;
    counties: Results[];
    geo: Geography;
    activity: Activity | null;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const detailRef = useRef<HTMLElement>(null);
  useEffect(() => {
    const controller = new AbortController();
    setState(null);
    setError(null);
    setSelected(null);
    get<Detail>(`/api/elections/${id}`, controller.signal)
      .then(async (detail) => {
        const [counties, geo, activity] = await Promise.all([
          get<Results[]>(`/api/elections/${id}/counties`, controller.signal),
          get<Geography>(
            `/api/geography/${detail.election.boundary_id}`,
            controller.signal,
          ),
          get<Activity | null>(
            `/api/elections/${id}/activity`,
            controller.signal,
          ),
        ]);
        if (!controller.signal.aborted)
          setState({ detail, counties, geo, activity });
      })
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      });
    return () => controller.abort();
  }, [id]);
  function selectCounty(geoid: string) {
    setSelected(geoid);
    requestAnimationFrame(() =>
      detailRef.current?.focus({ preventScroll: true }),
    );
  }
  if (error) return <ErrorState message={error} />;
  if (!state) return <Loading />;
  const { detail, counties, geo, activity } = state;
  const { election, statewide } = detail;
  const county = counties.find((c) => c.geoid === selected);
  const years = catalog.data?.filter(
    (e) => e.office_id === election.office_id,
  ) ?? [election];
  if (activity?.stage === "pre_results")
    return (
      <EarlyVotingPage
        election={election}
        years={years}
        activity={activity}
        geo={geo}
        counties={counties}
        selected={selected}
        onSelect={selectCounty}
        detailRef={detailRef}
      />
    );
  const provisional = activity?.stage === "unofficial";
  const mapCounties = provisional
    ? counties.map((c) => ({
        ...c,
        winner: activity.reported_leaders[c.geoid] ?? null,
      }))
    : counties;
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
          <p className="eyebrow">
            ARIZONA · {election.kind.toUpperCase()} ELECTION
          </p>
          <h1>
            {election.office} <span>{election.year}</span>
          </h1>
          <div className="election-meta">
            <Availability status={election.status} />
            <span>
              {new Date(`${election.date}T12:00:00`).toLocaleDateString(
                "en-US",
                { month: "long", day: "numeric", year: "numeric" },
              )}
            </span>
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
                {e.kind === "special" ? " · special election" : ""}
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
      {election.status !== "verified" && (
        <div className="notice" role="status">
          <strong>
            {provisional
              ? "Unofficial — counting in progress."
              : "This election is incomplete."}
          </strong>
          <p>
            {election.notes}{" "}
            {provisional
              ? "Map colors indicate current reported leaders, not certified winners. Missing reporting units remain unavailable."
              : "Winners and percentages are withheld until the dataset can be verified."}
          </p>
        </div>
      )}
      {activity && <SnapshotNotice activity={activity} />}
      <section className="panel statewide">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">THE STATEWIDE PICTURE</p>
            <h2>Candidate results</h2>
          </div>
          <div className="contest-total">
            <strong>{number(statewide.total_votes)}</strong>
            <span>votes in this contest</span>
          </div>
        </div>
        <CandidateSummary results={statewide} />
        <div className="statewide-foot">
          <span>{number(election.county_count)} counties represented</span>
          <span>
            Vote shares include all verified candidates and write-ins.
          </span>
        </div>
      </section>
      <section className="county-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">A CLOSER LOOK</p>
            <h2>County by county</h2>
          </div>
          <span className="muted">Select a county to explore</span>
        </div>
        <div className="county-grid">
          <section className="panel map-panel" aria-label="County winner map">
            <div className="panel-heading">
              <h3>Arizona</h3>
              <span className="muted">
                {provisional ? "Current reported leaders" : "County winners"}
              </span>
            </div>
            <CountyMap
              geography={geo}
              counties={mapCounties}
              selected={selected}
              onSelect={selectCounty}
              mode={provisional ? "unofficial" : "results"}
            />
          </section>
          <section
            className="panel table-panel"
            aria-label="County results table"
          >
            <div className="panel-heading">
              <h3>County results</h3>
              <span className="muted">{counties.length} counties</span>
            </div>
            <CountyTable
              counties={mapCounties}
              selected={selected}
              onSelect={selectCounty}
              provisional={provisional}
            />
            <p className="footnote table-note">
              Dem / Rep shares include all candidates of that party. Contest
              votes exclude undervotes and overvotes. Turnout is the official
              election-wide figure.
            </p>
          </section>
        </div>
      </section>
      <section
        className="panel county-detail"
        ref={detailRef}
        tabIndex={-1}
        aria-label="Selected county details"
        aria-live="polite"
      >
        {county ? (
          <>
            <div className="panel-heading">
              <div>
                <p className="eyebrow">COUNTY DETAILS · FIPS {county.geoid}</p>
                <h2>{county.name} County</h2>
              </div>
              <button
                className="close-button"
                onClick={() => setSelected(null)}
                aria-label="Close county details"
              >
                ×
              </button>
            </div>
            <div className="detail-grid">
              <div>
                <h3>All candidate results</h3>
                <CandidateSummary results={county} />
              </div>
              <div className="turnout-panel">
                <p className="eyebrow">ELECTION PARTICIPATION</p>
                <h3>Beyond the contest</h3>
                <TurnoutMetrics turnout={county.turnout} />
                <p className="footnote">
                  {number(county.total_votes)} verified votes in the{" "}
                  {election.office.toLowerCase()} contest. This differs from
                  total ballots cast.
                </p>
              </div>
            </div>
          </>
        ) : (
          <div className="select-prompt">
            <span aria-hidden="true">⌖</span>
            <div>
              <h3>Explore a county’s story</h3>
              <p>
                Select any county on the map or in the table to see every
                candidate’s results and official turnout.
              </p>
            </div>
          </div>
        )}
      </section>
      <section className="sources">
        <p className="eyebrow">TRANSPARENT BY DESIGN</p>
        <h2>Sources & verification</h2>
        <p>{election.notes}</p>
        <div className="sources-grid">
          {detail.sources.map((s) => (
            <a key={s.id} href={s.url} target="_blank" rel="noreferrer">
              <small>DATA SOURCE ↗</small>
              <strong>{s.title}</strong>
              <span>{s.notes}</span>
            </a>
          ))}
        </div>
        <details>
          <summary>View reconciliation report</summary>
          {detail.reconciliation ? (
            <div className="table-scroll">
              <table>
                <caption>
                  County sums compared with published statewide totals
                </caption>
                <thead>
                  <tr>
                    <th>Candidate</th>
                    <th>County sum</th>
                    <th>Official statewide</th>
                    <th>Difference</th>
                    <th>Missing counties</th>
                  </tr>
                </thead>
                <tbody>
                  {detail.reconciliation.candidates.map((r) => (
                    <tr key={r.candidate}>
                      <th>{r.candidate}</th>
                      <td>{number(r.county_sum)}</td>
                      <td>{number(r.official_statewide)}</td>
                      <td>{number(r.difference)}</td>
                      <td>
                        {r.missing_counties.length
                          ? r.missing_counties.join(", ")
                          : "None"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p>No verified import yet.</p>
          )}
        </details>
        <Link to="/methodology">Read the data methodology ↗</Link>
      </section>
    </>
  );
}
