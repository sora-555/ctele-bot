"""Auto-deletion of media messages.

The bot never keeps a permanent copy of the source's images in a chat: every
image-bearing message it sends is scheduled for deletion (default 30 minutes)
and removed by a background sweeper. The schedule lives in SQLite so a restart
does not lose pending deletions.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from aiogram.exceptions import TelegramAPIError

from bot.config import Settings
from bot.database import repository as repo
from bot.database.base import is_lock_error, session_scope
from bot.utils.time import utcnow

log = logging.getLogger(__name__)

MAX_ATTEMPTS = 5

# Scheduling is idempotent (a message that is already queued is skipped), so a
# momentary SQLite lock can be retried instead of failing the screen the user
# is looking at.
LOCK_RETRIES = 4
LOCK_BACKOFF = 0.25


class DeletionService:
    def __init__(self, bot, settings: Settings) -> None:
        self._bot = bot
        self._settings = settings
        self._task: asyncio.Task | None = None
        self._stopping = asyncio.Event()
        self.last_sweep: tuple[int, int] | None = None

    @property
    def enabled(self) -> bool:
        return self._settings.auto_delete_enabled

    @property
    def ttl(self) -> timedelta:
        return timedelta(minutes=max(self._settings.auto_delete_ttl_minutes, 1))

    @property
    def ttl_label(self) -> str:
        minutes = max(self._settings.auto_delete_ttl_minutes, 1)
        if minutes >= 60 and minutes % 60 == 0:
            hours = minutes // 60
            return f"{hours} hour" + ("s" if hours != 1 else "")
        return f"{minutes} min"

    async def schedule(
        self,
        *,
        chat_id: int,
        message_ids: list[int],
        user_id: int | None,
        kind: str = "media",
    ) -> int:
        if not self.enabled or not message_ids:
            return 0
        return await self._write(
            chat_id,
            [int(message_id) for message_id in message_ids],
            user_id=user_id,
            kind=kind,
        )

    async def schedule_messages(self, messages, *, user_id: int | None, kind: str = "media") -> int:
        if not messages:
            return 0
        return await self.schedule(
            chat_id=messages[0].chat.id,
            message_ids=[message.message_id for message in messages],
            user_id=user_id,
            kind=kind,
        )

    async def _write(self, chat_id: int, message_ids: list[int], *, user_id: int | None, kind: str) -> int:
        """Queue the messages in a short transaction of its own, retrying a busy database."""
        last: BaseException | None = None
        for attempt in range(LOCK_RETRIES):
            try:
                async with session_scope() as session:
                    return await repo.schedule_deletions(
                        session,
                        chat_id=int(chat_id),
                        message_ids=message_ids,
                        user_id=user_id,
                        delete_at=utcnow() + self.ttl,
                        kind=kind,
                    )
            except Exception as exc:  # noqa: BLE001 - only lock contention is retried
                if not is_lock_error(exc):
                    raise
                last = exc
                log.warning(
                    "scheduling deletions hit a locked database, retrying (%s/%s)",
                    attempt + 1,
                    LOCK_RETRIES,
                )
                await asyncio.sleep(LOCK_BACKOFF * (attempt + 1))
        raise last if last is not None else RuntimeError("deletion scheduling failed")

    # ------------------------------------------------------------------ sweeper

    def start(self) -> None:
        if not self.enabled or self._task is not None:
            return
        self._stopping.clear()
        self._task = asyncio.create_task(self._run(), name="auto-delete-sweeper")
        log.info("auto-delete sweeper started (ttl=%s)", self.ttl_label)

    async def stop(self) -> None:
        self._stopping.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            except Exception:  # noqa: BLE001
                log.debug("sweeper shutdown raised", exc_info=True)
            self._task = None

    async def _run(self) -> None:
        interval = max(self._settings.auto_delete_sweep_interval, 15)
        while not self._stopping.is_set():
            try:
                await asyncio.wait_for(self._stopping.wait(), timeout=interval)
                return
            except asyncio.TimeoutError:
                pass
            try:
                await self.sweep_once()
            except Exception:  # noqa: BLE001 - the sweeper must never die
                log.exception("auto-delete sweep failed")

    async def sweep_once(self) -> tuple[int, int]:
        deleted = 0
        failed = 0
        done_ids: list[int] = []
        retry_ids: list[int] = []
        async with session_scope() as session:
            due = await repo.due_deletions(session)
            if not due:
                return 0, 0
            pending = [
                (row.id, row.chat_id, row.message_id, row.attempts) for row in due
            ]

        for row_id, chat_id, message_id, attempts in pending:
            if attempts >= MAX_ATTEMPTS:
                done_ids.append(row_id)
                continue
            try:
                await self._bot.delete_message(chat_id=chat_id, message_id=message_id)
                deleted += 1
                done_ids.append(row_id)
            except TelegramAPIError as exc:
                failed += 1
                retry_ids.append(row_id)
                log.debug("delete failed for %s/%s: %s", chat_id, message_id, exc)

        async with session_scope() as session:
            await repo.drop_deletions(session, done_ids)
            await repo.bump_deletion_attempts(session, retry_ids)

        self.last_sweep = (deleted, failed)
        if deleted:
            log.info("auto-deleted %s message(s)", deleted)
        return deleted, failed

    async def pending(self) -> int:
        async with session_scope() as session:
            return await repo.count_deletions(session)
