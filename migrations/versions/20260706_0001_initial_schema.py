"""Initial schema.

Revision ID: 20260706_0001
Revises: None
Create Date: 2026-07-06
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260706_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "organizers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("username", sa.Text(), nullable=False, unique=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at", sa.Text(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column(
            "updated_at", sa.Text(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column("last_login_at", sa.Text()),
    )
    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("team_id", sa.Text(), nullable=False, unique=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by_organizer_id", sa.Integer()),
        sa.Column(
            "created_at", sa.Text(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column(
            "updated_at", sa.Text(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column("last_login_at", sa.Text()),
        sa.ForeignKeyConstraint(["created_by_organizer_id"], ["organizers.id"]),
    )
    op.create_table(
        "team_subtasks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("subtask", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.Text(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.CheckConstraint("subtask IN ('A', 'B')"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
        sa.UniqueConstraint("team_id", "subtask"),
    )
    op.create_table(
        "submission_periods",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.Text(), nullable=False, unique=True),
        sa.Column("starts_at_jst", sa.Text()),
        sa.Column("deadline_at_jst", sa.Text(), nullable=False),
        sa.Column("is_open_override", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.Text(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column(
            "updated_at", sa.Text(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
    )
    op.create_table(
        "ground_truth_versions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("subtask", sa.Text(), nullable=False),
        sa.Column("version_label", sa.Text(), nullable=False),
        sa.Column("stored_file_path", sa.Text(), nullable=False),
        sa.Column("file_sha256", sa.Text(), nullable=False),
        sa.Column("uploaded_by_organizer_id", sa.Integer(), nullable=False),
        sa.Column("uploaded_at_jst", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("validation_status", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.CheckConstraint("subtask IN ('A', 'B')"),
        sa.ForeignKeyConstraint(["uploaded_by_organizer_id"], ["organizers.id"]),
    )
    op.create_table(
        "submissions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("subtask", sa.Text(), nullable=False),
        sa.Column("submission_period_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("original_filename", sa.Text(), nullable=False),
        sa.Column("stored_file_path", sa.Text()),
        sa.Column("file_sha256", sa.Text()),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("submitted_at_jst", sa.Text(), nullable=False),
        sa.Column("validation_summary", sa.Text()),
        sa.Column("ground_truth_version_id", sa.Integer()),
        sa.CheckConstraint("subtask IN ('A', 'B')"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
        sa.ForeignKeyConstraint(["submission_period_id"], ["submission_periods.id"]),
        sa.ForeignKeyConstraint(["ground_truth_version_id"], ["ground_truth_versions.id"]),
    )
    op.create_index(
        "idx_one_successful_submission",
        "submissions",
        ["team_id", "subtask", "submission_period_id"],
        unique=True,
        sqlite_where=sa.text("status IN ('accepted', 'evaluated', 'evaluation_failed')"),
    )
    op.create_table(
        "runs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("submission_id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Text(), nullable=False),
        sa.Column("line_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("query_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.Text(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.ForeignKeyConstraint(["submission_id"], ["submissions.id"]),
        sa.UniqueConstraint("submission_id", "run_id"),
    )
    op.create_table(
        "validation_errors",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("submission_id", sa.Integer(), nullable=False),
        sa.Column("line_number", sa.Integer()),
        sa.Column("field_name", sa.Text()),
        sa.Column("error_code", sa.Text(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False, server_default="error"),
        sa.Column(
            "created_at", sa.Text(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.ForeignKeyConstraint(["submission_id"], ["submissions.id"]),
    )
    op.create_table(
        "evaluation_results",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("submission_id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("ground_truth_version_id", sa.Integer(), nullable=False),
        sa.Column("metric_name", sa.Text(), nullable=False),
        sa.Column("metric_value", sa.REAL(), nullable=False),
        sa.Column("created_at_jst", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["submission_id"], ["submissions.id"]),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"]),
        sa.ForeignKeyConstraint(["ground_truth_version_id"], ["ground_truth_versions.id"]),
    )
    op.create_table(
        "evaluation_query_results",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("submission_id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("ground_truth_version_id", sa.Integer(), nullable=False),
        sa.Column("topic_id", sa.Text(), nullable=False),
        sa.Column("metric_name", sa.Text(), nullable=False),
        sa.Column("metric_value", sa.REAL(), nullable=False),
        sa.Column("created_at_jst", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["submission_id"], ["submissions.id"]),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"]),
        sa.ForeignKeyConstraint(["ground_truth_version_id"], ["ground_truth_versions.id"]),
    )
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("actor_type", sa.Text(), nullable=False),
        sa.Column("actor_id", sa.Integer()),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.Text()),
        sa.Column("entity_id", sa.Integer()),
        sa.Column("metadata_json", sa.Text()),
        sa.Column("created_at_jst", sa.Text(), nullable=False),
    )
    op.bulk_insert(
        sa.table(
            "submission_periods",
            sa.column("name", sa.Text()),
            sa.column("starts_at_jst", sa.Text()),
            sa.column("deadline_at_jst", sa.Text()),
        ),
        [
            {"name": "normal", "starts_at_jst": None, "deadline_at_jst": "2026-08-01 15:00:00"},
            {"name": "late", "starts_at_jst": None, "deadline_at_jst": "2026-10-15 23:59:00"},
        ],
    )


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("evaluation_query_results")
    op.drop_table("evaluation_results")
    op.drop_table("validation_errors")
    op.drop_table("runs")
    op.drop_index("idx_one_successful_submission", table_name="submissions")
    op.drop_table("submissions")
    op.drop_table("ground_truth_versions")
    op.drop_table("submission_periods")
    op.drop_table("team_subtasks")
    op.drop_table("teams")
    op.drop_table("organizers")
