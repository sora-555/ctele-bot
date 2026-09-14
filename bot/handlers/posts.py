"""Post detail cards, the paginated gallery, and the favorite toggle."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.database import repository as repo
from bot.database.base import session_scope
from bot.handlers.common import (
    open_gallery,
    open_post_card,
    render_gallery_page,
    safe_edit_markup,
)
from bot.keyboards import inline
from bot.loader import services
from bot.texts import ui

log = logging.getLogger(__name__)
router = Router(name="posts")


async def _last_viewed(session, user_id: int):
    rows, _ = await repo.list_history(session, user_id, page=1, per_page=1)
    return rows[0] if rows else None


@router.message(Command("post"))
async def cmd_post(message: Message, user) -> None:
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await message.answer(
            f"{ui.PENDING} 𝗣𝗼𝘀𝘁\n\n{ui.SEPARATOR}\n\n"
            f"{ui.ITEM} Usage {ui.KV} /post <link>\n"
            f"{ui.ITEM} Tip {ui.KV} search results open galleries directly\n",
            reply_markup=inline.back_to_menu(),
        )
        return
    await open_post_card(message.bot, message.chat.id, user_id=user.id, post_url=parts[1].strip())


@router.message(Command("last"))
async def cmd_last(message: Message, user, session) -> None:
    row = await _last_viewed(session, user.id)
    if row is None:
        await message.answer(ui.no_history(), reply_markup=inline.back_to_menu())
        return
    await open_post_card(message.bot, message.chat.id, user_id=user.id, post_url=row.post_url)


@router.message(Command("gallery"))
async def cmd_gallery(message: Message, user, session) -> None:
    row = await _last_viewed(session, user.id)
    if row is None:
        await message.answer(ui.no_history(), reply_markup=inline.back_to_menu())
        return
    await open_gallery(message.bot, message.chat.id, user_id=user.id, post_url=row.post_url)


@router.callback_query(F.data.startswith("pv:"))
async def cb_post_to_gallery(callback: CallbackQuery, user) -> None:
    _, sid, raw_page = callback.data.split(":")
    payload = services().sessions.get(sid, user_id=user.id)
    if payload is None:
        await callback.answer("Expired", show_alert=True)
        return
    await callback.answer()
    await open_gallery(
        callback.bot,
        callback.message.chat.id,
        user_id=user.id,
        post_url=payload["post_url"],
        page=max(int(raw_page), 1),
        clear_ids=list(payload.get("message_ids") or []),
        edit_id=callback.message.message_id,
        edit_is_photo=bool(payload.get("is_photo")),
    )


@router.callback_query(F.data.startswith("g:"))
async def cb_gallery_page(callback: CallbackQuery, user) -> None:
    try:
        _, sid, raw_page = callback.data.split(":")
        page = int(raw_page)
    except ValueError:
        await callback.answer()
        return

    svc = services()
    payload = svc.sessions.get(sid, user_id=user.id)
    if payload is None:
        await callback.answer()
        await callback.message.answer(ui.session_expired(), reply_markup=inline.session_expired())
        return

    svc.sessions.update(sid, page=max(page, 1))
    await callback.answer()
    await render_gallery_page(
        callback.bot,
        callback.message.chat.id,
        sid=sid,
        user_id=user.id,
        edit_in_place=True,
    )


@router.callback_query(F.data.startswith("gd:"))
async def cb_gallery_details(callback: CallbackQuery, user) -> None:
    _, sid = callback.data.split(":", 1)
    payload = services().sessions.get(sid, user_id=user.id)
    if payload is None:
        await callback.answer("Expired", show_alert=True)
        return
    await callback.answer()
    await open_post_card(
        callback.bot,
        callback.message.chat.id,
        user_id=user.id,
        post_url=payload["post_url"],
        clear_ids=list(payload.get("message_ids") or []),
        edit_id=callback.message.message_id,
        edit_is_photo=True,
        back_label=f"{ui.LEFT} Gallery",
        back_data=f"g:{sid}:{payload.get('page', 1)}",
    )


@router.callback_query(F.data.startswith("fv:"))
async def cb_toggle_favorite(callback: CallbackQuery, user, session) -> None:
    _, sid = callback.data.split(":", 1)
    svc = services()
    payload = svc.sessions.get(sid, user_id=user.id)
    if payload is None:
        await callback.answer("Expired", show_alert=True)
        return

    post_url = payload["post_url"]
    async with session_scope() as db:
        saved = await repo.toggle_favorite(
            db,
            user_id=user.id,
            post_url=post_url,
            title=payload.get("title") or post_url,
            thumbnail=(payload.get("images") or [None])[0],
        )

    await callback.answer(f"{ui.SUCCESS} Saved" if saved else f"{ui.PENDING} Removed")

    message_ids = list(payload.get("message_ids") or [])
    if not message_ids:
        return

    if payload.get("kind") == "post":
        markup = inline.post_card(
            sid, is_favorite=saved, post_url=post_url, back_label="Back", back_data="cmd:menu"
        )
    else:
        from bot.services.pagination import known

        images = payload.get("images") or []
        per_page = max(2, min(10, payload.get("per_page") or svc.settings.images_per_page))
        info = known(len(images), per_page, payload.get("page", 1))
        markup = inline.gallery(sid, info, is_favorite=saved, post_url=post_url)
    await safe_edit_markup(callback.bot, callback.message.chat.id, message_ids[0], markup)
