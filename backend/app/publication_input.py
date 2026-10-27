"""Reviewed aggregate release contract. No voter-level or forecast inputs."""

from datetime import date, datetime, timezone
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SnapshotSource(StrictModel):
    title: str
    url: str
    raw_path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    notes: str


class MetricInput(StrictModel):
    geoid: str
    key: Literal[
        "registered_voters",
        "ballots_requested",
        "ballots_mailed",
        "ballots_issued",
        "ballots_verified_ready",
        "ballots_turned_over",
        "ballots_received",
        "ballots_accepted",
        "in_person_early",
    ]
    label: str
    definition: str
    value: int | None = Field(ge=0, strict=True)
    completeness: Literal["complete", "partial", "unavailable"]
    coverage_note: str = ""


class CandidateInput(StrictModel):
    key: str
    name: str
    party: str
    party_name: str
    write_in: bool
    category: Literal["named_candidate", "aggregate_write_in"] = "named_candidate"


class VoteInput(StrictModel):
    geoid: str
    candidate: str
    votes: int | None = Field(ge=0, strict=True)


class SnapshotInput(StrictModel):
    election_date: Literal["2026-11-03"]
    election_kind: Literal["general"]
    stream: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,79}$")
    kind: Literal["participation", "results"]
    stage: Literal["pre_results", "unofficial", "certified"]
    completeness: Literal["complete", "partial", "unavailable"]
    verification: Literal["source_checked", "reconciled"]
    source: SnapshotSource
    reported_at: str | None
    report_precision: Literal["datetime", "date", "unknown"]
    retrieved_at: str
    release_id: str
    vote_scope: Literal["participation", "total", "early_only"]
    metrics: list[MetricInput] = []
    candidates: list[CandidateInput] = []
    votes: list[VoteInput] = []
    roster_complete: bool = False
    complete_units: list[str] = []
    reference_path: str | None = None
    certification: SnapshotSource | None = None
    notes: str
    source_warnings: list[str] = []

    @field_validator("retrieved_at")
    @classmethod
    def aware_retrieval(cls, value):
        if datetime.fromisoformat(value.replace("Z", "+00:00")).tzinfo is None:
            raise ValueError("Retrieval time requires a UTC offset")
        return (
            datetime.fromisoformat(value.replace("Z", "+00:00"))
            .astimezone(timezone.utc)
            .isoformat()
        )

    @model_validator(mode="after")
    def timestamps_and_kind(self):
        if self.report_precision == "unknown":
            if self.reported_at is not None:
                raise ValueError("Unknown source time must be null")
        elif self.report_precision == "date":
            date.fromisoformat(self.reported_at or "")
        elif (
            datetime.fromisoformat(
                (self.reported_at or "").replace("Z", "+00:00")
            ).tzinfo
            is None
        ):
            raise ValueError("Source time requires a UTC offset")
        if self.report_precision == "datetime":
            self.reported_at = (
                datetime.fromisoformat(self.reported_at.replace("Z", "+00:00"))
                .astimezone(timezone.utc)
                .isoformat()
            )
        if self.kind == "participation":
            if (
                self.candidates
                or self.votes
                or self.vote_scope != "participation"
                or self.stage != "pre_results"
            ):
                raise ValueError(
                    "Participation snapshots cannot contain candidate results"
                )
        elif (
            self.metrics
            or self.stage == "pre_results"
            or self.vote_scope == "participation"
            or self.stream != "results"
        ):
            raise ValueError(
                "Results must be a single publisher results stream, with explicit vote scope"
            )
        if self.stage == "certified" and (
            not self.certification
            or not self.reference_path
            or self.vote_scope != "total"
            or self.verification != "reconciled"
            or self.completeness != "complete"
        ):
            raise ValueError(
                "Certification requires a final-canvass source, authoritative reference and complete total results"
            )
        return self
