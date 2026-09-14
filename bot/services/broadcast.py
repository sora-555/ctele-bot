"""Rate-limited fan-out with live progress and cooperative cancellation."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

from aiogram.exceptions import (
    TelegramAPIError,
    TelegramForbiddenError,
    TelegramRetryAfter,
)

from bot.config import Settings

log = logging.getLogger(__name__)

ProgressHook = Callable[[int, int], Awaitable[None]]


class BroadcastService:
    def __init__(self, bot, settings: Settings) -> None:
        self._bot = bot
        self._settings = settings
        self._cancelled: set[int] = set()

    def cancel(self, broadcast_id: int) -> None:
        self._cancelled.add(broadcast_id)

    def is_cancelled(self, broadcast_id: int) -> bool:
        return broadcast_id in self._cancelled

    def clear(self, broadcast_id: int) -> None:
        self._cancelled.discard(broadcast_id)

    async def run(
        self,
        *,
        broadcast_id: int,
        recipients: list[int],
        text: str | None,
        photo: str | None = None,
        on_progress: ProgressHook | None = None,
    ) -> tuple[int, int, bool]:
        """Returns ``(sent, failed, cancelled)``."""
        rate = max(self._settings.broadcast_rate, 1)
        delay = 1.0 / rate
        sent = 0
        failed = 0
        total = len(recipients)
        last_report = 0.0

        loop = asyncio.get_running_loop()
        for index, chat_id in enumerate(recipients, start=1):
            if self.is_cancelled(broadcast_id):
                return sent, failed, True
            try:
                if photo:
                    await self._bot.send_photo(chat_id=chat_id, photo=photo, caption=text)
                else:
                    await self._bot.send_message(chat_id=chat_id, text=text or "")
                sent += 1
            except TelegramRetryAfter as exc:
                await asyncio.sleep(exc.retry_after + 0.5)
                try:
                    if photo:
                        await self._bot.send_photo(chat_id=chat_id, photo=photo, caption=text)
                    else:
                        await self._bot.send_message(chat_id=chat_id, text=text or "")
                    sent += 1
                except TelegramAPIError:
                    failed += 1
            except TelegramForbiddenError:
                failed += 1
            except TelegramAPIError as exc:
                failed += 1
                log.debug("broadcast to %s failed: %s", chat_id, exc)

            now = loop.time()
            if on_progress and (now - last_report >= 1.5 or index == total):
                last_report = now
                try:
                    await on_progress(sent, failed)
                except Exception:  # noqa: BLE001 - progress is best-effort
                    log.debug("broadcast progress hook failed", exc_info=True)
            await asyncio.sleep(delay)

        return sent, failed, False