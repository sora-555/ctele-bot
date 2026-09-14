"""Role filters. Middleware data is available as filter kwargs."""

from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import TelegramObject

from bot.database.models import ROLE_RANK


class IsAdmin(BaseFilter):
    async def __call__(self, event: TelegramObject, **data) -> bool:
        return bool(data.get("is_admin"))


class IsOwner(BaseFilter):
    async def __call__(self, event: TelegramObject, **data) -> bool:
        return bool(data.get("is_owner"))


class RoleAtLeast(BaseFilter):
    def __init__(self, role: str) -> None:
        self._rank = ROLE_RANK.get(role, 0)

    async def __call__(self, event: TelegramObject, **data) -> bool:
        role = data.get("role")
        return bool(role) and ROLE_RANK.get(role, 0) >= self._rank