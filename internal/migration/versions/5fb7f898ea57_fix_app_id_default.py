"""fix_app_id_default

Revision ID: 5fb7f898ea57
Revises: b645089920cc
Create Date: 2026-06-07 23:44:27.605684

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5fb7f898ea57'
down_revision = 'b645089920cc'
branch_labels = None
depends_on = None


def upgrade():
    # 修复 app 表的 id 列默认值
    op.execute('ALTER TABLE app ALTER COLUMN id SET DEFAULT uuid_generate_v4()')
    # 修复 updated_at 和 created_at 的默认值
    op.execute('ALTER TABLE app ALTER COLUMN updated_at SET DEFAULT CURRENT_TIMESTAMP(0)')
    op.execute('ALTER TABLE app ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP(0)')


def downgrade():
    # 回滚：移除默认值
    op.execute('ALTER TABLE app ALTER COLUMN id DROP DEFAULT')
