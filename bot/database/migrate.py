"""Idempotent schema top-ups for databases created by an older build.

create_all() only creates missing tables, so columns added later are applied
here with plain ALTER TABLE statements guarded by PRAGMA table_info.
"""

from sqlalchemy import text

from bot.database.base import engine

COLUMNS = [
    ('users', 'language_code', 'VARCHAR(12)'),
    ('users', 'last_action', 'VARCHAR(24)'),
    ('users', 'bot_blocked', 'BOOLEAN NOT NULL DEFAULT 0'),
    ('users', 'blocked_at', 'DATETIME'),
    ('users', 'blocked_by', 'BIGINT'),
    ('users', 'blocked_reason', 'VARCHAR(255)'),
    ('user_settings', 'show_thumbnails', 'BOOLEAN NOT NULL DEFAULT 1'),
    ('user_settings', 'numbered_nav', 'BOOLEAN NOT NULL DEFAULT 1'),
    ('user_settings', 'auto_delete_minutes', 'INTEGER'),
    ('user_settings', 'favorites_tab', "VARCHAR(12) DEFAULT 'posts'"),
]

INDEXES = [
    'CREATE INDEX IF NOT EXISTS ix_users_username ON users (username)',
    'CREATE INDEX IF NOT EXISTS ix_users_last_seen_at ON users (last_seen_at)',
]


async def _columns(conn, table: str) -> set[str]:
    rows = (await conn.execute(text(f'PRAGMA table_info({table})'))).all()
    return {row[1] for row in rows}


async def run_migrations():
    async with engine.begin() as conn:
        for table, column, ddl in COLUMNS:
            if column not in await _columns(conn, table):
                await conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {column} {ddl}'))
        for statement in INDEXES:
            await conn.execute(text(statement))


async def backfill_users(session):
    """Give orphan favourite/history rows a user record so foreign keys hold."""
    for table in ('favorites', 'history'):
        await session.execute(
            text(
                f'INSERT INTO users (id, is_active, bot_blocked, age_verified, request_count, created_at, last_seen_at) '
                f'SELECT DISTINCT user_id, 1, 0, 0, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP FROM {table} '
                f'WHERE user_id NOT IN (SELECT id FROM users)'
            )
        )
    await session.commit()
