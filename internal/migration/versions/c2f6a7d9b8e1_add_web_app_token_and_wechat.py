"""add web app token and wechat tables

Revision ID: c2f6a7d9b8e1
Revises: faf78e29c801
Create Date: 2026-07-06 23:12:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c2f6a7d9b8e1"
down_revision = "faf78e29c801"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("app", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "token",
                sa.String(length=255),
                server_default=sa.text("''::character varying"),
                nullable=True,
            )
        )
        batch_op.create_index("app_token_idx", ["token"], unique=False)

    op.create_table(
        "wechat_config",
        sa.Column("id", sa.UUID(), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("app_id", sa.UUID(), nullable=False),
        sa.Column(
            "wechat_app_id",
            sa.String(length=255),
            server_default=sa.text("''::character varying"),
            nullable=True,
        ),
        sa.Column(
            "wechat_app_secret",
            sa.String(length=255),
            server_default=sa.text("''::character varying"),
            nullable=True,
        ),
        sa.Column(
            "wechat_token",
            sa.String(length=255),
            server_default=sa.text("''::character varying"),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.String(length=255),
            server_default=sa.text("''::character varying"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP(0)"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP(0)"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_wechat_config_id"),
    )
    with op.batch_alter_table("wechat_config", schema=None) as batch_op:
        batch_op.create_index("wechat_config_app_id_idx", ["app_id"], unique=False)

    op.create_table(
        "wechat_end_user",
        sa.Column("id", sa.UUID(), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("openid", sa.String(), nullable=False),
        sa.Column("app_id", sa.UUID(), nullable=False),
        sa.Column("end_user_id", sa.UUID(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP(0)"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP(0)"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_wechat_end_user_id"),
    )
    with op.batch_alter_table("wechat_end_user", schema=None) as batch_op:
        batch_op.create_index("wechat_end_user_openid_app_id_idx", ["openid", "app_id"], unique=False)

    op.create_table(
        "wechat_message",
        sa.Column("id", sa.UUID(), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("wechat_end_user_id", sa.UUID(), nullable=False),
        sa.Column("message_id", sa.UUID(), nullable=False),
        sa.Column("is_pushed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP(0)"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP(0)"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_wechat_message_id"),
    )
    with op.batch_alter_table("wechat_message", schema=None) as batch_op:
        batch_op.create_index("wechat_message_wechat_end_user_id_idx", ["wechat_end_user_id"], unique=False)


def downgrade():
    with op.batch_alter_table("wechat_message", schema=None) as batch_op:
        batch_op.drop_index("wechat_message_wechat_end_user_id_idx")
    op.drop_table("wechat_message")

    with op.batch_alter_table("wechat_end_user", schema=None) as batch_op:
        batch_op.drop_index("wechat_end_user_openid_app_id_idx")
    op.drop_table("wechat_end_user")

    with op.batch_alter_table("wechat_config", schema=None) as batch_op:
        batch_op.drop_index("wechat_config_app_id_idx")
    op.drop_table("wechat_config")

    with op.batch_alter_table("app", schema=None) as batch_op:
        batch_op.drop_index("app_token_idx")
        batch_op.drop_column("token")
