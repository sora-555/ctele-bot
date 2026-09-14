"""Profile, settings, personal stats, favorites and history."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.database import repository as repo
from bot.handlers.common import open_gallery, safe_edit_text, show_listing, show_screen
from bot.keyboards import inline
from bot.loader import services
from bot.texts import ui

log = logging.getLogger(__name__)
router = Router(name="account")

IMAGE_MIN, IMAGE_MAX = 2, 10
ITEM_MIN, ITEM_MAX = 4, 10


def _settings_view(setting, ttl_label: str) -> tuple[str, object]:
    return (
        ui.settings_text(
            images_per_page=setting.images_per_page,
            items_per_page=setting.items_per_page,
            mode=setting.delivery_mode,
            spoiler=setting.spoiler_media,
            thumbnails=setting.show_thumbnails,
            ttl_label=ttl_label,
        ),
        inline.settings(
            images_per_page=setting.images_per_page,
            items_per_page=setting.items_per_page,
            mode=setting.delivery_mode,
            spoiler=setting.spoiler_media,
            thumbnails=setting.show_thumbnails,
        ),
    )


async def send_profile(bot, chat_id: int, user, session) -> None:
    favorites = await repo.count_favorites(session, user.id)
    history = await repo.count_history(session, user.id)
    await bot.send_message(
        chat_id,
        ui.profile(
            user=user,
            favorites=favorites,
            history=history,
            ttl_label=services().deletions.ttl_label,
        ),
        reply_markup=inline.profile(),
    )


@router.message(Command("profile"))
async def cmd_profile(message: Message, user, session) -> None:
    await send_profile(message.bot, message.chat.id, user, session)


@router.callback_query(F.data == "cmd:profile")
async def cb_profile(callback: CallbackQuery, user, session) -> None:
    await callback.answer()
    await send_profile(callback.bot, callback.message.chat.id, user, session)


@router.message(Command("stats"))
async def cmd_stats(message: Message, user, session) -> None:
    favorites = await repo.count_favorites(session, user.id)
    rows, total = await repo.list_history(session, user.id, page=1, per_page=1)
    await message.answer(
        ui.user_stats(
            requests=user.request_count,
            viewed=total,
            favorites=favorites,
            since=user.created_at,
            last_seen=user.last_seen_at,
        ),
        reply_markup=inline.back_to_menu(),
    )


@router.message(Command("settings"))
async def cmd_settings(message: Message, user, session) -> None:
    setting = await repo.settings_for(session, user.id)
    text, markup = _settings_view(setting, services().deletions.ttl_label)
    await message.answer(text, reply_markup=markup)


@router.callback_query(F.data == "cmd:settings")
async def cb_settings(callback: CallbackQuery, user, session) -> None:
    setting = await repo.settings_for(session, user.id)
    text, markup = _settings_view(setting, services().deletions.ttl_label)
    await callback.answer()
    await callback.message.answer(text, reply_markup=markup)


@router.callback_query(F.data.startswith("st:"))
async def cb_settings_change(callback: CallbackQuery, user, session) -> None:
    _, field, value = callback.data.split(":")
    setting = await repo.settings_for(session, user.id)

    if field == "images":
        step = 1 if value.lstrip("-").isdigit() and int(value) > 0 else -1
        target = min(max(setting.images_per_page + step, IMAGE_MIN), IMAGE_MAX)
        await repo.update_settings(session, user.id, images_per_page=target)
    elif field == "mode":
        await repo.update_settings(session, user.id, delivery_mode=value if value in ("album", "single") else "album")
    elif field == "thumb":
        await repo.update_settings(session, user.id, show_thumbnails=not setting.show_thumbnails)
    elif field == "spoiler":
        await repo.update_settings(session, user.id, spoiler_media=not setting.spoiler_media)
    elif field == "reset":
        await repo.reset_settings(session, user.id)

    fresh = await repo.settings_for(session, user.id)
    text, markup = _settings_view(fresh, services().deletions.ttl_label)
    await callback.answer(f"{ui.SUCCESS} Saved")
    try:
        await safe_edit_text(callback.bot, callback.message.chat.id, callback.message.message_id, text, markup)
    except Exception:  # noqa: BLE001
        await callback.message.answer(text, reply_markup=markup)


@router.message(Command("favorites"))
async def cmd_favorites(message: Message, user) -> None:
    await show_listing(message.bot, message.chat.id, user_id=user.id, kind="favorites", page=1)


@router.callback_query(F.data == "cmd:favorites")
async def cb_favorites(callback: CallbackQuery, user) -> None:
    await callback.answer()
    await show_listing(callback.bot, callback.message.chat.id, user_id=user.id, kind="favorites", page=1)


@router.message(Command("history"))
async def cmd_history(message: Message, user) -> None:
    parts = (message.text or "").split()
    if len(parts) > 1 and parts[1].lower() == "clear":
        await clear_history(message, user)
        return
    await show_listing(message.bot, message.chat.id, user_id=user.id, kind="history", page=1)


@router.callback_query(F.data == "cmd:history")
async def cb_history(callback: CallbackQuery, user) -> None:
    await callback.answer()
    await show_listing(callback.bot, callback.message.chat.id, user_id=user.id, kind="history", page=1)


async def clear_history(message: Message, user) -> None:
    from bot.database.base import session_scope

    async with session_scope() as session:
        removed = await repo.clear_history(session, user.id)
    await message.answer(
        f"{ui.SUCCESS} 𝗛𝗶𝘀𝘁𝗼𝗿𝘆 𝗖𝗹𝗲𝗮𝗿𝗲𝗱\n\n{ui.SEPARATOR}\n\n"
        f"{ui.ITEM} Removed {ui.KV} {removed} entr" + ("y" if removed == 1 else "ies") + "\n",
        reply_markup=inline.back_to_menu(),
    )


@router.callback_query(F.data == "hc:ask")
async def cb_clear_ask(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        f"{ui.IMPORTANT} 𝗖𝗹𝗲𝗮𝗿 𝗛𝗶𝘀𝘁𝗼𝗿𝘆\n\n{ui.SEPARATOR}\n\n"
        "This removes every entry from your history.\n",
        reply_markup=inline.clear_history_confirm(),
    )


@router.callback_query(F.data == "hc:yes")
async def cb_clear_yes(callback: CallbackQuery, user) -> None:
    from bot.database.base import session_scope

    async with session_scope() as session:
        removed = await repo.clear_history(session, user.id)
    await callback.answer(f"{ui.SUCCESS} Cleared")
    try:
        await safe_edit_text(
            callback.bot,
            callback.message.chat.id,
            callback.message.message_id,
            f"{ui.SUCCESS} 𝗛𝗶𝘀𝘁𝗼𝗿𝘆 𝗖𝗹𝗲𝗮𝗿𝗲𝗱\n\n{ui.SEPARATOR}\n\n{ui.ITEM} Removed {ui.KV} {removed}\n",
            inline.back_to_menu(),
        )
    except Exception:  # noqa: BLE001
        pass


@router.callback_query(F.data == "hc:no")
async def cb_clear_no(callback: CallbackQuery) -> None:
    await callback.answer("Cancelled")
    await show_screen(
        callback.bot,
        callback.message.chat.id,
        text=(f"{ui.PENDING} 𝗖𝗹𝗲𝗮𝗿 𝗛𝗶𝘀𝘁𝗼𝗿𝘆\n\n{ui.SEPARATOR}\n\n"
              f"{ui.ITEM} Cancelled {ui.KV} nothing was removed\n"),
        markup=inline.back_to_menu(),
        edit_id=callback.message.message_id,
    )


@router.callback_query(F.data.startswith("fe:"))
async def cb_open_media_entry(callback: CallbackQuery, user) -> None:
    _, sid, raw_index = callback.data.split(":")
    svc = services()
    payload = svc.sessions.get(sid, user_id=user.id)
    if payload is None:
        await callback.answer("Expired", show_alert=True)
        return
    entries = payload.get("entries") or []
    index = int(raw_index)
    if index >= len(entries):
        await callback.answer("Expired", show_alert=True)
        return

    entry = entries[index]
    await callback.answer()
    await open_gallery(
        callback.bot,
        callback.message.chat.id,
        user_id=user.id,
        post_url=entry["url"],
        clear_ids=list(payload.get("album_ids") or []),
        edit_id=callback.message.message_id,
        edit_is_photo=bool(payload.get("is_photo")),
    )


@router.callback_query(F.data.startswith("fx:"))
async def cb_toggle_manage(callback: CallbackQuery, user) -> None:
    _, sid = callback.data.split(":", 1)
    svc = services()
    payload = svc.sessions.get(sid, user_id=user.id)
    if payload is None:
        await callback.answer("Expired", show_alert=True)
        return
    manage = not bool(payload.get("manage"))
    svc.sessions.update(sid, manage=manage)
    await callback.answer("Removal mode" if manage else "Browse mode")
    await show_listing(
        callback.bot,
        callback.message.chat.id,
        user_id=user.id,
        kind=payload["kind"],
        page=payload.get("page", 1),
        manage=manage,
        clear_ids=[payload["card_id"]] if payload.get("card_id") else [],
        edit_id=callback.message.message_id,
    )


@router.callback_query(F.data.startswith("fr:"))
async def cb_remove_favorite(callback: CallbackQuery, user, session) -> None:
    _, sid, raw_index = callback.data.split(":")
    svc = services()
    payload = svc.sessions.get(sid, user_id=user.id)
    if payload is None:
        await callback.answer("Expired", show_alert=True)
        return
    entries = payload.get("entries") or []
    index = int(raw_index)
    if index >= len(entries):
        await callback.answer("Expired", show_alert=True)
        return

    entry = entries[index]
    removed = await repo.remove_favorite_by_id(session, user_id=user.id, favorite_id=entry["id"])
    await callback.answer(f"{ui.PENDING} Removed" if removed else "Already gone")
    await show_listing(
        callback.bot,
        callback.message.chat.id,
        user_id=user.id,
        kind="favorites",
        page=payload.get("page", 1),
        manage=True,
        clear_ids=[payload["card_id"]] if payload.get("card_id") else [],
        edit_id=callback.message.message_id,
    )
