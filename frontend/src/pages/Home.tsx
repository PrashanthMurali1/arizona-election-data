import { useRef, useState, type KeyboardEvent } from "react";
import { Link } from "react-router-dom";
import type { Election } from "../types";
import { useResource } from "../api";
import { Availability, ErrorState, Loading } from "../components";
import LiveElection from "./LiveElection";

const catalogTabs = [
  { id: "live", label: "Live Elections", offices: ["early-voting"] },
  {
    id: "federal",
    label: "Federal Elections",
    offices: ["us-senate", "us-house"],
  },
  {
    id: "state",
    label: "State Elections",
    offices: ["governor", "attorney-general"],
  },
] as const;

export default function Home() {
  const [selectedTab, setSelectedTab] =
    useState<(typeof catalogTabs)[number]["id"]>("live");
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const selectedOffices: readonly string[] = catalogTabs.find(
    (tab) => tab.id === selectedTab,
  )!.offices;

  function navigateTabs(
    event: KeyboardEvent<HTMLButtonElement>,
    index: number,
  ) {
    let nextIndex: number;
    switch (event.key) {
      case "ArrowRight":
        nextIndex = (index + 1) % catalogTabs.length;
        break;
      case "ArrowLeft":
        nextIndex = (index + catalogTabs.length - 1) % catalogTabs.length;
        break;
      case "Home":
        nextIndex = 0;
        break;
      case "End":
        nextIndex = catalogTabs.length - 1;
        break;
      default:
        return;
    }
    event.preventDefault();
    setSelectedTab(catalogTabs[nextIndex].id);
    tabRefs.current[nextIndex]?.focus();
  }

  const {
    data: elections,
    error,
    loading,
  } = useResource<Election[]>("/api/elections");
  const categoryElections =
    elections?.filter((e) => selectedOffices.includes(e.office_id)) ?? [];
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
            <section className="catalog">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">EXPLORE THE ARCHIVE</p>
                  <h2>Election catalog</h2>
                </div>
                <span className="muted">Organized by office</span>
              </div>
              <div
                className="catalog-tabs"
                role="tablist"
                aria-label="Election categories"
              >
                {catalogTabs.map((tab, index) => (
                  <button
                    key={tab.id}
                    ref={(element) => {
                      tabRefs.current[index] = element;
                    }}
                    type="button"
                    role="tab"
                    id={`catalog-tab-${tab.id}`}
                    aria-controls={`catalog-panel-${tab.id}`}
                    aria-selected={selectedTab === tab.id}
                    tabIndex={selectedTab === tab.id ? 0 : -1}
                    onClick={() => setSelectedTab(tab.id)}
                    onKeyDown={(event) => navigateTabs(event, index)}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
              {catalogTabs.map((tab) => (
                <div
                  key={tab.id}
                  role="tabpanel"
                  id={`catalog-panel-${tab.id}`}
                  aria-labelledby={`catalog-tab-${tab.id}`}
                  hidden={selectedTab !== tab.id}
                  tabIndex={0}
                >
                  {selectedTab === tab.id &&
                    (categoryElections.length === 0 ? (
                      <p className="empty">
                        No elections available in this category yet.
                      </p>
                    ) : tab.id === "live" ? (
                      <LiveElection election={categoryElections[0]} />
                    ) : (
                      [
                        ...new Set(categoryElections.map((e) => e.office_id)),
                      ].map((office) => (
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
                            <span className="muted">
                              {office === "us-house"
                                ? "Congressional districts"
                                : office === "early-voting"
                                  ? "Statewide participation"
                                  : "Statewide office"}
                            </span>
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
                                  aria-label={
                                    e.office_id === "early-voting"
                                      ? `${e.year} Early Voting`
                                      : undefined
                                  }
                                >
                                  <div className="card-top">
                                    <span className="eyebrow">
                                      {e.kind.toUpperCase()} ELECTION
                                    </span>
                                    <Availability status={e.status} />
                                  </div>
                                  <strong className="card-year">
                                    {e.year}
                                  </strong>
                                  <h3>
                                    {e.office_id === "early-voting"
                                      ? e.office
                                      : `Arizona ${e.office}`}
                                    {e.district_label
                                      ? ` · ${e.district_label}`
                                      : ""}
                                  </h3>
                                  <p>
                                    {e.office_id === "early-voting"
                                      ? `${e.county_count} counties · Requested and returned ballots`
                                      : e.status === "civicapi"
                                        ? `${e.district_count ?? 1} special-election district · civicAPI candidate report · ${e.date}`
                                        : e.status === "verified"
                                          ? e.district_count !== undefined
                                            ? `${e.district_count} ${e.district_count === 1 ? "district" : "districts"} · ${e.candidate_count} candidates${e.kind === "special" ? ` · ${e.date}` : ""}`
                                            : `${e.county_count} counties · ${e.candidate_count} candidates`
                                          : e.status === "pre_results"
                                            ? "General-election participation · candidate results not released"
                                            : e.status === "unofficial"
                                              ? "Unofficial reported results · counting in progress"
                                              : "Source located · results awaiting verification"}
                                  </p>
                                  <div className="card-bottom">
                                    <span>
                                      {e.status === "civicapi"
                                        ? "Explore civicAPI report"
                                        : e.status === "verified"
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
                      ))
                    ))}
                </div>
              ))}
            </section>
            <aside className="provenance-banner">
              <span className="provenance-icon" aria-hidden="true">
                ✓
              </span>
              <div>
                <h3>Sources are clear for every election.</h3>
                <p>
                  Each results page identifies its data source and how its
                  reported figures are presented.
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
