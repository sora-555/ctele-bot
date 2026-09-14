"""Async engine, session factory and schema bootstrap.

The engine is created lazily so importing the package never opens a file
handle - `start.py` decides when the database comes to life.
"""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from bot.config import get_settings

log = logging.getLogger(__name__)

SCHEMA_VERSION = "1"

# How long SQLite may wait for a lock before giving up, in seconds/milliseconds.
SQLITE_BUSY_TIMEOUT = 15
SQLITE_BUSY_TIMEOUT_MS = SQLITE_BUSY_TIMEOUT * 1000

_LOCK_MARKERS = ("database is locked", "database table is locked", "database schema is locked")


class Base(DeclarativeBase):
    """Declarative base for every ORM model."""


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        settings = get_settings()
        is_sqlite = settings.database_url.startswith("sqlite")
        _engine = create_async_engine(
            settings.database_url,
            echo=False,
            future=True,
            # The driver-level timeout is what makes SQLite wait for a busy database
            # instead of failing immediately; it must cover our slowest transaction.
            connect_args={"timeout": SQLITE_BUSY_TIMEOUT} if is_sqlite else {},
        )
        if is_sqlite:
            _install_sqlite_pragmas(_engine)
    return _engine


def _install_sqlite_pragmas(engine: AsyncEngine) -> None:
    """WAL + a patient busy timeout.

    WAL lets readers run while a writer is committing - without it every read
    blocks on the writer and vice versa. `busy_timeout` is a per-connection
    setting, so it is re-applied on every checkout; `synchronous=NORMAL` is the
    WAL-appropriate durability trade-off and shortens the write lock.
    """

    @event.listens_for(engine.sync_engine, "connect")
    def _on_connect(dbapi_connection, _record):  # pragma: no cover - driver hook
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS}")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA foreign_keys=ON")
        finally:
            cursor.close()


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(), expire_on_commit=False, class_=AsyncSession
        )
    return _session_factory


def is_lock_error(exc: BaseException) -> bool:
    """True when SQLite refused a write because another connection held the lock."""
    for error in (exc, getattr(exc, "orig", None)):
        if error is None:
            continue
        message = str(error).lower()
        if any(marker in message for marker in _LOCK_MARKERS):
            return True
    return False


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """A self-managing session for background tasks and services."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Create the schema and seed the ``meta`` table."""
    from bot.database import models

    engine = get_engine()
    log.debug("schema tables: %s", ", ".join(sorted(models.Base.metadata.tables)))
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    await seed_meta()


async def seed_meta() -> None:
    from bot.database.models import Meta

    settings = get_settings()
    async with session_scope() as session:
        existing = {
            row.key for row in (await session.execute(select(Meta))).scalars().all()
        }
        defaults = {
            "schema_version": SCHEMA_VERSION,
            "maintenance": "true" if settings.maintenance else "false",
        }
        for key, value in defaults.items():
            if key not in existing:
                session.add(Meta(key=key, value=value))


async def dispose_db() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


def sqlite_path() -> str | None:
    url = get_settings().database_url
    if not url.startswith("sqlite"):
        return None
    tail = url.split("///", 1)[-1]
    return tail or None


def database_size_bytes() -> int:
    path = sqlite_path()
    if not path:
        return 0
    try:
        return os.path.getsize(path)
    except OSError:
        return 0