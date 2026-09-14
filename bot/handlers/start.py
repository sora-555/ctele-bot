"""Onboarding, menu, and small utility commands."""

from __future__ import annotations

import logging
import time

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot import __version__
from bot.database import repository as repo
from bot.keyboards import inline, reply
from bot.loader import services
from bot.texts import ui

log = logging.getLogger(__name__)
router = Router(name="start")


async def send_welcome(bot, chat_id: int, *, user, ttl_label: str) -> None:
    await bot.send_message(
        chat_id,
        ui.welcome(user.display_name, user.id, ttl_label),
        reply_markup=inline.welcome(),
    )
    try:
        await bot.send_message(chat_id, "\u2756 𝗠𝗲𝗻𝘂", reply_markup=reply.main_menu())
    except Exception:  # noqa: BLE001 - reply keyboard is a nicety
        log.debug("reply keyboard could not be sent", exc_info=True)


@router.message(CommandStart())
async def cmd_start(message: Message, session, user, is_admin: bool, state: FSMContext) -> None:
    await state.clear()
    svc = services()
    if svc.settings.age_gate and not user.age_verified and not is_admin:
        await message.answer(ui.age_gate(), reply_markup=inline.age_gate())
        return
    await send_welcome(message.bot, message.chat.id, user=user, ttl_label=svc.deletions.ttl_label)


@router.callback_query(F.data == "age:yes")
async def age_confirm(callback: CallbackQuery, session, user) -> None:
    await repo.mark_age_verified(session, user.id)
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:  # noqa: BLE001
        pass
    await callback.answer("Verified")
    fresh = await repo.get(session, user.id) or user
    await send_welcome(
        callback.bot, callback.message.chat.id, user=fresh, ttl_label=services().deletions.ttl_label
    )


@router.callback_query(F.data == "age:no")
async def age_decline(callback: CallbackQuery) -> None:
    try:
        await callback.message.edit_text(ui.age_gate_declined(), reply_markup=inline.back_to_menu())
    except Exception:  # noqa: BLE001
        pass
    await callback.answer()


@router.callback_query(F.data == "cmd:menu")
async def callback_menu(callback: CallbackQuery, session, user) -> None:
    await repo.settings_for(session, user.id)
    favorites = await repo.count_favorites(session, user.id)
    status = f"{ui.IMPORTANT} Active" if user.is_active else f"{ui.PENDING} Blocked"
    await callback.answer()
    await callback.message.answer(
        ui.main_menu(user.display_name, favorites, status), reply_markup=inline.main_menu()
    )


@router.message(Command("menu"))
async def cmd_menu(message: Message, session, user) -> None:
    await repo.settings_for(session, user.id)
    favorites = await repo.count_favorites(session, user.id)
    status = f"{ui.IMPORTANT} Active" if user.is_active else f"{ui.PENDING} Blocked"
    await message.answer(
        ui.main_menu(user.display_name, favorites, status), reply_markup=inline.main_menu()
    )


@router.message(Command("help"))
async def cmd_help(message: Message, is_admin: bool) -> None:
    text = ui.help_user() + ("\n\n" + ui.help_admin() if is_admin else "")
    await message.answer(text, reply_markup=inline.back_to_menu())


@router.message(F.text == reply.HELP)
async def reply_help(message: Message, is_admin: bool) -> None:
    await cmd_help(message, is_admin)


@router.message(Command("about"))
async def cmd_about(message: Message) -> None:
    svc = services()
    await message.answer(
        ui.about(__version__, svc.deletions.ttl_label, svc.settings.source_base_url),
        reply_markup=inline.back_to_menu(),
    )


@router.message(Command("ping"))
async def cmd_ping(message: Message) -> None:
    svc = services()
    started = time.perf_counter()
    ok, latency, error = await svc.ctele.health()
    elapsed = int((time.perf_counter() - started) * 1000)
    lines = [
        f"{ui.SUCCESS if ok else ui.IMPORTANT} 𝗣𝗶𝗻𝗴",
        "",
        ui.SEPARATOR,
        "",
        f"{ui.ITEM} Bot {ui.KV} responsive",
        f"{ui.ITEM} Source {ui.KV} {latency if latency is not None else '-'} ms",
        f"{ui.ITEM} Round trip {ui.KV} {elapsed} ms",
    ]
    if not ok and error:
        lines.append(f"{ui.ITEM} Error {ui.KV} {error[:80]}")
    await message.answer("\n".join(lines), reply_markup=inline.back_to_menu())


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        f"{ui.PENDING} 𝗖𝗮𝗻𝗰𝗲𝗹𝗹𝗲𝗱\n\n{ui.SEPARATOR}\n\n{ui.ITEM} Nothing is pending\n",
        reply_markup=inline.back_to_menu(),
    )
