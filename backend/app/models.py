from sqlalchemy import ForeignKey, UniqueConstraint, CheckConstraint, JSON, Float
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base


class Office(Base):
    __tablename__ = "offices"
    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]


class ElectionEvent(Base):
    __tablename__ = "election_events"
    id: Mapped[str] = mapped_column(primary_key=True)
    year: Mapped[int]
    date: Mapped[str]
    kind: Mapped[str]


class Source(Base):
    __tablename__ = "sources"
    id: Mapped[str] = mapped_column(primary_key=True)
    title: Mapped[str]
    url: Mapped[str]
    sha256: Mapped[str]
    notes: Mapped[str]


class BoundaryVersion(Base):
    __tablename__ = "boundary_versions"
    id: Mapped[str] = mapped_column(primary_key=True)
    vintage: Mapped[int]
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"))


class GeographicUnit(Base):
    __tablename__ = "geographic_units"
    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    kind: Mapped[str]


class Geometry(Base):
    __tablename__ = "geometries"
    __table_args__ = (UniqueConstraint("unit_id", "boundary_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    unit_id: Mapped[str] = mapped_column(ForeignKey("geographic_units.id"))
    boundary_id: Mapped[str] = mapped_column(ForeignKey("boundary_versions.id"))
    feature: Mapped[dict] = mapped_column(JSON)


class Contest(Base):
    __tablename__ = "contests"
    id: Mapped[str] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(ForeignKey("election_events.id"))
    office_id: Mapped[str] = mapped_column(ForeignKey("offices.id"))
    jurisdiction_id: Mapped[str] = mapped_column(ForeignKey("geographic_units.id"))
    boundary_id: Mapped[str] = mapped_column(ForeignKey("boundary_versions.id"))
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"))
    status: Mapped[str]
    notes: Mapped[str]


class Party(Base):
    __tablename__ = "parties"
    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]


class Candidate(Base):
    __tablename__ = "candidates"
    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]


class Participation(Base):
    __tablename__ = "participations"
    __table_args__ = (UniqueConstraint("contest_id", "candidate_id"),)
    id: Mapped[str] = mapped_column(primary_key=True)
    contest_id: Mapped[str] = mapped_column(ForeignKey("contests.id"))
    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates.id"))
    party_id: Mapped[str] = mapped_column(ForeignKey("parties.id"))
    write_in: Mapped[bool]
    category: Mapped[str]  # named_candidate or aggregate_write_in


class VoteResult(Base):
    __tablename__ = "vote_results"
    __table_args__ = (
        UniqueConstraint("participation_id", "unit_id"),
        CheckConstraint("votes >= 0"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    participation_id: Mapped[str] = mapped_column(ForeignKey("participations.id"))
    unit_id: Mapped[str] = mapped_column(ForeignKey("geographic_units.id"))
    votes: Mapped[int | None]
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"))
    status: Mapped[str]


class Turnout(Base):
    __tablename__ = "turnout"
    __table_args__ = (UniqueConstraint("event_id", "unit_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(ForeignKey("election_events.id"))
    unit_id: Mapped[str] = mapped_column(ForeignKey("geographic_units.id"))
    ballots_cast: Mapped[int | None]
    registered_voters: Mapped[int | None]
    percent: Mapped[float | None] = mapped_column(Float)
    definition: Mapped[str]
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"))


class ImportRun(Base):
    __tablename__ = "import_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    contest_id: Mapped[str] = mapped_column(ForeignKey("contests.id"))
    created_at: Mapped[str]
    status: Mapped[str]
    report: Mapped[dict] = mapped_column(JSON)


class ElectionPublication(Base):
    __tablename__ = "election_publications"
    contest_id: Mapped[str] = mapped_column(ForeignKey("contests.id"), primary_key=True)
    stage: Mapped[str]
    completeness: Mapped[str]
    verification: Mapped[str]
    result_snapshot_id: Mapped[str | None] = mapped_column(
        ForeignKey("publication_snapshots.id")
    )
    notes: Mapped[str]


class PublicationSnapshot(Base):
    __tablename__ = "publication_snapshots"
    id: Mapped[str] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(ForeignKey("election_events.id"))
    contest_id: Mapped[str] = mapped_column(ForeignKey("contests.id"))
    stream: Mapped[str]
    kind: Mapped[str]
    stage: Mapped[str]
    completeness: Mapped[str]
    verification: Mapped[str]
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"))
    reported_at: Mapped[str | None]
    report_precision: Mapped[str]
    retrieved_at: Mapped[str]
    release_id: Mapped[str]
    vote_scope: Mapped[str]
    payload: Mapped[dict] = mapped_column(JSON)
    warnings: Mapped[list] = mapped_column(JSON)


class CurrentSnapshot(Base):
    __tablename__ = "current_snapshots"
    event_id: Mapped[str] = mapped_column(
        ForeignKey("election_events.id"), primary_key=True
    )
    stream: Mapped[str] = mapped_column(primary_key=True)
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("publication_snapshots.id"))
    checked_at: Mapped[str]


class MetricObservation(Base):
    __tablename__ = "metric_observations"
    __table_args__ = (
        UniqueConstraint("snapshot_id", "unit_id", "key"),
        CheckConstraint("value >= 0"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("publication_snapshots.id"))
    unit_id: Mapped[str] = mapped_column(ForeignKey("geographic_units.id"))
    key: Mapped[str]
    label: Mapped[str]
    definition: Mapped[str]
    value: Mapped[int | None]
    completeness: Mapped[str]
    coverage_note: Mapped[str]


class RefreshAttempt(Base):
    __tablename__ = "refresh_attempts"
    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(ForeignKey("election_events.id"))
    stream: Mapped[str]
    attempted_at: Mapped[str]
    success: Mapped[bool]
    error: Mapped[str | None]
    snapshot_id: Mapped[str | None] = mapped_column(
        ForeignKey("publication_snapshots.id")
    )
