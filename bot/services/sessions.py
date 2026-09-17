"""Navigation sessions for the viewer.

Sessions live in the same table as before, but they are written through the
database session that belongs to the current update. Previously this module
kept its own blocking ``sqlite3`` connection: the update transaction held the
SQLite write lock while the handler called into that second connection, which
blocked the event loop and deadlocked until ``busy_timeout`` expired with
"database is locked".
"""

import asyncio
import pickle
import secrets
import time

from sqlalchemy import delete, select

from bot.config import settings
from bot.database.models import BotSession


class SessionStore:
    def __init__(self, ttl=1800):
        self.ttl = ttl
        self._locks: dict[str, asyncio.Lock] = {}

    def lock(self, sid: str) -> asyncio.Lock:
        """Serialise concurrent updates of the same screen."""
        return self._locks.setdefault(sid, asyncio.Lock())

    async def create(self, db, user_id: int, data: dict) -> str:
        sid = secrets.token_urlsafe(6)
        db.add(
            BotSession(
                sid=sid,
                user_id=user_id,
                payload=self._dump(data),
                expires=time.time() + self.ttl,
            )
        )
        await db.flush()
        self._locks[sid] = asyncio.Lock()
        return sid

    async def get(self, db, sid: str, user_id: int):
        row = await db.get(BotSession, sid)
        now = time.time()
        if row is None or row.user_id != user_id or row.expires < now:
            if row is not None and row.expires < now:
                await db.delete(row)
                await db.flush()
            return None
        row.expires = now + self.ttl
        await db.flush()
        return self._load(row.payload)

    async def update(self, db, sid: str, data: dict) -> bool:
        row = await db.get(BotSession, sid)
        if row is None or row.expires < time.time():
            return False
        row.payload = self._dump(data)
        row.expires = time.time() + self.ttl
        await db.flush()
        return True

    async def alive_ids(self, db) -> set[str]:
        return set(await db.scalars(select(BotSession.sid)))

    def prune_locks(self, alive: set[str]) -> None:
        for sid in list(self._locks):
            if sid not in alive:
                self._locks.pop(sid, None)

    @staticmethod
    def _dump(data: dict) -> bytes:
        return pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)

    @staticmethod
    def _load(payload) -> dict:
        return pickle.loads(payload if isinstance(payload, bytes) else bytes(payload))


async def sweep_expired(db) -> int:
    """Drop expired sessions; the caller commits."""
    result = await db.execute(delete(BotSession).where(BotSession.expires < time.time()))
    return result.rowcount or 0


store = SessionStore(ttl=settings.session_ttl)
