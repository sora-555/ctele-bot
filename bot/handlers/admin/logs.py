"""Audit log viewer with optional action filtering."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.database import repository as repo
from bot.filters.admin import IsAdmin
from bot.handlers.common import show_screen
from bot.keyboards import admin as admin_kb
from bot.services.pagination import known
from bot.texts import ui
from bot.utils.text import truncate
from bot.utils.time import format_dt

router = Router(name="admin-logs")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

PAGE_SIZE = 10


def _keyboard(action: str | None, info) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    prefix = f"a:logp:{action}" if action else "a:logs"
    builder.row(
        InlineKeyboardButton(
            text=f"{ui.PREV} Prev" if info.has_prev else ui.PREV,
            callback_data=f"{prefix}:{info.page - 1}" if info.has_prev else admin_kb.NOOP,
        ),
        InlineKeyboardButton(text=f"Page {info.label}", callback_data=admin_kb.NOOP),
        InlineKeyboardButton(
            text=f"Next {ui.NEXT}" if info.has_next else ui.NEXT,
            callback_data=f"{prefix}:{info.page + 1}" if info.has_next else admin_kb.NOOP,
        ),
    )
    builder.row(
        InlineKeyboardButton(text="Filter" if action else "Filter by Action", callback_data="a:logfilter"),
        InlineKeyboardButton(text="Menu", callback_data="cmd:menu"),
    )
    return builder.as_markup()


async def send_logs(
    bot, chat_id: int, session, *, page: int, action: str | None = None, edit_id: int | None = None
) -> None:
    rows, total = await repo.list_logs_page(session, page=page, per_page=PAGE_SIZE, action=action)
    info = known(total, PAGE_SIZE, page)
    body = [
        f"{format_dt(row.created_at)} {ui.KV} {row.admin_id or '-'} {ui.KV} {row.action} "
        f"{ui.KV} {truncate(str(row.target_id or '-'), 24)}"
        for row in rows
    ]
    text = ui.logs_text(entries=total, page_label=info.label, rows=body)
    if action:
        text += f"\n{ui.ITEM} Filter {ui.KV} {action}"
    await show_screen(bot, chat_id, text=text, markup=_keyboard(action, info), edit_id=edit_id)


@router.message(Command("logs"))
async def cmd_logs(message: Message, session) -> None:
    tokens = (message.text or "").split()[1:]
    page = next((int(token) for token in tokens if token.isdigit()), 1)
    await send_logs(message.bot, message.chat.id, session, page=page)


@router.callback_query(F.data.startswith("a:logs:"))
async def cb_logs(callback: CallbackQuery, session) -> None:
    page = int(callback.data.split(":")[2])
    await callback.answer()
    await send_logs(
        callback.bot, callback.message.chat.id, session, page=page, edit_id=callback.message.message_id
    )


@router.callback_query(F.data.startswith("a:logp:"))
async def cb_logs_filtered(callback: CallbackQuery, session) -> None:
    _, _, action, raw_page = callback.data.split(":")
    await callback.answer()
    await send_logs(
        callback.bot,
        callback.message.chat.id,
        session,
        page=int(raw_page),
        action=None if action == "all" else action,
        edit_id=callback.message.message_id,
    )


@router.callback_query(F.data == "a:logfilter")
async def cb_log_filter_prompt(callback: CallbackQuery, session) -> None:
    actions = await repo.audit_actions(session)
    if not actions:
        await callback.answer("No entries yet", show_alert=True)
        return
    builder = InlineKeyboardBuilder()
    for action in actions[:10]:
        builder.row(InlineKeyboardButton(text=action, callback_data=f"a:logp:{action}:1"))
    builder.row(InlineKeyboardButton(text="All", callback_data="a:logp:all:1"))
    await callback.answer()
    await show_screen(
        callback.bot,
        callback.message.chat.id,
        text=f"{ui.HEADER} 𝗙𝗶𝗹𝘁𝗲𝗿 𝗟𝗼𝗴\n\n{ui.SEPARATOR}\n\n{ui.ITEM} Pick an action to filter by\n",
        markup=builder.as_markup(),
        edit_id=callback.message.message_id,
    )


@router.callback_query(F.data == "a:logdo:all")
async def cb_log_do_all(callback: CallbackQuery, session) -> None:
    await callback.answer()
    await send_logs(
        callback.bot, callback.message.chat.id, session, page=1, edit_id=callback.message.message_id
    )
