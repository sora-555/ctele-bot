"""Add durable friend invites, requests, and friendships."""

from alembic import op
import sqlalchemy as sa

revision = '0002_friend_system'
down_revision = '0001_baseline'
branch_labels = None
depends_on = None


def _has_table(name):
    return sa.inspect(op.get_bind()).has_table(name)


def upgrade():
    # A fresh database is completed by init_db(); this revision only needs
    # to create friend tables when the legacy users table already exists.
    if not _has_table('users'):
        return
    if not _has_table('friend_invites'):
        op.create_table(
            'friend_invites',
            sa.Column('owner_id', sa.BigInteger(), nullable=False),
            sa.Column('token', sa.String(length=64), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(['owner_id'], ['users.id']),
            sa.PrimaryKeyConstraint('owner_id'),
            sa.UniqueConstraint('token'),
        )
        op.create_index('ix_friend_invites_token', 'friend_invites', ['token'], unique=False)
    if not _has_table('friend_requests'):
        op.create_table(
            'friend_requests',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('sender_id', sa.BigInteger(), nullable=False),
            sa.Column('receiver_id', sa.BigInteger(), nullable=False),
            sa.Column('status', sa.String(length=12), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(['receiver_id'], ['users.id']),
            sa.ForeignKeyConstraint(['sender_id'], ['users.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('sender_id', 'receiver_id'),
        )
        op.create_index('ix_friend_requests_sender_id', 'friend_requests', ['sender_id'], unique=False)
        op.create_index('ix_friend_requests_receiver_id', 'friend_requests', ['receiver_id'], unique=False)
        op.create_index('ix_friend_requests_status', 'friend_requests', ['status'], unique=False)
    if not _has_table('friendships'):
        op.create_table(
            'friendships',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.BigInteger(), nullable=False),
            sa.Column('friend_id', sa.BigInteger(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(['friend_id'], ['users.id']),
            sa.ForeignKeyConstraint(['user_id'], ['users.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('user_id', 'friend_id'),
        )
        op.create_index('ix_friendships_user_id', 'friendships', ['user_id'], unique=False)
        op.create_index('ix_friendships_friend_id', 'friendships', ['friend_id'], unique=False)


def downgrade():
    if _has_table('friendships'):
        op.drop_index('ix_friendships_friend_id', table_name='friendships')
        op.drop_index('ix_friendships_user_id', table_name='friendships')
        op.drop_table('friendships')
    if _has_table('friend_requests'):
        op.drop_index('ix_friend_requests_status', table_name='friend_requests')
        op.drop_index('ix_friend_requests_receiver_id', table_name='friend_requests')
        op.drop_index('ix_friend_requests_sender_id', table_name='friend_requests')
        op.drop_table('friend_requests')
    if _has_table('friend_invites'):
        op.drop_index('ix_friend_invites_token', table_name='friend_invites')
        op.drop_table('friend_invites')
