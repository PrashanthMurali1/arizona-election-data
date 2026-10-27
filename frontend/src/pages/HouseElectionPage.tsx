import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import type { Election, Geography, HouseOverview } from "../types";
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

export default function HouseElectionPage({ id }: { id: string }) {
  const navigate = useNavigate();
  const catalog = useResource<Election[]>("/api/elections");
  const [state, setState] = useState<{
    overview: HouseOverview;
    geo: Geography;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(true);
  const detailRef = useRef<HTMLElement>(null);
  useEffect(() => {
    const controller = new AbortController();
    get<HouseOverview>(`/api/elections/${id}`, controller.signal)
      .then(async (overview) => {
        if (!overview.districts)
          throw new Error(
            "Open a House election from the catalog to select its districts.",
          );
        const geo = await get<Geography>(
          `/api/geography/${overview.election.boundary_id}`,
          controller.signal,
        );
        if (!controller.signal.aborted) {
          setState({ overview, geo });
          setSelected(overview.default_district);
        }
      })
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      });
    return () => controller.abort();
  }, [id]);
  if (error) return <ErrorState message={error} />;
  if (!state || !selected) return <Loading />;
  const { overview, geo } = state;
  const { election, districts } = overview;
  const active = districts.find((d) => d.geoid === selected && d.contested)!;
  const contested = districts.filter((d) => d.contested);
  const report = overview.reconciliation.reports[selected];
  const years = catalog.data
    ?.filter((e) => e.office_id === "us-house")
    .sort((a, b) => b.date.localeCompare(a.date)) ?? [election];
  function selectDistrict(unit: string) {
    if (!districts.some((d) => d.geoid === unit && d.contested)) return;
    setSelected(unit);
    setDetailsOpen(true);
    requestAnimationFrame(() =>
      detailRef.current?.focus({ preventScroll: true }),
    );
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
            value={id}
            onChange={(e) => navigate(`/elections/${e.target.value}`)}
          >
            {years.map((e) => (
              <option key={e.id} value={e.id}>
                {e.selection_label}
              </option>
            ))}
          </select>
        </label>
      </section>
      {(election.status !== "verified" || election.kind === "special") && (
        <div className="notice" role="status">
          <strong>
            {election.kind === "special"
              ? "civicAPI report · not an official canvass"
              : "This election is incomplete."}
          </strong>
          <p>{election.notes}</p>
        </div>
      )}
      <section className="panel statewide">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">
              SELECTED DISTRICT · {active.name.toUpperCase()}
            </p>
            <h2>Candidate results</h2>
          </div>
          <div className="contest-total">
            <strong>{number(active.total_votes)}</strong>
            <span>votes in this district contest</span>
          </div>
        </div>
        <CandidateSummary results={active} />
        <div className="statewide-foot">
          <span>
            {active.name} · {number(contested.length)}{" "}
            {contested.length === 1
              ? "district contested"
              : "districts contested"}
          </span>
          <span>
            {election.kind === "special"
              ? "Vote shares use the listed civicAPI candidates."
              : "Vote shares include all verified candidates and write-ins in this district."}
          </span>
        </div>
      </section>
      <section className="county-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">A CLOSER LOOK</p>
            <h2>District by district</h2>
          </div>
          <span className="muted">Select a district to explore</span>
        </div>
        <div className="county-grid">
          <section className="panel map-panel" aria-label="District winner map">
            <div className="panel-heading">
              <h3>Arizona</h3>
              <span className="muted">District winners</span>
            </div>
            <CountyMap
              geography={geo}
              counties={districts}
              selected={selected}
              onSelect={selectDistrict}
              unitKind="district"
            />
          </section>
          <section
            className="panel table-panel"
            aria-label="District results table"
          >
            <div className="panel-heading">
              <h3>District results</h3>
              <span className="muted">
                {contested.length}{" "}
                {contested.length === 1 ? "district" : "districts"}
              </span>
            </div>
            <CountyTable
              counties={contested}
              selected={selected}
              onSelect={selectDistrict}
              unitKind="district"
            />
            <p className="footnote table-note">
              Shares and winners belong to each district’s own contest. Contest
              votes exclude undervotes and overvotes. Turnout requires an
              official district-specific source; unavailable figures remain N/A.
            </p>
          </section>
        </div>
      </section>
      <section
        className="panel county-detail"
        ref={detailRef}
        tabIndex={-1}
        aria-label="Selected district details"
        aria-live="polite"
      >
        {detailsOpen ? (
          <>
            <div className="panel-heading">
              <div>
                <p className="eyebrow">DISTRICT DETAILS · {selected}</p>
                <h2>{active.name}</h2>
              </div>
              <button
                className="close-button"
                onClick={() => setDetailsOpen(false)}
                aria-label="Close district details"
              >
                ×
              </button>
            </div>
            <div className="detail-grid">
              <div>
                <h3>All candidate results</h3>
                <CandidateSummary results={active} />
              </div>
              <div className="turnout-panel">
                <p className="eyebrow">ELECTION PARTICIPATION</p>
                <h3>Beyond the contest</h3>
                <TurnoutMetrics turnout={active.turnout} />
                <p className="footnote">
                  {number(active.total_votes)} {election.kind === "special" ? "reported" : "verified"} votes in this district’s
                  U.S. House contest. This differs from total ballots cast.
                </p>
              </div>
            </div>
          </>
        ) : (
          <div className="select-prompt">
            <span aria-hidden="true">⌖</span>
            <div>
              <h3>Explore a district’s story</h3>
              <p>
                Select a contested district on the map or in the table to see
                every candidate’s results and available district turnout.
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
          {overview.sources.map((source) => (
            <a
              key={source.id}
              href={source.url}
              target="_blank"
              rel="noreferrer"
            >
              <small>DATA SOURCE ↗</small>
              <strong>{source.title}</strong>
              <span>{source.notes}</span>
            </a>
          ))}
        </div>
        <details>
          <summary>
            {report?.kind === "provider_results"
              ? "View civicAPI report details"
              : "View reconciliation report"}
          </summary>
          {report ? (
            <div className="table-scroll">
              <table>
                <caption>
                  {report.kind === "provider_results"
                    ? `${active.name}: civicAPI candidate results as reported`
                    : `${active.name}: reporting-unit sums compared with official district totals`}
                </caption>
                <thead>
                  {report.kind === "provider_results" ? (
                    <tr>
                      <th>Candidate</th>
                      <th>Votes reported</th>
                      <th>civicAPI share</th>
                    </tr>
                  ) : (
                    <tr>
                      <th>Candidate</th>
                      <th>Reporting-unit sum</th>
                      <th>Official district</th>
                      <th>Difference</th>
                      <th>Missing reporting units</th>
                    </tr>
                  )}
                </thead>
                <tbody>
                  {report.candidates.map((candidate) => (
                    <tr key={candidate.candidate}>
                      <th>{candidate.candidate}</th>
                      {report.kind === "provider_results" ? (
                        <>
                          <td>{number(candidate.votes ?? null)}</td>
                          <td>{candidate.percent == null ? "N/A" : `${candidate.percent}%`}</td>
                        </>
                      ) : (
                        <>
                          <td>{number(candidate.county_sum ?? null)}</td>
                          <td>{number(candidate.official_district ?? null)}</td>
                          <td>{number(candidate.difference ?? null)}</td>
                          <td>
                            {candidate.missing_counties?.length
                              ? candidate.missing_counties.join(", ")
                              : "None"}
                          </td>
                        </>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
              {report.kind === "provider_results" && report.provider && (
                <p>
                  civicAPI reports {report.provider.percent_reporting ?? "N/A"}% reporting
                  {report.provider.last_updated
                    ? `; provider last updated ${new Date(report.provider.last_updated).toLocaleString("en-US", { dateStyle: "medium", timeStyle: "short", timeZone: "UTC" })} UTC.`
                    : "."}
                  {" "}No separate canvass reconciliation is represented here.
                </p>
              )}
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
