"""Global error handler: log, tell the user, mirror to the log channel."""

from __future__ import annotations

import logging

from aiogram import Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import ErrorEvent

from bot.handlers.common import mirror_error
from bot.services.ctele_service import SourceError
from bot.texts import ui

log = logging.getLogger(__name__)
router = Router(name="errors")


def _where(event: ErrorEvent) -> str:
    update = event.update
    if update.callback_query:
        return f"callback {update.callback_query.data or '-'}"
    if update.message:
        text = (update.message.text or "").strip()
        return f"message {text[:40]}" if text else "message"
    return "update"


def _user_id(event: ErrorEvent) -> int | None:
    update = event.update
    for source in (update.message, update.callback_query):
        if source is not None and source.from_user is not None:
            return source.from_user.id
    return None


@router.errors()
async def handle_error(event: ErrorEvent, bot) -> None:
    exception = event.exception
    if isinstance(exception, SourceError):
        log.warning("source error: %s", exception)
        text = ui.source_unavailable(str(exception))
    else:
        log.exception("unhandled error", exc_info=exception)
        text = (
            f"{ui.IMPORTANT} 𝗦𝗼𝗺𝗲𝘁𝗵𝗶𝗻𝗴 𝗪𝗲𝗻𝘁 𝗪𝗿𝗼𝗻𝗴\n\n{ui.SEPARATOR}\n\n"
            "That action could not be completed.\n\n"
            f"{ui.ITEM} Type {ui.KV} {type(exception).__name__}\n"
            f"{ui.ITEM} Try {ui.KV} /menu\n\n{ui.SEPARATOR}"
        )

    update = event.update
    try:
        if update.callback_query is not None:
            await update.callback_query.answer("Something went wrong", show_alert=False)
            if update.callback_query.message is not None:
                await update.callback_query.message.answer(text)
        elif update.message is not None:
            await update.message.answer(text)
    except TelegramAPIError:
        pass

    try:
        await mirror_error(bot, where=_where(event), kind=type(exception).__name__, user_id=_user_id(event))
    except Exception:  # noqa: BLE001 - never let the error handler raise
        log.debug("error mirror failed", exc_info=True)
