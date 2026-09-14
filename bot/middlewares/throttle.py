"""Per-user anti-flood bucket. Admins are exempt."""

from __future__ import annotations

import time
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from bot.config import Settings
from bot.texts import ui


class ThrottleMiddleware(BaseMiddleware):
    def __init__(self, settings: Settings) -> None:
        self._rate = max(settings.throttle_rate, 1)
        self._period = max(settings.throttle_period, 1.0)
        self._hits: dict[int, list[float]] = {}
        self._warned: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if data.get("is_admin"):
            return await handler(event, data)

        tg_user = data.get("event_from_user")
        if tg_user is None:
            return await handler(event, data)

        now = time.monotonic()
        hits = [stamp for stamp in self._hits.get(tg_user.id, []) if now - stamp < self._period]
        if len(hits) >= self._rate:
            if now - self._warned.get(tg_user.id, 0.0) > self._period:
                self._warned[tg_user.id] = now
                await self._warn(event)
            return None

        hits.append(now)
        self._hits[tg_user.id] = hits
        if len(self._hits) > 5000:
            self._hits = {uid: stamps for uid, stamps in self._hits.items() if stamps and now - stamps[-1] < self._period}
        return await handler(event, data)

    async def _warn(self, event: TelegramObject) -> None:
        if isinstance(event, CallbackQuery):
            await event.answer("Slow down", show_alert=False)
        elif isinstance(event, Message):
            await event.answer(ui.rate_limited(self._rate, self._period))