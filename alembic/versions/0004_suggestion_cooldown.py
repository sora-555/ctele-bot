"""Store the last user suggestion time for cooldown enforcement."""

from alembic import op
import sqlalchemy as sa

revision = '0004_suggestion_cooldown'
down_revision = '0003_friend_expiry_and_permissions'
branch_labels = None
depends_on = None


def upgrade():
    columns = {column['name'] for column in sa.inspect(op.get_bind()).get_columns('users')}
    if 'suggestion_last_at' not in columns:
        op.add_column('users', sa.Column('suggestion_last_at', sa.DateTime(timezone=True), nullable=True))


def downgrade():
    columns = {column['name'] for column in sa.inspect(op.get_bind()).get_columns('users')}
    if 'suggestion_last_at' in columns:
        op.drop_column('users', 'suggestion_last_at')
