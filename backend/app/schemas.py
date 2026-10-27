from typing import Any
from pydantic import BaseModel


class SourceOut(BaseModel):
    id: str
    title: str
    url: str
    sha256: str
    notes: str


class ElectionOut(BaseModel):
    id: str
    year: int
    date: str
    office_id: str
    office: str
    kind: str
    status: str
    notes: str
    county_count: int
    candidate_count: int
    boundary_id: str


class CandidateOut(BaseModel):
    id: str
    name: str
    party: str
    party_name: str
    write_in: bool
    category: str
    votes: int | None
    percent: float | None
    status: str


class TurnoutOut(BaseModel):
    ballots_cast: int | None = None
    registered_voters: int | None = None
    percent: float | None = None
    definition: str = (
        "N/A — official turnout has not been imported for this reporting unit."
    )
    source_id: str | None = None


class ResultsOut(BaseModel):
    geoid: str
    name: str
    status: str
    total_votes: int | None
    candidates: list[CandidateOut]
    winner: CandidateOut | None
    turnout: TurnoutOut


class DetailOut(BaseModel):
    election: ElectionOut
    statewide: ResultsOut
    sources: list[SourceOut]
    reconciliation: dict[str, Any] | None


class GeometryOut(BaseModel):
    type: str = "FeatureCollection"
    boundary_id: str
    vintage: int
    features: list[dict[str, Any]]


class MetricOut(BaseModel):
    key: str
    label: str
    definition: str
    value: int | None
    completeness: str
    coverage_note: str
    source_id: str | None
    snapshot_id: str | None
    reported_at: str | None
    report_precision: str
    retrieved_at: str | None
    stale: bool


class ParticipationOut(BaseModel):
    geoid: str
    name: str
    metrics: list[MetricOut]


class ReleaseOut(BaseModel):
    id: str
    stream: str
    kind: str
    stage: str
    reported_at: str | None
    report_precision: str
    retrieved_at: str
    release_id: str
    vote_scope: str
    stale: bool
    error: str | None
    source_id: str


class ActivityOut(BaseModel):
    stage: str
    candidate_availability: str
    completeness: str
    verification: str
    notes: str
    statewide: ParticipationOut
    counties: list[ParticipationOut]
    coverage: dict[str, int]
    releases: list[ReleaseOut]
    warnings: list[str]
    stale: bool
    failures: list[dict[str, str]]
    sources: list[SourceOut]
    reported_leaders: dict[str, CandidateOut]
    refresh_mode: str
    statewide_policy: str
