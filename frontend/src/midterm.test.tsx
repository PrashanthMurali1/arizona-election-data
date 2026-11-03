import { expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import CountyTable from "./CountyTable";
import { sortCounties } from "./results";
import {
  countyResults,
  districtResults,
  midtermIsStale,
  toCandidates,
  toResults,
  withDistrictIds,
} from "./midterm";
import type {
  Geography,
  MidtermCandidate,
  MidtermRace,
  MidtermResults,
} from "./types";

it("marks locally cached races overdue using their own retrieval times and server freshness windows", () => {
  const now = Date.parse("2026-11-04T12:00:00Z");
  const snapshot = (races: MidtermRace[]): MidtermResults => ({
    election_date: "2026-11-03",
    source_url: "",
    retrieved_at: new Date(now).toISOString(),
    stale: false,
    refresh_error: null,
    revision: "r1",
    offices: { governor: races },
  });
  const old = (minutes: number, extra: Partial<MidtermRace> = {}) =>
    race(null, [], {
      retrieved_at: new Date(now - minutes * 60_000).toISOString(),
      ...extra,
    });
  expect(midtermIsStale(snapshot([old(14)]), now)).toBe(false);
  expect(midtermIsStale(snapshot([old(16)]), now)).toBe(true);
  expect(
    midtermIsStale(snapshot([old(359, { percent_reporting: 100 })]), now),
  ).toBe(false);
  expect(
    midtermIsStale(snapshot([old(361, { percent_reporting: 100 })]), now),
  ).toBe(true);
  expect(
    midtermIsStale(snapshot([old(999, { status: "certified" })]), now),
  ).toBe(false);
  expect(
    midtermIsStale(snapshot([old(1, { refresh_error: "offline" })]), now),
  ).toBe(true);
  expect(
    midtermIsStale(
      {
        ...snapshot([race(null, [])]),
        retrieved_at: new Date(now - 16 * 60_000).toISOString(),
      },
      now,
    ),
  ).toBe(true);
});

const candidate = (
  name: string,
  party: string,
  votes: number,
): MidtermCandidate => ({
  name,
  party,
  color: null,
  votes,
  percent: 0,
  winner: false,
  seats: null,
});
const race = (
  district: number | null,
  candidates: MidtermCandidate[],
  extra: Partial<MidtermRace> = {},
): MidtermRace => ({
  id: 1,
  name: "Arizona State House",
  district,
  percent_reporting: 0,
  total_votes: candidates.reduce((n, c) => n + (c.votes ?? 0), 0),
  called: false,
  source_url: "",
  seats: null,
  candidates,
  counties: [],
  ...extra,
});

it("shares are computed from votes and are zero before counting", () => {
  expect(
    toCandidates([candidate("A", "Democratic", 0)], 0).map((c) => c.percent),
  ).toEqual([0]);
  const [a, b] = toCandidates(
    [candidate("A", "Democratic", 75), candidate("B", "Republican", 25)],
    100,
  );
  expect([a.percent, b.percent, a.party, b.party]).toEqual([
    75,
    25,
    "DEM",
    "REP",
  ]);
  const empty = toResults(race(null, [candidate("A", "Democratic", 0)]), "04");
  expect(empty.winner).toBeNull(); // grey map until there is a leader
  expect(empty.percent_reporting).toBe(0);
});

it("matches boundary features to districts by number for either boundary file", () => {
  const geography = {
    type: "FeatureCollection",
    features: [
      { type: "Feature", properties: { district: 5 }, geometry: null }, // congressional (number)
      { type: "Feature", properties: { district: "19" }, geometry: null }, // legislative (string)
    ],
  } as unknown as Geography;
  const ids = withDistrictIds(geography).features.map((f) => [
    f.properties?.geoid,
    f.properties?.name,
    f.properties?.label,
  ]);
  expect(ids).toEqual([
    ["d5", "District 5", "5"],
    ["d19", "District 19", "19"],
  ]);
  expect(districtResults(race(5, [])).geoid).toBe("d5");
});

it("two-member State House districts show both leaders and color only when they share a party", () => {
  const split = districtResults(
    race(7, [
      candidate("Ann Lee", "Republican", 50),
      candidate("Bo Kim", "Democratic", 40),
      candidate("Cy Wu", "Republican", 30),
    ]),
    2,
  );
  expect(split.winner?.name).toBe("Lee / Kim");
  expect(split.winner?.party).toBe("SPLIT"); // neutral on the map
  const sweep = districtResults(
    race(8, [
      candidate("Ann Lee", "Republican", 50),
      candidate("Cy Wu", "Republican", 45),
      candidate("Bo Kim", "Democratic", 40),
    ]),
    2,
  );
  expect(sweep.winner?.party).toBe("REP");
  // One seat, no votes, or a single candidate with votes keeps the plain leader.
  const one = districtResults(
    race(9, [candidate("Ann Lee", "Republican", 5)]),
    2,
  );
  expect(one.winner?.name).toBe("Ann Lee");
  expect(
    districtResults(race(10, [candidate("A", "Republican", 0)]), 2).winner,
  ).toBeNull();
});

const county = (name: string, votes: number, reporting: number | null) =>
  countyResults({
    fips: "04001",
    name,
    percent_reporting: reporting,
    total_votes: votes,
    candidates: [
      candidate("Katie Hobbs", "Democratic", Math.round(votes * 0.6)),
      candidate("Andy Biggs", "Republican", Math.round(votes * 0.4)),
    ],
  });

it("live tables show Dem %, Rep %, leader and Reporting % only, 0.00% before counting", () => {
  const html = renderToStaticMarkup(
    <CountyTable
      counties={[county("Apache", 0, 0), county("Pima", 100, 62.5)]}
      selected={null}
      onSelect={() => {}}
      provisional
    />,
  );
  for (const header of ["Dem %", "Rep %", "Current leader", "Reporting %"])
    expect(html).toContain(header);
  expect(html).not.toContain("Contest votes");
  expect(html).not.toContain("Turnout");
  expect(html).toContain("62.50%");
  expect(html).toContain("60.00%"); // Pima Dem share
  expect(html).toContain("0.00%"); // Apache before counting, not N/A for the shares
  expect(html.match(/N\/A/g)?.length ?? 0).toBe(1); // only Apache's leader
});

it("the reporting column is omitted when the API returns no reporting data", () => {
  const html = renderToStaticMarkup(
    <CountyTable
      counties={[county("Apache", 10, null), county("Pima", 20, null)]}
      selected={null}
      onSelect={() => {}}
      provisional
    />,
  );
  expect(html).not.toContain("Reporting %");
  expect(html).toContain("Current leader");
});

it("district names sort in numeric order for live tables only", () => {
  const rows = [10, 2, 1].map((n) => ({
    ...county(`District ${n}`, 1, 0),
    geoid: `d${n}`,
  }));
  expect(sortCounties(rows, "name", "asc", true).map((r) => r.name)).toEqual([
    "District 1",
    "District 2",
    "District 10",
  ]);
  // Existing (historical) tables keep their original collation.
  expect(sortCounties(rows, "name", "asc").map((r) => r.name)).toEqual([
    "District 1",
    "District 10",
    "District 2",
  ]);
});
