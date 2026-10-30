import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { Link } from "react-router-dom";
import type { Election } from "../types";
import { useResource } from "../api";
import { Availability, ErrorState, Loading } from "../components";
import LiveElection from "./LiveElection";
import { prefetchElections } from "../electionPrefetch";
import Icon from "../Icon";

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
  const [federalOffice, setFederalOffice] = useState("us-senate");
  const [stateOffice, setStateOffice] = useState("governor");
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const selectedOffices: readonly string[] =
    selectedTab === "federal"
      ? [federalOffice]
      : selectedTab === "state"
        ? [stateOffice]
        : catalogTabs.find((tab) => tab.id === selectedTab)!.offices;

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
  const prefetchOffice =
    selectedTab === "federal"
      ? federalOffice
      : selectedTab === "state"
        ? stateOffice
        : null;
  useEffect(() => {
    if (!prefetchOffice || !elections) return;
    const controller = new AbortController();
    let running = false;
    const warm = async () => {
      if (running || controller.signal.aborted) return;
      running = true;
      try {
        await prefetchElections(elections, prefetchOffice, controller.signal);
      } finally {
        running = false;
      }
    };
    // Skip StrictMode's immediately cancelled first effect.
    queueMicrotask(() => void warm());
    window.addEventListener("online", warm);
    return () => {
      controller.abort();
      window.removeEventListener("online", warm);
    };
  }, [prefetchOffice, elections]);

  const categoryElections =
    elections?.filter((e) => selectedOffices.includes(e.office_id)) ?? [];
  return (
    <>
      <section className="home-intro catalog-intro">
        <div>
          <h1>
            Every county.
            <br />
            Every vote, in context.
          </h1>
          <p className="lead">
            Explore Arizona’s election history through certified results, county
            maps, and the numbers behind the outcome.
          </p>
        </div>
        <aside>
          <strong>Independent. Unofficial. Source-linked.</strong>
          <p>
            Each results page identifies its data source and how its reported
            figures are presented.
          </p>
          <Link to="/methodology">About the data</Link>
        </aside>
      </section>
      {loading ? (
        <Loading />
      ) : error ? (
        <ErrorState message={error} />
      ) : (
        elections && (
          <>
            <section className="catalog">
              <h2 className="sr-only">Election catalog</h2>
              <div
                className="catalog-tabs categories"
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
                    (tab.id === "live" ? (
                      categoryElections.length ? (
                        <LiveElection election={categoryElections[0]} />
                      ) : (
                        <p className="empty">
                          No elections available in this category yet.
                        </p>
                      )
                    ) : (
                      <div className="catalog-layout">
                        <aside className="office-nav">
                          <h2>Browse offices</h2>
                          <nav
                            className="office-buttons"
                            aria-label="Office directory"
                          >
                            {(tab.id === "federal"
                              ? [
                                  ["us-senate", "U.S. Senate"],
                                  ["us-house", "U.S. House"],
                                ]
                              : [
                                  ["governor", "Governor"],
                                  ["attorney-general", "Attorney General"],
                                ]
                            ).map(([value, label]) => (
                              <button
                                key={value}
                                type="button"
                                aria-pressed={
                                  (tab.id === "federal"
                                    ? federalOffice
                                    : stateOffice) === value
                                }
                                onClick={() =>
                                  tab.id === "federal"
                                    ? setFederalOffice(value)
                                    : setStateOffice(value)
                                }
                              >
                                {label}
                              </button>
                            ))}
                          </nav>
                        </aside>
                        <section
                          className="office-section"
                          aria-label={`${tab.id === "federal" ? "Federal" : "State"} election archive`}
                        >
                          <div className="catalog-office-filter mobile-office control">
                            <label htmlFor={`${tab.id}-office`}>
                              {tab.id === "federal" ? "Federal" : "State"}{" "}
                              office
                            </label>
                            <select
                              id={`${tab.id}-office`}
                              value={
                                tab.id === "federal"
                                  ? federalOffice
                                  : stateOffice
                              }
                              onChange={(event) =>
                                tab.id === "federal"
                                  ? setFederalOffice(event.target.value)
                                  : setStateOffice(event.target.value)
                              }
                            >
                              {(tab.id === "federal"
                                ? [
                                    ["us-senate", "U.S. Senate"],
                                    ["us-house", "U.S. House"],
                                  ]
                                : [
                                    ["governor", "Governor"],
                                    ["attorney-general", "Attorney General"],
                                  ]
                              ).map(([value, label]) => (
                                <option key={value} value={value}>
                                  {label}
                                </option>
                              ))}
                            </select>
                          </div>
                          <div className="archive-heading">
                            <h2>
                              {elections.find((e) =>
                                selectedOffices.includes(e.office_id),
                              )?.office ??
                                (tab.id === "federal"
                                  ? federalOffice === "us-house"
                                    ? "U.S. House"
                                    : "U.S. Senate"
                                  : stateOffice === "governor"
                                    ? "Governor"
                                    : "Attorney General")}
                            </h2>
                            <span className="small muted">
                              {categoryElections.length} elections ·{" "}
                              {selectedOffices.includes("us-house")
                                ? "Districts"
                                : "Statewide office"}
                            </span>
                          </div>
                          {categoryElections.length === 0 ? (
                            <p className="empty">
                              No elections available in this category yet.
                            </p>
                          ) : (
                            <div className="election-grid archive-list">
                              {[...categoryElections]
                                .sort((a, b) => b.date.localeCompare(a.date))
                                .map((e) => (
                                  <Link
                                    to={`/elections/${e.id}`}
                                    className="election-card archive-row"
                                    key={e.id}
                                  >
                                    <strong className="card-year year">
                                      {e.year}
                                    </strong>
                                    <div>
                                      <h3 className="title">
                                        Arizona {e.office}
                                        {e.district_label
                                          ? ` · ${e.district_label}`
                                          : ""}
                                      </h3>
                                      <p className="description">
                                        {e.kind === "special"
                                          ? `Special election · ${e.date} · `
                                          : "General election · "}
                                        {e.status === "civicapi"
                                          ? `${e.district_count ?? 1} special-election district · civicAPI candidate report`
                                          : e.status === "verified"
                                            ? e.district_count !== undefined
                                              ? `${e.district_count} ${e.district_count === 1 ? "district" : "districts"} · ${e.candidate_count} candidates`
                                              : `${e.county_count} counties · ${e.candidate_count} candidates`
                                            : e.status === "unofficial"
                                              ? "Unofficial reported results · counting in progress"
                                              : "Source located · results awaiting verification"}
                                      </p>
                                      <span className="sr-only">
                                        {e.status === "civicapi"
                                          ? "Explore civicAPI report"
                                          : e.status === "verified"
                                            ? "Explore results"
                                            : "View availability"}
                                      </span>
                                    </div>
                                    <Availability status={e.status} />
                                    <span className="arrow">
                                      <Icon name="arrow" />
                                    </span>
                                  </Link>
                                ))}
                            </div>
                          )}
                        </section>
                      </div>
                    ))}
                </div>
              ))}
            </section>
            {selectedTab !== "live" && (
              <aside className="provenance-banner provenance">
                <p>
                  <strong>Sources are clear for every election.</strong>
                  <br />
                  Each results page identifies its data source and how its
                  reported figures are presented.
                </p>
                <Link to="/methodology">
                  Our methodology <Icon name="arrow" />
                </Link>
              </aside>
            )}
          </>
        )
      )}
    </>
  );
}
