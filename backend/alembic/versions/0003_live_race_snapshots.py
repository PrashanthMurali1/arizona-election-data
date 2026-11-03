"""Isolated latest unofficial race snapshots; historical data is untouched."""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = depends_on = None


def upgrade():
    op.create_table("live_race_snapshots",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("election_date", sa.String(), nullable=False),
        sa.Column("race_id", sa.Integer(), nullable=False),
        sa.Column("office", sa.String(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("revision", sa.String(), nullable=False),
        sa.Column("retrieved_at", sa.String(), nullable=False),
        sa.Column("source_url", sa.String(), nullable=False),
        sa.Column("raw_sha256", sa.String(), nullable=True),
        sa.Column("completed", sa.Boolean(), nullable=False),
        sa.Column("certified", sa.Boolean(), nullable=False),
        sa.Column("attempted_at", sa.String(), nullable=False),
        sa.Column("refresh_error", sa.String(), nullable=True),
        sa.UniqueConstraint("election_date", "race_id"))
    op.create_index("ix_live_race_snapshots_election_date", "live_race_snapshots", ["election_date"])
    op.create_index("ix_live_race_snapshots_office", "live_race_snapshots", ["office"])


def downgrade():
    op.drop_table("live_race_snapshots")
