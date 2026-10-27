"""Initial normalized election schema.

Revision ID: 0001
"""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None


def upgrade():
    # Snapshot defined here rather than importing mutable application metadata.
    m = sa.MetaData()

    def table(name, *columns, constraints=()):
        return sa.Table(name, m, *columns, *constraints)

    def text(name, pk=False, fk=None, nullable=False):
        return sa.Column(
            name,
            sa.String(),
            *([sa.ForeignKey(fk)] if fk else []),
            primary_key=pk,
            nullable=nullable,
        )

    def integer(name, nullable=False, pk=False):
        return sa.Column(name, sa.Integer(), primary_key=pk, nullable=nullable)

    table("offices", text("id", True), text("name"))
    table(
        "election_events", text("id", True), integer("year"), text("date"), text("kind")
    )
    table(
        "sources",
        text("id", True),
        text("title"),
        text("url"),
        text("sha256"),
        text("notes"),
    )
    table(
        "boundary_versions",
        text("id", True),
        integer("vintage"),
        text("source_id", fk="sources.id"),
    )
    table("geographic_units", text("id", True), text("name"), text("kind"))
    table(
        "geometries",
        integer("id", pk=True),
        text("unit_id", fk="geographic_units.id"),
        text("boundary_id", fk="boundary_versions.id"),
        sa.Column("feature", sa.JSON(), nullable=False),
        constraints=[sa.UniqueConstraint("unit_id", "boundary_id")],
    )
    table(
        "contests",
        text("id", True),
        text("event_id", fk="election_events.id"),
        text("office_id", fk="offices.id"),
        text("jurisdiction_id", fk="geographic_units.id"),
        text("boundary_id", fk="boundary_versions.id"),
        text("source_id", fk="sources.id"),
        text("status"),
        text("notes"),
    )
    table("parties", text("id", True), text("name"))
    table("candidates", text("id", True), text("name"))
    table(
        "participations",
        text("id", True),
        text("contest_id", fk="contests.id"),
        text("candidate_id", fk="candidates.id"),
        text("party_id", fk="parties.id"),
        sa.Column("write_in", sa.Boolean(), nullable=False),
        text("category"),
        constraints=[sa.UniqueConstraint("contest_id", "candidate_id")],
    )
    table(
        "vote_results",
        integer("id", pk=True),
        text("participation_id", fk="participations.id"),
        text("unit_id", fk="geographic_units.id"),
        integer("votes", True),
        text("source_id", fk="sources.id"),
        text("status"),
        constraints=[
            sa.UniqueConstraint("participation_id", "unit_id"),
            sa.CheckConstraint("votes >= 0"),
        ],
    )
    table(
        "turnout",
        integer("id", pk=True),
        text("event_id", fk="election_events.id"),
        text("unit_id", fk="geographic_units.id"),
        integer("ballots_cast", True),
        integer("registered_voters", True),
        sa.Column("percent", sa.Float(), nullable=True),
        text("definition"),
        text("source_id", fk="sources.id"),
        constraints=[sa.UniqueConstraint("event_id", "unit_id")],
    )
    table(
        "import_runs",
        integer("id", pk=True),
        text("contest_id", fk="contests.id"),
        text("created_at"),
        text("status"),
        sa.Column("report", sa.JSON(), nullable=False),
    )
    m.create_all(op.get_bind())


def downgrade():
    for name in [
        "import_runs",
        "turnout",
        "vote_results",
        "participations",
        "candidates",
        "parties",
        "contests",
        "geometries",
        "geographic_units",
        "boundary_versions",
        "sources",
        "election_events",
        "offices",
    ]:
        op.drop_table(name)
