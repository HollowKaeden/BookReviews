"""rating: float, range 0-5

Revision ID: b3e7f9a2c015
Revises: 6103c93a5132
Create Date: 2026-07-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "b3e7f9a2c015"
down_revision = "6103c93a5132"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_reviews_rating_range", "reviews", type_="check")
    op.alter_column(
        "reviews",
        "rating",
        existing_type=sa.Integer(),
        type_=sa.Float(),
        existing_nullable=False,
    )
    op.create_check_constraint(
        "ck_reviews_rating_range",
        "reviews",
        "rating >= 0 AND rating <= 5",
    )


def downgrade() -> None:
    op.drop_constraint("ck_reviews_rating_range", "reviews", type_="check")
    op.alter_column(
        "reviews",
        "rating",
        existing_type=sa.Float(),
        type_=sa.Integer(),
        existing_nullable=False,
    )
    op.create_check_constraint(
        "ck_reviews_rating_range",
        "reviews",
        "rating >= 1 AND rating <= 5",
    )
