"""Delete the media messages the bot promised to remove."""

import asyncio
import logging

from bot.config import settings
from bot.database.base import SessionLocal, retry_locked
from bot.database.repository import content as content_repo

log = logging.getLogger(__name__)


class DeletionService:
    def __init__(self, bot):
        self.bot = bot
        self._task = None

    async def start(self):
        if not settings.auto_delete_enabled or self._task is not None:
            return
        self._task = asyncio.create_task(self._loop())

    async def stop(self):
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    async def _loop(self):
        interval = max(15, settings.auto_delete_sweep_interval)
        while True:
            try:
                await self.sweep()
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception('auto-delete sweep failed')
            await asyncio.sleep(interval)

    async def sweep(self) -> int:
        removed = 0

        async def claim():
            async with SessionLocal() as session:
                entries = await content_repo.purge_tracked(session)
                await session.commit()
                return entries

        entries = await retry_locked(claim)
        for _id, chat_id, message_id in entries:
            try:
                await self.bot.delete_message(chat_id, message_id)
                removed += 1
            except Exception:
                pass
        return removed
