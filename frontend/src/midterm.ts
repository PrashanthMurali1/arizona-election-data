import type {
  Candidate,
  Geography,
  MidtermCandidate,
  MidtermCounty,
  MidtermRace,
  MidtermResults,
  Results,
} from "./types";

export const midtermOffices = [
  ["governor", "Governor"],
  ["attorney-general", "Attorney General"],
  ["secretary-of-state", "Secretary of State"],
  ["us-house", "U.S. House"],
  ["state-senate", "State Senate"],
  ["state-house", "State House"],
] as const;

export const districtOffices: readonly string[] = [
  "us-house",
  "state-senate",
  "state-house",
];

// Match the server's overdue windows, including when the browser is offline.
export function midtermIsStale(
  data: MidtermResults,
  now = Date.now(),
): boolean {
  if (data.stale || data.refresh_error) return true;
  const races = Object.values(data.offices).flat();
  const overdue = (retrieved: string, completed = false) => {
    const age = now - Date.parse(retrieved);
    return !Number.isFinite(age) || age > (completed ? 6 * 60 : 15) * 60_000;
  };
  return races.length
    ? races.some(
        (race) =>
          race.status !== "certified" &&
          (Boolean(race.refresh_error) ||
            overdue(
              race.retrieved_at || data.retrieved_at,
              race.percent_reporting === 100,
            )),
      )
    : overdue(data.retrieved_at);
}

const codes: Record<string, string> = {
  Democratic: "DEM",
  Republican: "REP",
  Green: "GRN",
  Libertarian: "LIB",
  Independent: "IND",
  Nonpartisan: "NP",
  "No Labels": "NL",
};

// Shares are computed from votes: they are 0 before counting, whatever units the provider uses.
export function toCandidates(
  source: MidtermCandidate[],
  total: number,
): Candidate[] {
  return source.map((c, index) => ({
    id: `${index}-${c.name}`,
    name: c.name,
    party: codes[c.party ?? ""] ?? (c.party ?? "?").slice(0, 3).toUpperCase(),
    party_name: c.party ?? "Unknown",
    write_in: /^write-?in$/i.test(c.name),
    category: "candidate",
    votes: c.votes ?? null,
    percent: c.votes == null ? null : total > 0 ? (c.votes / total) * 100 : 0,
    status: "source_checked",
  }));
}

export function toResults(
  unit: {
    name: string;
    total_votes: number;
    candidates: MidtermCandidate[];
    percent_reporting: number | null;
  },
  geoid: string,
): Results {
  const candidates = toCandidates(unit.candidates, unit.total_votes);
  return {
    geoid,
    name: unit.name,
    status: "unofficial",
    percent_reporting: unit.percent_reporting,
    total_votes: unit.total_votes,
    candidates,
    // A leader only exists once votes do; until then the map stays neutral grey.
    winner: unit.total_votes > 0 ? (candidates[0] ?? null) : null,
    turnout: {
      ballots_cast: null,
      registered_voters: null,
      percent: null,
      definition: "Not supplied by civicAPI for this race.",
      source_id: null,
    },
  };
}

export const countyResults = (county: MidtermCounty): Results =>
  toResults(county, county.fips);

export const districtId = (district: number) => `d${district}`;

// Arizona legislative districts elect two House members, so the top `seats` candidates lead together.
// The leader label lists their last names; the district is colored by their party only when they
// share one, and stays neutral ("SPLIT") when the two leading seats are held by different parties.
export function withSeats(result: Results, seats: number): Results {
  if (seats < 2 || !result.total_votes) return result;
  const leaders = result.candidates.slice(0, seats).filter((c) => c.votes);
  if (leaders.length < 2) return result;
  const party = leaders.every((c) => c.party === leaders[0].party)
    ? leaders[0].party
    : "SPLIT";
  return {
    ...result,
    winner: {
      ...leaders[0],
      name: leaders.map((c) => c.name.split(" ").pop()).join(" / "),
      party,
    },
  };
}

export const districtResults = (race: MidtermRace, seats = 1): Results =>
  withSeats(
    toResults(
      { ...race, name: `District ${race.district}` },
      districtId(race.district!),
    ),
    seats,
  );

// Congressional and legislative boundary files identify districts differently;
// give every feature the id that districtResults() uses.
export function withDistrictIds(geography: Geography): Geography {
  return {
    ...geography,
    features: geography.features.map((feature) => {
      const district = Number(feature.properties?.district);
      return {
        ...feature,
        properties: {
          ...feature.properties,
          geoid: districtId(district),
          name: `District ${district}`,
          label: String(district),
        },
      };
    }),
  };
}
