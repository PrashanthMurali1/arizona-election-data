import { Link } from "react-router-dom";
import type { Election } from "../types";
import { useResource } from "../api";
import { Availability, ErrorState, Loading } from "../components";
import { number } from "../results";
export default function Home() {
  const {
    data: elections,
    error,
    loading,
  } = useResource<Election[]>("/api/elections");
  return (
    <>
      <section className="home-intro">
        <p className="eyebrow">
          <span />
          THE GRAND CANYON STATE · ELECTION ARCHIVE
        </p>
        <h1>
          Every county.
          <br />
          <span>Every vote, in context.</span>
        </h1>
        <p className="lead">
          Explore Arizona’s election history through certified results, county
          maps, and the numbers behind the outcome.
        </p>
      </section>
      {loading ? (
        <Loading />
      ) : error ? (
        <ErrorState message={error} />
      ) : (
        elections && (
          <>
            <section className="stats" aria-label="Archive overview">
              <div>
                <span>Election records</span>
                <strong>
                  {number(elections.length)}
                  <small>in the archive</small>
                </strong>
              </div>
              <div>
                <span>Verified elections</span>
                <strong>
                  {number(
                    elections.filter((e) => e.status === "verified").length,
                  )}
                  <small>official totals reconciled</small>
                </strong>
              </div>
              <div>
                <span>Arizona counties</span>
                <strong>
                  {number(Math.max(0, ...elections.map((e) => e.county_count)))}
                  <small>across the state</small>
                </strong>
              </div>
              <div>
                <span>Coverage</span>
                <strong>
                  {elections.length
                    ? `${Math.min(...elections.map((e) => e.year))}—${Math.max(...elections.map((e) => e.year))}`
                    : "N/A"}
                  <small>general elections</small>
                </strong>
              </div>
            </section>
            <section className="catalog">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">EXPLORE THE ARCHIVE</p>
                  <h2>Election catalog</h2>
                </div>
                <span className="muted">Organized by office</span>
              </div>
              {elections.length === 0 ? (
                <p className="empty">
                  No election records yet. Run the documented data import.
                </p>
              ) : (
                [...new Set(elections.map((e) => e.office_id))].map(
                  (office) => (
                    <div key={office} className="office-section">
                      <div className="office-heading">
                        <span className="office-symbol" aria-hidden="true">
                          ▥
                        </span>
                        <h3>
                          {
                            elections.find((e) => e.office_id === office)
                              ?.office
                          }
                        </h3>
                        <span className="muted">Statewide office</span>
                        <span className="office-rule" />
                      </div>
                      <div className="election-grid">
                        {elections
                          .filter((e) => e.office_id === office)
                          .sort((a, b) => b.year - a.year)
                          .map((e) => (
                            <Link
                              to={`/elections/${e.id}`}
                              className="election-card"
                              key={e.id}
                            >
                              <div className="card-top">
                                <span className="eyebrow">
                                  GENERAL ELECTION
                                </span>
                                <Availability status={e.status} />
                              </div>
                              <strong className="card-year">{e.year}</strong>
                              <h3>Arizona {e.office}</h3>
                              <p>
                                {e.status === "verified"
                                  ? `${e.county_count} counties · ${e.candidate_count} candidates`
                                  : e.status === "pre_results"
                                    ? "General-election participation · candidate results not released"
                                    : e.status === "unofficial"
                                      ? "Unofficial reported results · counting in progress"
                                      : "Source located · results awaiting verification"}
                              </p>
                              <div className="card-bottom">
                                <span>
                                  {e.status === "verified"
                                    ? "Explore results"
                                    : e.status === "pre_results"
                                      ? "Explore early voting"
                                      : e.status === "unofficial"
                                        ? "Explore reported results"
                                        : "View availability"}
                                </span>
                                <span aria-hidden="true">↗</span>
                              </div>
                            </Link>
                          ))}
                      </div>
                    </div>
                  ),
                )
              )}
            </section>
            <aside className="provenance-banner">
              <span className="provenance-icon" aria-hidden="true">
                ✓
              </span>
              <div>
                <h3>Built on the official record.</h3>
                <p>
                  County results are reconciled against published statewide
                  totals. Every election includes its sources and verification
                  status.
                </p>
              </div>
              <Link to="/methodology">Our methodology ↗</Link>
            </aside>
          </>
        )
      )}
    </>
  );
}
