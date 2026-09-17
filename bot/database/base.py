import asyncio

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from bot.config import settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(settings.database_url, echo=False)


@event.listens_for(engine.sync_engine, "connect")
def _sqlite_pragmas(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=15000")
    cursor.close()


SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    from bot.database import models  # noqa: F401  (register the tables)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    from bot.database.migrate import backfill_users, run_migrations

    await run_migrations()
    async with SessionLocal() as session:
        await backfill_users(session)


async def retry_locked(operation, attempts: int = 4, delay: float = 0.5):
    """Run a short write, retrying while SQLite reports the database is locked.

    SQLite allows a single writer. Request handlers hold the write lock for the
    duration of their transaction, so background writers (broadcast, deletion)
    wait it out and retry instead of failing the whole batch.
    """
    from sqlalchemy.exc import OperationalError

    for attempt in range(attempts):
        try:
            return await operation()
        except OperationalError as exc:
            if 'locked' not in str(exc).lower() or attempt == attempts - 1:
                raise
            await asyncio.sleep(delay * (attempt + 1))
