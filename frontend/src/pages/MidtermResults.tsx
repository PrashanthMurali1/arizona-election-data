import { useMemo, useState } from "react";
import {
  CandidateOverview,
  GeographyResults,
  ErrorState,
  Loading,
} from "../components";
import CountyMap from "../Map";
import CountyTable from "../CountyTable";
import Icon from "../Icon";
import useGeographySelection from "../useGeographySelection";
import { useResource } from "../api";
import { reportTime } from "../activity";
import { number } from "../results";
import type { Geography, MidtermRace, Results } from "../types";
import {
  countyResults,
  districtId,
  districtOffices,
  districtResults,
  midtermOffices,
  toResults,
  withDistrictIds,
} from "../midterm";
import { useMidterm } from "../useMidterm";

function Explorer({
  heading,
  unit,
  mapLabel,
  geography,
  units,
  selected,
  onSelect,
  unitKind,
}: {
  heading: string;
  unit: string;
  mapLabel: string;
  geography: Geography | null;
  units: Results[];
  selected: string | null;
  onSelect: (id: string) => void;
  unitKind: "county" | "district";
}) {
  return (
    <section className="county-section" id="geography-explorer">
      <div className="section-heading">
        <div>
          <h2>{heading}</h2>
        </div>
        <span className="muted">Select a {unit} to explore</span>
      </div>
      <div className={`county-grid explorer${geography ? "" : " without-map"}`}>
        {geography && (
          <section className="panel map-panel" aria-label={`${mapLabel} map`}>
            <div className="panel-heading">
              <h3>Arizona</h3>
              <span className="muted">Current reported leaders</span>
            </div>
            <CountyMap
              geography={geography}
              counties={units}
              selected={selected}
              onSelect={onSelect}
              unitKind={unitKind}
              mode="unofficial"
            />
          </section>
        )}
        <section
          className="panel table-panel table-region"
          aria-label={`${unit[0].toUpperCase()}${unit.slice(1)} results table`}
        >
          <div className="panel-heading">
            <h3>{unit[0].toUpperCase() + unit.slice(1)} results</h3>
            <span className="muted">
              {units.length} {unit === "county" ? "counties" : "districts"}
            </span>
          </div>
          <CountyTable
            counties={units}
            selected={selected}
            onSelect={onSelect}
            provisional
            unitKind={unitKind}
          />
        </section>
      </div>
    </section>
  );
}

function StatewideOffice({ race }: { race: MidtermRace }) {
  const [selected, setSelected] = useState<string | null>(null);
  const { detailRef, focusSelection } = useGeographySelection(selected);
  const geography = useResource<Geography>("/api/geography/county-2022").data;
  const counties = useMemo(() => race.counties.map(countyResults), [race]);
  const county = counties.find((c) => c.geoid === selected);
  const select = (id: string) => {
    setSelected(id);
    focusSelection();
  };
  return (
    <>
      <CandidateOverview results={toResults(race, "04")} />
      {counties.length > 0 && (
        <>
          <Explorer
            heading="County by county"
            unit="county"
            mapLabel="County winner"
            geography={geography}
            units={counties}
            selected={selected}
            onSelect={select}
            unitKind="county"
          />
          <section
            className="panel county-detail selection-panel"
            ref={detailRef}
            tabIndex={-1}
            aria-label="Selected county details"
          >
            {county ? (
              <GeographyResults
                results={county}
                title={`${county.name} County`}
                onClose={() => setSelected(null)}
                contestNote={
                  county.total_votes === 0 ? (
                    "No votes reported in this contest yet."
                  ) : (
                    <>
                      {number(county.total_votes)} reported votes in this
                      contest.
                    </>
                  )
                }
              />
            ) : (
              <div className="select-prompt">
                <Icon name="location" />
                <div>
                  <h3>Explore a county’s story</h3>
                  <p>Select any county on the map or in the table.</p>
                </div>
              </div>
            )}
          </section>
        </>
      )}
    </>
  );
}

function DistrictOffice({
  office,
  races,
}: {
  office: string;
  races: MidtermRace[];
}) {
  const chamber = races.find((race) => race.district == null);
  const units = useMemo(
    () =>
      races
        .filter((race) => race.district != null)
        .map((race) => districtResults(race, office === "state-house" ? 2 : 1)),
    [races, office],
  );
  const [selected, setSelected] = useState<string>(
    units[0]?.geoid ?? districtId(1),
  );
  const { detailRef, focusSelection } = useGeographySelection(selected);
  const source = useResource<Geography>(
    office === "us-house"
      ? "/api/geography/congressional-2022"
      : `/api/midterm-2026/geography/${office}`,
  ).data;
  const geography = useMemo(
    () => (source ? withDistrictIds(source) : null),
    [source],
  );
  const active = units.find((u) => u.geoid === selected) ?? units[0];
  return (
    <>
      {chamber && (
        <section className="result-summary" aria-label="Seats by party">
          <div className="summary-heading">
            <h2>Seats by party</h2>
          </div>
          <ul className="midterm-seats">
            {chamber.candidates.map((c) => (
              <li key={c.name}>
                <strong>{c.name}</strong>
                <span>
                  {c.seats ?? 0}
                  {chamber.seats != null ? ` of ${chamber.seats}` : ""} seats
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
      {active && (
        <div
          ref={detailRef as React.RefObject<HTMLDivElement>}
          tabIndex={-1}
          aria-label="Selected district results"
        >
          <CandidateOverview results={active} unitKind="district" />
        </div>
      )}
      <Explorer
        heading="District by district"
        unit="district"
        mapLabel="District winner"
        geography={geography}
        units={units}
        selected={selected}
        onSelect={(id) => {
          setSelected(id);
          focusSelection();
        }}
        unitKind="district"
      />
    </>
  );
}

export default function MidtermResults() {
  const { data, error, refreshError } = useMidterm();
  const [office, setOffice] = useState<string>("governor");
  if (error && !data) return <ErrorState message={error} />;
  if (!data) return <Loading />;
  const races = data.offices[office] ?? [];
  const label = midtermOffices.find(([id]) => id === office)![1];
  return (
    <div className="catalog-layout">
      <aside className="office-nav">
        <h2>Browse offices</h2>
        <nav className="office-buttons" aria-label="Midterm office directory">
          {midtermOffices.map(([value, text]) => (
            <button
              key={value}
              type="button"
              aria-pressed={office === value}
              onClick={() => setOffice(value)}
            >
              {text}
            </button>
          ))}
        </nav>
      </aside>
      <section className="office-section" aria-label="2026 midterm results">
        <div className="catalog-office-filter mobile-office control">
          <label htmlFor="midterm-office">Midterm office</label>
          <select
            id="midterm-office"
            value={office}
            onChange={(event) => setOffice(event.target.value)}
          >
            {midtermOffices.map(([value, text]) => (
              <option key={value} value={value}>
                {text}
              </option>
            ))}
          </select>
        </div>
        <div className="archive-heading">
          <h2>{label}</h2>
          <span className="small muted">
            {districtOffices.includes(office)
              ? "Districts"
              : "Statewide office"}{" "}
            · November 3, 2026
          </span>
        </div>
        <p className="muted midterm-source" role="status">
          Unofficial results · Source: <a href={data.source_url}>civicAPI</a> ·
          Retrieved {reportTime(data.retrieved_at)}
        </p>
        {(data.stale || refreshError) && (
          <div className="warn notice" role="alert">
            <div>
              <strong>Showing the last results we loaded.</strong>
              <p>
                The latest refresh failed, so these figures may be out of date.
              </p>
            </div>
          </div>
        )}
        {races.length === 0 ? (
          <p className="empty">No races available for this office yet.</p>
        ) : districtOffices.includes(office) ? (
          <DistrictOffice key={office} office={office} races={races} />
        ) : (
          <StatewideOffice key={races[0].id} race={races[0]} />
        )}
      </section>
    </div>
  );
}
