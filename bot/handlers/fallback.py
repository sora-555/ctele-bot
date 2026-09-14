"""Last-resort handlers so nothing ever fails silently."""

from __future__ import annotations

from aiogram import Router
from aiogram.types import CallbackQuery, Message

from bot.keyboards import inline
from bot.texts import ui

router = Router(name="fallback")


@router.message()
async def unknown_message(message: Message) -> None:
    await message.answer(ui.unknown_input(), reply_markup=inline.back_to_menu())


@router.callback_query()
async def unknown_callback(callback: CallbackQuery) -> None:
    await callback.answer("This button is no longer active", show_alert=False)
