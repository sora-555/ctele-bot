"""Short-lived server-side state for callback buttons.

Telegram caps `callback_data` at 64 bytes, so buttons carry a short session id
and the real payload lives here. Every payload records its owner so one user can
never drive another user's buttons.
"""

from __future__ import annotations

import secrets
import string
import time

_ALPHABET = string.ascii_lowercase + string.digits


class SessionStore:
    def __init__(self, ttl_seconds: int = 1800, max_entries: int = 2000) -> None:
        self._ttl = ttl_seconds
        self._max = max_entries
        self._data: dict[str, tuple[float, dict]] = {}

    def new(self, payload: dict) -> str:
        self._prune()
        sid = "".join(secrets.choice(_ALPHABET) for _ in range(6))
        while sid in self._data:
            sid = "".join(secrets.choice(_ALPHABET) for _ in range(6))
        self._data[sid] = (time.monotonic(), payload)
        return sid

    def get(self, sid: str, *, user_id: int | None = None) -> dict | None:
        entry = self._data.get(sid)
        if entry is None:
            return None
        stored_at, payload = entry
        if time.monotonic() - stored_at > self._ttl:
            self._data.pop(sid, None)
            return None
        if user_id is not None and payload.get("user_id") not in (None, user_id):
            return None
        self._data[sid] = (time.monotonic(), payload)
        return payload

    def update(self, sid: str, **changes) -> dict | None:
        entry = self._data.get(sid)
        if entry is None:
            return None
        stored_at, payload = entry
        payload.update(changes)
        self._data[sid] = (stored_at, payload)
        return payload

    def drop(self, sid: str) -> None:
        self._data.pop(sid, None)

    def count(self) -> int:
        self._prune()
        return len(self._data)

    def _prune(self) -> None:
        now = time.monotonic()
        stale = [sid for sid, (stored_at, _) in self._data.items() if now - stored_at > self._ttl]
        for sid in stale:
            self._data.pop(sid, None)
        if len(self._data) > self._max:
            ordered = sorted(self._data.items(), key=lambda kv: kv[1][0])
            for sid, _ in ordered[: len(self._data) - self._max]:
                self._data.pop(sid, None)