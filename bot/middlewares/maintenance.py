"""Locks the bot to admins while maintenance mode is on."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from bot.loader import services
from bot.texts import ui


class MaintenanceMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not services().maintenance_enabled or data.get("is_admin"):
            return await handler(event, data)
        if isinstance(event, CallbackQuery):
            await event.answer("Maintenance in progress", show_alert=True)
        elif isinstance(event, Message):
            await event.answer(ui.maintenance_notice())
        return None