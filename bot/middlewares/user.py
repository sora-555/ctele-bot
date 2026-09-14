"""Registers/updates the user, counts activity, and enforces the gates.

Two gates live here so no handler can forget them:
* blocked users are stopped before any handler runs;
* the 18+ gate is enforced until the user accepts it.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from bot.config import Settings
from bot.database import repository as repo
from bot.texts import ui

log = logging.getLogger(__name__)

_NOTICE_COOLDOWN = 300.0


class UserMiddleware(BaseMiddleware):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._last_notice: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user = data.get("event_from_user")
        session = data.get("session")
        if tg_user is None or session is None or getattr(tg_user, "is_bot", False):
            return await handler(event, data)

        user, created = await repo.upsert(
            session,
            user_id=tg_user.id,
            username=tg_user.username,
            first_name=tg_user.first_name,
            last_name=tg_user.last_name,
            language_code=tg_user.language_code,
            is_premium=bool(getattr(tg_user, "is_premium", False)),
        )
        await repo.touch(session, tg_user.id)
        await repo.settings_for(session, tg_user.id)
        await repo.stats.touch(session, requests=1, new_users=1 if created else 0)
        # Commit the tracking writes *now*. Everything below may talk to Telegram, and
        # SQLite allows a single writer: holding this transaction open across a send
        # kept the write lock for the whole handler, so the auto-delete scheduler and
        # every other update failed with "database is locked".
        await session.commit()
        data["user"] = user
        data["user_created"] = created

        if created:
            log.info("new user %s (%s)", tg_user.id, tg_user.username or "-")

        if not user.is_active and not data.get("is_admin"):
            await self._notify_blocked(event, tg_user.id, user)
            return None

        if self._settings.age_gate and not user.age_verified and not data.get("is_admin"):
            if not self._is_age_flow(event):
                await self._notify_age(event)
                return None

        return await handler(event, data)

    # ------------------------------------------------------------------ helpers

    def _is_age_flow(self, event: TelegramObject) -> bool:
        if isinstance(event, Message) and event.text:
            return event.text.lstrip().lower().startswith("/start")
        if isinstance(event, CallbackQuery) and event.data:
            return event.data.startswith("age:")
        return False

    async def _notify_age(self, event: TelegramObject) -> None:
        if isinstance(event, Message):
            from bot.keyboards import inline

            await event.answer(ui.age_gate(), reply_markup=inline.age_gate())
        elif isinstance(event, CallbackQuery):
            await event.answer("Confirm your age first", show_alert=True)

    async def _notify_blocked(self, event: TelegramObject, user_id: int, user) -> None:
        if isinstance(event, CallbackQuery):
            await event.answer("Access restricted", show_alert=True)
            return
        now = time.monotonic()
        if now - self._last_notice.get(user_id, 0.0) < _NOTICE_COOLDOWN:
            return
        self._last_notice[user_id] = now
        if isinstance(event, Message):
            support = self._settings.admin_ids.split(",")[0].strip() if self._settings.admin_ids else "-"
            await event.answer(
                ui.blocked_notice(user.block_reason or "not specified", user.blocked_at, support or "-")
            )