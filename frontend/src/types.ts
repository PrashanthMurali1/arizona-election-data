import type { FeatureCollection } from "geojson";
export interface Election {
  id: string;
  year: number;
  date: string;
  office_id: string;
  office: string;
  kind: string;
  status: string;
  notes: string;
  county_count: number;
  candidate_count: number;
  boundary_id: string;
  district_count?: number;
  selection_label?: string;
  district_label?: string | null;
}

export interface HouseDistrict extends Results {
  contest_id: string | null;
  contested: boolean;
}
export interface HouseReport {
  status: string;
  district: number;
  kind?: "county_reconciliation" | "provider_results";
  provider?: {
    provider: string;
    percent_reporting: number | null;
    last_updated: string | null;
  } | null;
  candidates: {
    candidate: string;
    county_sum?: number | null;
    official_district?: number | null;
    difference?: number | null;
    missing_counties?: string[];
    votes?: number;
    percent?: number | null;
    winner?: boolean;
  }[];
}
export interface HouseOverview {
  election: Election;
  districts: HouseDistrict[];
  default_district: string;
  sources: Source[];
  reconciliation: {
    status: string;
    district_count: number;
    reports: Record<string, HouseReport>;
  };
}
export interface Candidate {
  id: string;
  name: string;
  party: string;
  party_name: string;
  write_in: boolean;
  category: string;
  votes: number | null;
  percent: number | null;
  status: string;
}
export interface Turnout {
  basis?: "published" | "contest_votes" | "calculated_ballots";
  votes_cast?: number | null;
  ballots_cast: number | null;
  registered_voters: number | null;
  percent: number | null;
  definition: string;
  source_id: string | null;
}
export interface Results {
  partial?: boolean;
  // Share of precincts reported (0-100). Present only for live 2026 midterm results.
  percent_reporting?: number | null;
  geoid: string;
  name: string;
  status: string;
  total_votes: number | null;
  candidates: Candidate[];
  winner: Candidate | null;
  turnout: Turnout;
}
export interface Source {
  id: string;
  title: string;
  url: string;
  sha256: string;
  notes: string;
}
export interface Detail {
  election: Election;
  statewide: Results;
  sources: Source[];
  reconciliation: {
    status: string;
    county_count: number;
    candidates: {
      candidate: string;
      county_sum: number;
      official_statewide: number | null;
      difference: number | null;
      missing_counties: string[];
    }[];
  } | null;
}
export interface Geography extends FeatureCollection {
  boundary_id: string;
  vintage: number;
}

export interface ActivityMetric {
  key: string;
  label: string;
  definition: string;
  value: number | null;
  completeness: string;
  coverage_note: string;
  source_id: string | null;
  snapshot_id: string | null;
  reported_at: string | null;
  report_precision: string;
  retrieved_at: string | null;
  stale: boolean;
}
export interface Participation {
  geoid: string;
  name: string;
  metrics: ActivityMetric[];
}
export interface Activity {
  revision?: string;
  stage: "pre_results" | "unofficial" | "certified";
  candidate_availability:
    | "not_released"
    | "not_imported"
    | "published"
    | "test_data"
    | "not_reporting";
  provider_participation?: {
    provider: string;
    reports: {
      category: string;
      label: string;
      source_id: string;
      snapshot_id: string;
      breakdowns: Record<string, Record<string, number | null>>;
    }[];
  } | null;
  provider_report?: {
    provider: string;
    record_id: string;
    test_data: boolean;
    race_status: string;
    percent_reporting: number | null;
    candidates: {
      name: string;
      party: string;
      votes: number | null;
      percent: number | null;
      winner: boolean;
    }[];
  } | null;
  completeness: string;
  verification: string;
  notes: string;
  statewide: Participation;
  counties: Participation[];
  coverage: Record<string, number>;
  releases: {
    id: string;
    stream: string;
    kind: string;
    stage: string;
    reported_at: string | null;
    report_precision: string;
    retrieved_at: string;
    release_id: string;
    vote_scope: string;
    stale: boolean;
    error: string | null;
    source_id: string;
  }[];
  warnings: string[];
  stale: boolean;
  failures: { stream: string; attempted_at: string; error: string }[];
  sources: Source[];
  reported_leaders: Record<string, Candidate>;
  refresh_mode: string;
  statewide_policy: string;
}

export interface MidtermCandidate {
  name: string;
  party: string | null;
  color: string | null;
  votes: number | null;
  percent: number | null;
  winner: boolean;
  seats: number | null;
}
export interface MidtermRace {
  id: number;
  name: string;
  district: number | null;
  percent_reporting: number | null;
  total_votes: number;
  called: boolean;
  source_url: string;
  seats: number | null;
  candidates: MidtermCandidate[];
  counties: MidtermCounty[];
}
export interface MidtermCounty {
  fips: string;
  name: string;
  percent_reporting: number | null;
  total_votes: number;
  candidates: MidtermCandidate[];
}
export interface MidtermResults {
  election_date: string;
  source_url: string;
  retrieved_at: string;
  stale: boolean;
  refresh_error: string | null;
  // Snapshot identity announced by /api/midterm-2026/updates.
  revision: string;
  offices: Record<string, MidtermRace[]>;
}
