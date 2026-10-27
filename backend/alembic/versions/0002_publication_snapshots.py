"""Versioned event participation and contest publication lifecycle."""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "publication_snapshots",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "event_id", sa.String(), sa.ForeignKey("election_events.id"), nullable=False
        ),
        sa.Column(
            "contest_id", sa.String(), sa.ForeignKey("contests.id"), nullable=False
        ),
        *[
            sa.Column(k, sa.String(), nullable=False)
            for k in ["stream", "kind", "stage", "completeness", "verification"]
        ],
        sa.Column(
            "source_id", sa.String(), sa.ForeignKey("sources.id"), nullable=False
        ),
        sa.Column("reported_at", sa.String(), nullable=True),
        *[
            sa.Column(k, sa.String(), nullable=False)
            for k in ["report_precision", "retrieved_at", "release_id", "vote_scope"]
        ],
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
    )
    op.create_table(
        "election_publications",
        sa.Column(
            "contest_id", sa.String(), sa.ForeignKey("contests.id"), primary_key=True
        ),
        *[
            sa.Column(k, sa.String(), nullable=False)
            for k in ["stage", "completeness", "verification"]
        ],
        sa.Column(
            "result_snapshot_id",
            sa.String(),
            sa.ForeignKey("publication_snapshots.id"),
            nullable=True,
        ),
        sa.Column("notes", sa.String(), nullable=False),
    )
    op.create_table(
        "current_snapshots",
        sa.Column(
            "event_id",
            sa.String(),
            sa.ForeignKey("election_events.id"),
            primary_key=True,
        ),
        sa.Column("stream", sa.String(), primary_key=True),
        sa.Column(
            "snapshot_id",
            sa.String(),
            sa.ForeignKey("publication_snapshots.id"),
            nullable=False,
        ),
        sa.Column("checked_at", sa.String(), nullable=False),
    )
    op.create_table(
        "metric_observations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "snapshot_id",
            sa.String(),
            sa.ForeignKey("publication_snapshots.id"),
            nullable=False,
        ),
        sa.Column(
            "unit_id", sa.String(), sa.ForeignKey("geographic_units.id"), nullable=False
        ),
        *[
            sa.Column(k, sa.String(), nullable=False)
            for k in ["key", "label", "definition"]
        ],
        sa.Column("value", sa.Integer(), nullable=True),
        *[
            sa.Column(k, sa.String(), nullable=False)
            for k in ["completeness", "coverage_note"]
        ],
        sa.UniqueConstraint("snapshot_id", "unit_id", "key"),
        sa.CheckConstraint("value >= 0"),
    )
    op.create_table(
        "refresh_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "event_id", sa.String(), sa.ForeignKey("election_events.id"), nullable=False
        ),
        sa.Column("stream", sa.String(), nullable=False),
        sa.Column("attempted_at", sa.String(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column(
            "snapshot_id",
            sa.String(),
            sa.ForeignKey("publication_snapshots.id"),
            nullable=True,
        ),
    )


def downgrade():
    for name in [
        "refresh_attempts",
        "metric_observations",
        "current_snapshots",
        "election_publications",
        "publication_snapshots",
    ]:
        op.drop_table(name)
