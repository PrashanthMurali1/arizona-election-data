import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import type { Election, Geography, HouseOverview } from "../types";
import { get, useResource } from "../api";
import {
  Availability,
  CandidateSummary,
  CandidateOverview,
  ErrorState,
  Loading,
  TurnoutMetrics,
} from "../components";
import { number } from "../results";
import Icon from "../Icon";
import useGeographySelection from "../useGeographySelection";
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
  const tableRef = useRef<HTMLElement>(null);
  const { detailRef, focusSelection, restoreFocus } =
    useGeographySelection(selected);
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
    focusSelection();
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
      <section className="election-heading page-heading">
        <div>
          <h1>
            {election.office} <span>{election.year}</span>
          </h1>
          <p className="election-description">
            {election.kind === "special" ? "Special" : "General"} election ·{" "}
            {new Date(`${election.date}T12:00:00`).toLocaleDateString("en-US", {
              month: "long",
              day: "numeric",
              year: "numeric",
            })}
          </p>
          <div className="election-meta">
            <Availability status={election.status} />
            <a href="#sources">
              {election.status === "civicapi"
                ? "Provider report & limitations"
                : "Sources & verification"}
            </a>
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
      <CandidateOverview
        results={active}
        unitKind="district"
        provider={election.status === "civicapi"}
      />
      <section className="county-section" id="geography-explorer">
        <div className="section-heading">
          <div>
            <h2>District by district</h2>
          </div>
          <span className="muted">Select a district to explore</span>
        </div>
        <div className="county-grid explorer">
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
            className="panel table-panel table-region"
            aria-label="District results table"
            ref={tableRef}
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
      <span className="sr-only" role="status">
        {detailsOpen
          ? `${active.name} selected. Candidate results and turnout updated.`
          : "District details closed."}
      </span>
      <section
        className="panel county-detail selection-panel"
        ref={detailRef}
        tabIndex={-1}
        aria-label="Selected district details"
      >
        {detailsOpen ? (
          <>
            <div className="panel-heading">
              <div>
                <h2>{active.name}</h2>
              </div>
              <button
                className="close-button"
                onClick={() => {
                  setDetailsOpen(false);
                  restoreFocus(
                    tableRef.current?.querySelector<HTMLButtonElement>(
                      'tbody button[aria-pressed="true"]',
                    ),
                  );
                }}
                aria-label="Close district details"
              >
                <Icon name="close" />
              </button>
            </div>
            <div className="detail-grid">
              <div>
                <h3>All candidate results</h3>
                <CandidateSummary results={active} />
              </div>
              <div className="turnout-panel">
                <h3>Beyond the contest</h3>
                <TurnoutMetrics turnout={active.turnout} />
                <p className="footnote">
                  {number(active.total_votes)}{" "}
                  {election.kind === "special" ? "reported" : "verified"} votes
                  in this district’s U.S. House contest. This differs from total
                  ballots cast.
                </p>
              </div>
            </div>
          </>
        ) : (
          <div className="select-prompt">
            <Icon name="location" />
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
      <section className="sources source-section" id="sources">
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
              <span className="source-link-icon">
                <Icon name="arrow" />
              </span>
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
            <div
              className="table-scroll scroll-region"
              tabIndex={0}
              role="region"
              aria-label="Scrollable source report"
            >
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
                          <td>
                            {candidate.percent == null
                              ? "N/A"
                              : `${candidate.percent}%`}
                          </td>
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
                  civicAPI reports {report.provider.percent_reporting ?? "N/A"}%
                  reporting
                  {report.provider.last_updated
                    ? `; provider last updated ${new Date(report.provider.last_updated).toLocaleString("en-US", { dateStyle: "medium", timeStyle: "short", timeZone: "UTC" })} UTC.`
                    : "."}{" "}
                  No separate canvass reconciliation is represented here.
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
