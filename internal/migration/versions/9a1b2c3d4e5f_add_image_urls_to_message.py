"""add image_urls to message

Revision ID: 9a1b2c3d4e5f
Revises: e043c9d17a2b
Create Date: 2026-07-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "9a1b2c3d4e5f"
down_revision = "e043c9d17a2b"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("message", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "image_urls",
                postgresql.JSONB(astext_type=sa.Text()),
                server_default=sa.text("'[]'::jsonb"),
                nullable=False,
            )
        )


def downgrade():
    with op.batch_alter_table("message", schema=None) as batch_op:
        batch_op.drop_column("image_urls")
