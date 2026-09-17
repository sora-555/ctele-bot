"""Add expiring invite links and directional send permissions."""

from alembic import op
import sqlalchemy as sa

revision = '0003_friend_expiry_and_permissions'
down_revision = '0002_friend_system'
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    invite_columns = {column['name'] for column in inspector.get_columns('friend_invites')}
    if 'expires_at' not in invite_columns:
        op.add_column(
            'friend_invites',
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        )
        op.execute("UPDATE friend_invites SET expires_at = CURRENT_TIMESTAMP WHERE expires_at IS NULL")
        with op.batch_alter_table('friend_invites') as batch:
            batch.alter_column('expires_at', nullable=False)
        op.create_index('ix_friend_invites_expires_at', 'friend_invites', ['expires_at'], unique=False)

    friendship_columns = {column['name'] for column in inspector.get_columns('friendships')}
    if 'send_allowed' not in friendship_columns:
        op.add_column(
            'friendships',
            sa.Column('send_allowed', sa.Boolean(), server_default=sa.true(), nullable=False),
        )


def downgrade():
    inspector = sa.inspect(op.get_bind())
    if 'send_allowed' in {column['name'] for column in inspector.get_columns('friendships')}:
        op.drop_column('friendships', 'send_allowed')
    if 'expires_at' in {column['name'] for column in inspector.get_columns('friend_invites')}:
        op.drop_index('ix_friend_invites_expires_at', table_name='friend_invites')
        op.drop_column('friend_invites', 'expires_at')
