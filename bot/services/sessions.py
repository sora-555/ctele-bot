import asyncio
import os
import pickle
import secrets
import sqlite3
import time
from dataclasses import dataclass

from bot.config import settings


@dataclass
class Session:
    user_id: int
    data: dict
    expires: float


class SessionStore:
    def __init__(self, ttl=1800, database_path="Database.db"):
        self.ttl = ttl
        self.database_path = database_path
        self._locks = {}
        self._connection = sqlite3.connect(
            self.database_path,
            check_same_thread=False,
            timeout=30,
        )
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS bot_sessions (
                sid TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                payload BLOB NOT NULL,
                expires REAL NOT NULL
            )
            """
        )
        self._connection.commit()

    def create(self, user_id, data):
        sid = secrets.token_urlsafe(6)
        expires = time.time() + self.ttl
        payload = sqlite3.Binary(pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL))
        self._connection.execute(
            "INSERT INTO bot_sessions (sid, user_id, payload, expires) VALUES (?, ?, ?, ?)",
            (sid, user_id, payload, expires),
        )
        self._connection.commit()
        self._locks[sid] = asyncio.Lock()
        return sid

    def get(self, sid, user_id):
        row = self._connection.execute(
            "SELECT user_id, payload, expires FROM bot_sessions WHERE sid = ?",
            (sid,),
        ).fetchone()
        now = time.time()
        if not row or row[0] != user_id or row[2] < now:
            if row and row[2] < now:
                self._connection.execute("DELETE FROM bot_sessions WHERE sid = ?", (sid,))
                self._connection.commit()
            return None

        expires = now + self.ttl
        self._connection.execute(
            "UPDATE bot_sessions SET expires = ? WHERE sid = ?",
            (expires, sid),
        )
        self._connection.commit()
        return pickle.loads(row[1])

    def update(self, sid, data):
        payload = sqlite3.Binary(pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL))
        result = self._connection.execute(
            """
            UPDATE bot_sessions
            SET payload = ?, expires = ?
            WHERE sid = ? AND expires >= ?
            """,
            (payload, time.time() + self.ttl, sid, time.time()),
        )
        self._connection.commit()
        return result.rowcount == 1

    def lock(self, sid):
        return self._locks.setdefault(sid, asyncio.Lock())


store = SessionStore(ttl=settings.session_ttl)
