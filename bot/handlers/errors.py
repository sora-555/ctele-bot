import logging

from aiogram.types import CallbackQuery, ErrorEvent, Message

from bot.config import settings
from bot.middlewares.user import inner_event
from bot.texts import ui

log = logging.getLogger(__name__)


async def handle_error(event: ErrorEvent, bot=None, **_kwargs):
    update = event.update
    log.error('unhandled error in update %s', getattr(update, 'update_id', None), exc_info=event.exception)
    target = inner_event(update)
    try:
        if isinstance(target, CallbackQuery):
            await target.answer('Something went wrong. Please try again.', show_alert=True)
        elif isinstance(target, Message):
            await target.answer(ui.notice('Something went wrong', 'Please try again, or open /menu.'))
    except Exception:
        pass
    channel = settings.log_channel
    if bot is None or channel is None:
        return
    try:
        await bot.send_message(
            channel,
            ui.screen('Bot error', ui.bullet(ui.safe(str(event.exception))[:350])),
        )
    except Exception:
        pass
