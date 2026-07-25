"""Add commit_sha, github_review_id, and unique constraint on (pull_request_id, commit_sha) to reviews table

Revision ID: a4b8c9d1e2f3
Revises: 36503757ec9f
Create Date: 2026-07-25 10:55:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a4b8c9d1e2f3"
down_revision: Union[str, Sequence[str], None] = "36503757ec9f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("reviews", sa.Column("commit_sha", sa.String(), nullable=True))
    op.add_column("reviews", sa.Column("github_review_id", sa.String(), nullable=True))
    op.create_index(
        op.f("ix_reviews_commit_sha"), "reviews", ["commit_sha"], unique=False
    )
    op.create_unique_constraint(
        "uq_reviews_pull_request_commit_sha",
        "reviews",
        ["pull_request_id", "commit_sha"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("uq_reviews_pull_request_commit_sha", "reviews", type_="unique")
    op.drop_index(op.f("ix_reviews_commit_sha"), table_name="reviews")
    op.drop_column("reviews", "github_review_id")
    op.drop_column("reviews", "commit_sha")
