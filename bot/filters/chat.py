"""Chat-type guards: this bot only answers in private chats."""

from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import Chat, TelegramObject


class PrivateOnly(BaseFilter):
    async def __call__(self, event: TelegramObject, **data) -> bool:
        chat: Chat | None = data.get("event_chat")
        return chat is None or chat.type == "private"