"""Repair stale evaluation lifecycle summaries.

Revision ID: 20261014_0004
Revises: 20260708_0003
Create Date: 2026-10-14
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "20261014_0004"
down_revision: str | None = "20260708_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE submissions
        SET validation_summary = CASE status
            WHEN 'evaluated' THEN 'Evaluated.'
            WHEN 'processing' THEN 'Evaluating.'
        END
        WHERE status IN ('evaluated', 'processing')
          AND validation_summary IN ('Queued for evaluation.', 'Preparing for evaluation.')
        """
    )


def downgrade() -> None:
    # Data repair is intentionally retained: the original stale wording cannot
    # be recovered, and restoring it would make lifecycle summaries inaccurate.
    pass
