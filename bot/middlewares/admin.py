"""Resolves the caller's admin role before anything else needs it."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from bot.database import repository as repo
from bot.database.models import ROLE_OWNER


class AdminMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        data["role"] = None
        data["is_admin"] = False
        data["is_owner"] = False

        tg_user = data.get("event_from_user")
        session = data.get("session")
        if tg_user is not None and session is not None:
            role = await repo.get_role(session, tg_user.id)
            data["role"] = role
            data["is_admin"] = role is not None
            data["is_owner"] = role == ROLE_OWNER
        return await handler(event, data)