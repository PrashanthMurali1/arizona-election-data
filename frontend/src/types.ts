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
  ballots_cast: number | null;
  registered_voters: number | null;
  percent: number | null;
  definition: string;
  source_id: string | null;
}
export interface Results {
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
  stage: "pre_results" | "unofficial" | "certified";
  candidate_availability: "not_released" | "not_imported" | "published";
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
