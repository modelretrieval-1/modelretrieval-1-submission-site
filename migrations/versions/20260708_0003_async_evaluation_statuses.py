"""Include async evaluation statuses in the current-submission uniqueness index.

Revision ID: 20260708_0003
Revises: 20260706_0002
Create Date: 2026-07-08
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260708_0003"
down_revision: str | None = "20260706_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# The queued/processing in-flight states must reserve the "one current successful
# submission per (team, subtask, period)" slot so a team cannot enqueue several
# files at once while evaluation is pending.
NEW_STATUS_SQL = (
    "status IN ('accepted', 'queued', 'processing', 'evaluated', 'evaluation_failed') "
    "AND is_current = 1"
)
OLD_STATUS_SQL = (
    "status IN ('accepted', 'evaluated', 'evaluation_failed') AND is_current = 1"
)


def upgrade() -> None:
    op.drop_index("idx_one_current_successful_submission", table_name="submissions")
    op.create_index(
        "idx_one_current_successful_submission",
        "submissions",
        ["team_id", "subtask", "submission_period_id"],
        unique=True,
        sqlite_where=sa.text(NEW_STATUS_SQL),
    )


def downgrade() -> None:
    op.drop_index("idx_one_current_successful_submission", table_name="submissions")
    op.create_index(
        "idx_one_current_successful_submission",
        "submissions",
        ["team_id", "subtask", "submission_period_id"],
        unique=True,
        sqlite_where=sa.text(OLD_STATUS_SQL),
    )
