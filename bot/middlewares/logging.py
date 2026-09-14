"""Structured, low-noise update logging."""

from __future__ import annotations

import logging
import time
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

log = logging.getLogger("bot.updates")


class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        started = time.perf_counter()
        try:
            return await handler(event, data)
        finally:
            if log.isEnabledFor(logging.DEBUG):
                user = data.get("event_from_user")
                label = "-"
                if isinstance(event, Message) and event.text:
                    label = event.text[:40]
                elif isinstance(event, CallbackQuery) and event.data:
                    label = event.data[:40]
                log.debug(
                    "%s | user=%s | %s | %.0f ms",
                    type(event).__name__,
                    getattr(user, "id", "-"),
                    label,
                    (time.perf_counter() - started) * 1000,
                )