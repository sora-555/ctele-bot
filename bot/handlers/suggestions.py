from datetime import datetime, timedelta, timezone
import logging

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from bot.config import settings
from bot.texts import ui

log = logging.getLogger(__name__)
router = Router()
COOLDOWN = timedelta(minutes=10)


def _utc(value):
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _sender_label(user) -> str:
    name = ui.safe(user.display_name or 'unknown')
    username = f"@{ui.safe(user.username)}" if user.username else 'not set'
    return f"{name} {ui.kv('Username', username)} {ui.kv('ID', user.id)}"


@router.message(Command('suggestions', 'suuggestions'))
async def suggestions_command(message: Message, command: CommandObject, bot, db, user):
    now = datetime.now(timezone.utc)
    last = _utc(user.suggestion_last_at)
    if last is not None:
        remaining = COOLDOWN - (now - last)
        if remaining.total_seconds() > 0:
            minutes = max(1, int(remaining.total_seconds() // 60) + 1)
            return await message.answer(ui.suggestion_cooldown(minutes))

    text = (command.args or '').strip()
    replied = message.reply_to_message
    if not text and replied is None:
        return await message.answer(ui.suggestion_usage())

    header = ui.suggestion_admin_header(_sender_label(user))
    delivered = 0
    for admin_id in settings.admin_id_list:
        try:
            await bot.send_message(admin_id, header)
            if text:
                await bot.send_message(admin_id, ui.suggestion_content(text))
            else:
                await bot.forward_message(
                    chat_id=admin_id,
                    from_chat_id=message.chat.id,
                    message_id=replied.message_id,
                )
            delivered += 1
        except Exception:
            log.exception('could not deliver suggestion to admin %s', admin_id)

    if delivered == 0:
        return await message.answer(ui.suggestion_failed())
    user.suggestion_last_at = now
    await db.flush()
    await message.answer(ui.suggestion_sent())
