"""Add organizer-approved resubmission permissions.

Revision ID: 20260706_0002
Revises: 20260706_0001
Create Date: 2026-07-06
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260706_0002"
down_revision: str | None = "20260706_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


SUCCESSFUL_STATUS_SQL = "status IN ('accepted', 'evaluated', 'evaluation_failed')"


def upgrade() -> None:
    op.add_column(
        "submissions",
        sa.Column("is_current", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("submissions", sa.Column("superseded_at_jst", sa.Text()))
    op.add_column("submissions", sa.Column("superseded_by_submission_id", sa.Integer()))
    op.add_column("submissions", sa.Column("superseded_reason", sa.Text()))
    op.add_column("submissions", sa.Column("superseded_by_organizer_id", sa.Integer()))

    op.execute(
        f"""
        UPDATE submissions
        SET is_current = 1
        WHERE {SUCCESSFUL_STATUS_SQL}
        """
    )

    op.create_table(
        "resubmission_permissions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("subtask", sa.Text(), nullable=False),
        sa.Column("submission_period_id", sa.Integer(), nullable=False),
        sa.Column("granted_by_organizer_id", sa.Integer(), nullable=False),
        sa.Column("granted_at_jst", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text()),
        sa.Column("used_by_submission_id", sa.Integer()),
        sa.Column("used_at_jst", sa.Text()),
        sa.Column("is_used", sa.Integer(), nullable=False, server_default="0"),
        sa.CheckConstraint("subtask IN ('A', 'B')"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
        sa.ForeignKeyConstraint(["submission_period_id"], ["submission_periods.id"]),
        sa.ForeignKeyConstraint(["granted_by_organizer_id"], ["organizers.id"]),
        sa.ForeignKeyConstraint(["used_by_submission_id"], ["submissions.id"]),
    )
    op.create_index(
        "idx_unused_resubmission_permission",
        "resubmission_permissions",
        ["team_id", "subtask", "submission_period_id"],
        unique=True,
        sqlite_where=sa.text("is_used = 0"),
    )

    op.drop_index("idx_one_successful_submission", table_name="submissions")
    op.create_index(
        "idx_one_current_successful_submission",
        "submissions",
        ["team_id", "subtask", "submission_period_id"],
        unique=True,
        sqlite_where=sa.text(f"{SUCCESSFUL_STATUS_SQL} AND is_current = 1"),
    )


def downgrade() -> None:
    op.drop_index("idx_one_current_successful_submission", table_name="submissions")
    op.create_index(
        "idx_one_successful_submission",
        "submissions",
        ["team_id", "subtask", "submission_period_id"],
        unique=True,
        sqlite_where=sa.text(SUCCESSFUL_STATUS_SQL),
    )
    op.drop_index("idx_unused_resubmission_permission", table_name="resubmission_permissions")
    op.drop_table("resubmission_permissions")
    op.drop_column("submissions", "superseded_by_organizer_id")
    op.drop_column("submissions", "superseded_reason")
    op.drop_column("submissions", "superseded_by_submission_id")
    op.drop_column("submissions", "superseded_at_jst")
    op.drop_column("submissions", "is_current")
