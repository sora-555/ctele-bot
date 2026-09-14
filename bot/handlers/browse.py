"""Browsing: latest, popular, categories, search and random.

`/search` shows one result at a time: Prev, Open and Next on the top row, a number row
underneath. The number row is a shortcut into the in-chat flow - the bot asks for the
number in the chat and then rewrites the same card, so stepping through results never
leaves a trail of old screens behind.
"""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.handlers.common import (
    open_gallery,
    open_post_card,
    open_search_card,
    render_search_card,
    safe_delete,
    show_listing,
)
from bot.keyboards import inline, reply
from bot.loader import services
from bot.states.user import SearchJump, SearchQuery
from bot.texts import ui

log = logging.getLogger(__name__)
router = Router(name="browse")

RANGES = {
    "day": "last24hours",
    "week": "last7days",
    "month": "last30days",
    "all": "all",
}


def _tokens(text: str | None) -> list[str]:
    return (text or "").split()[1:]


def _page_from(tokens: list[str], default: int = 1) -> int:
    for token in tokens:
        if token.isdigit():
            return max(int(token), 1)
    return default


def _range_from(tokens: list[str]) -> tuple[str, str]:
    for token in tokens:
        key = token.lower()
        if key in RANGES:
            return RANGES[key], key
    return RANGES["week"], "week"


# ---------------------------------------------------------------------- commands


@router.message(Command("latest"))
async def cmd_latest(message: Message, user) -> None:
    await show_listing(
        message.bot,
        message.chat.id,
        user_id=user.id,
        kind="latest",
        page=_page_from(_tokens(message.text)),
    )


@router.message(Command("popular"))
async def cmd_popular(message: Message, user) -> None:
    tokens = _tokens(message.text)
    time_range, _ = _range_from(tokens)
    await show_listing(
        message.bot,
        message.chat.id,
        user_id=user.id,
        kind="popular",
        page=_page_from(tokens, 1),
        time_range=time_range,
    )


@router.message(Command("categories"))
async def cmd_categories(message: Message, user) -> None:
    await show_listing(message.bot, message.chat.id, user_id=user.id, kind="categories", page=1)


@router.message(Command("category"))
async def cmd_category(message: Message, user) -> None:
    tokens = _tokens(message.text)
    if not tokens:
        await message.answer(
            f"{ui.PENDING} 𝗖𝗮𝘁𝗲𝗴𝗼𝗿𝘆\n\n{ui.SEPARATOR}\n\n"
            f"{ui.ITEM} Usage {ui.KV} /category <name>\n"
            f"{ui.ITEM} Example {ui.KV} /category cosplay\n",
            reply_markup=inline.confirm("cmd:categories", "cmd:menu", yes_label="Browse Categories", no_label="Menu"),
        )
        return
    path = await _resolve_category(tokens[0])
    await show_listing(
        message.bot,
        message.chat.id,
        user_id=user.id,
        kind="category",
        path=path,
        page=_page_from(tokens, 1),
    )


async def _resolve_category(token: str) -> str:
    """Accept either a bare name, a relative path, or a full URL."""
    if token.startswith(("http://", "https://")) or "/" in token:
        return token
    try:
        for category in await services().ctele.categories():
            if category.name.lower() == token.lower():
                return category.path
    except Exception:  # noqa: BLE001 - fall back to the raw token
        log.debug("category lookup failed", exc_info=True)
    return token


@router.message(Command("search"))
async def cmd_search(message: Message, state: FSMContext, user) -> None:
    tokens = _tokens(message.text)
    if not tokens:
        await state.set_state(SearchQuery.query)
        await message.answer(ui.search_prompt(), reply_markup=inline.cancel_only("cmd:menu"))
        return
    query = " ".join(tokens)
    await open_search_card(message.bot, message.chat.id, user_id=user.id, query=query)


@router.message(StateFilter(SearchQuery.query), F.text)
async def search_query_input(message: Message, state: FSMContext, user) -> None:
    query = (message.text or "").strip()
    await state.clear()
    if not query:
        await message.answer(ui.search_prompt(), reply_markup=inline.cancel_only("cmd:menu"))
        return
    await open_search_card(message.bot, message.chat.id, user_id=user.id, query=query)


@router.message(Command("random"))
async def cmd_random(message: Message, user) -> None:
    svc = services()
    try:
        pick = await svc.ctele.random_post()
    except Exception as exc:  # noqa: BLE001
        await message.answer(ui.source_unavailable(str(exc)), reply_markup=inline.back_to_menu())
        return
    if pick is None:
        await message.answer(ui.source_unavailable("no posts found"), reply_markup=inline.back_to_menu())
        return
    await message.answer(f"{ui.SECTION} 𝗥𝗮𝗻𝗱𝗼𝗺 𝗣𝗶𝗰𝗸")
    await open_post_card(message.bot, message.chat.id, user_id=user.id, post_url=pick.url)


# ---------------------------------------------------------------------- reply menu


@router.message(F.text == reply.LATEST)
async def reply_latest(message: Message, user) -> None:
    await cmd_latest(message, user)


@router.message(F.text == reply.POPULAR)
async def reply_popular(message: Message, user) -> None:
    await cmd_popular(message, user)


@router.message(F.text == reply.SEARCH)
async def reply_search(message: Message, state: FSMContext, user) -> None:
    await state.set_state(SearchQuery.query)
    await message.answer(ui.search_prompt(), reply_markup=inline.cancel_only("cmd:menu"))


# ---------------------------------------------------------------------- callbacks


@router.callback_query(F.data == "cmd:latest")
async def cb_latest(callback: CallbackQuery, user) -> None:
    await callback.answer()
    await show_listing(callback.bot, callback.message.chat.id, user_id=user.id, kind="latest", page=1)


@router.callback_query(F.data == "cmd:popular")
async def cb_popular(callback: CallbackQuery, user) -> None:
    await callback.answer()
    await show_listing(
        callback.bot, callback.message.chat.id, user_id=user.id, kind="popular", page=1, time_range=RANGES["week"]
    )


@router.callback_query(F.data == "cmd:categories")
async def cb_categories(callback: CallbackQuery, user) -> None:
    await callback.answer()
    await show_listing(callback.bot, callback.message.chat.id, user_id=user.id, kind="categories", page=1)


@router.callback_query(F.data == "cmd:search")
async def cb_search(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SearchQuery.query)
    await callback.answer()
    await callback.message.answer(ui.search_prompt(), reply_markup=inline.cancel_only("cmd:menu"))


@router.callback_query(F.data.startswith("ls:"))
async def cb_listing_nav(callback: CallbackQuery, user) -> None:
    try:
        _, sid, raw_page = callback.data.split(":")
        page = int(raw_page)
    except ValueError:
        await callback.answer("Bad button", show_alert=False)
        return

    svc = services()
    payload = svc.sessions.get(sid, user_id=user.id)
    if payload is None:
        await callback.answer()
        await callback.message.answer(ui.session_expired(), reply_markup=inline.session_expired())
        return

    await callback.answer()
    await show_listing(
        callback.bot,
        callback.message.chat.id,
        user_id=user.id,
        kind=payload["kind"],
        page=page,
        query=payload.get("query"),
        path=payload.get("path"),
        time_range=payload.get("time_range"),
        manage=bool(payload.get("manage")),
        clear_ids=list(payload.get("album_ids") or []),
        edit_id=callback.message.message_id,
    )


@router.callback_query(F.data.startswith("ct:"))
async def cb_open_category(callback: CallbackQuery, user) -> None:
    _, sid, raw_index = callback.data.split(":")
    payload = services().sessions.get(sid, user_id=user.id)
    if payload is None:
        await callback.answer("Expired", show_alert=True)
        return
    entries = payload.get("entries") or []
    index = int(raw_index)
    if index >= len(entries):
        await callback.answer("Expired", show_alert=True)
        return
    await callback.answer()
    await show_listing(
        callback.bot,
        callback.message.chat.id,
        user_id=user.id,
        kind="category",
        path=entries[index]["path"],
        page=1,
        clear_ids=list(payload.get("album_ids") or []),
        edit_id=callback.message.message_id,
    )


@router.callback_query(F.data.startswith("cr:"))
async def cb_refresh_categories(callback: CallbackQuery, user) -> None:
    _, sid = callback.data.split(":", 1)
    svc = services()
    payload = svc.sessions.get(sid, user_id=user.id)
    await callback.answer("Refreshing")
    try:
        await svc.ctele.categories(refresh=True)
    except Exception:  # noqa: BLE001
        log.warning("taxonomy refresh failed", exc_info=True)
    await show_listing(
        callback.bot,
        callback.message.chat.id,
        user_id=user.id,
        kind="categories",
        page=1,
        clear_ids=list((payload or {}).get("album_ids") or []),
        edit_id=callback.message.message_id,
    )


@router.callback_query(F.data.startswith("po:"))
async def cb_open_entry(callback: CallbackQuery, user, session) -> None:
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
    post_url = entry.get("url")
    if entry.get("kind") != "category" and not post_url:
        await callback.answer("Nothing to open", show_alert=True)
        return

    # The card the user tapped is rewritten into the next screen instead of being
    # deleted and re-posted, so a browse chain stays a single message.
    card_id = callback.message.message_id
    is_photo = bool(payload.get("is_photo"))
    clear_ids = list(payload.get("album_ids") or [])
    await callback.answer()

    if entry.get("kind") == "category":
        await show_listing(
            callback.bot,
            callback.message.chat.id,
            user_id=user.id,
            kind="category",
            path=entry["path"],
            page=1,
            clear_ids=clear_ids,
            edit_id=card_id,
        )
        return

    kind = payload.get("kind")
    wants_gallery = kind == "search" and svc.settings.search_select_target == "gallery"
    wants_gallery = wants_gallery or kind in ("favorites", "history")
    if wants_gallery:
        await open_gallery(
            callback.bot,
            callback.message.chat.id,
            user_id=user.id,
            post_url=post_url,
            clear_ids=clear_ids,
            edit_id=card_id,
            edit_is_photo=is_photo,
        )
    else:
        await open_post_card(
            callback.bot,
            callback.message.chat.id,
            user_id=user.id,
            post_url=post_url,
            clear_ids=clear_ids,
            edit_id=card_id,
            edit_is_photo=is_photo,
            back_data=f"ls:{sid}:{payload.get('page', 1)}",
        )


# ------------------------------------------------------------------- search card


def _step_toast(outcome: str, *, forward: bool) -> str:
    if outcome == "range":
        return "No further results" if forward else "This is the first result"
    if outcome == "unavailable":
        return "The source did not answer, try again"
    if outcome == "expired":
        return "This search expired"
    return ""


@router.callback_query(F.data.startswith("sv:"))
async def cb_search_step(callback: CallbackQuery, user) -> None:
    try:
        _, sid, direction = callback.data.split(":")
    except ValueError:
        await callback.answer()
        return

    payload = services().sessions.get(sid, user_id=user.id)
    if payload is None:
        await callback.answer("Expired", show_alert=True)
        return

    forward = direction != "p"
    outcome = await render_search_card(
        callback.bot,
        callback.message.chat.id,
        sid=sid,
        user_id=user.id,
        index=int(payload.get("index", 0)) + (1 if forward else -1),
        edit=True,
    )
    await callback.answer(_step_toast(outcome, forward=forward))


@router.callback_query(F.data.startswith("sn:"))
async def cb_search_number(callback: CallbackQuery, state: FSMContext, user) -> None:
    """The number row is a shortcut into the in-chat flow, not a direct jump."""
    try:
        _, sid, _position = callback.data.split(":")
    except ValueError:
        await callback.answer()
        return

    svc = services()
    payload = svc.sessions.get(sid, user_id=user.id)
    if payload is None:
        await callback.answer("Expired", show_alert=True)
        return

    count = len(payload.get("entries") or [])
    await callback.answer()
    await state.set_state(SearchJump.number)
    await state.update_data(sid=sid)
    prompt = await callback.message.answer(
        ui.search_jump_prompt(count), reply_markup=inline.cancel_only("cmd:menu")
    )
    svc.sessions.update(sid, jump_prompt_id=prompt.message_id)


@router.message(StateFilter(SearchJump.number), F.text)
async def search_jump_input(message: Message, state: FSMContext, user) -> None:
    raw = (message.text or "").strip()
    data = await state.get_data()
    sid = data.get("sid")
    await state.clear()

    svc = services()
    payload = svc.sessions.get(sid, user_id=user.id) if sid else None
    prompt_id = (payload or {}).get("jump_prompt_id")
    tidied = [message.message_id, prompt_id] if prompt_id else [message.message_id]
    await safe_delete(message.bot, message.chat.id, tidied)

    if payload is None:
        await message.answer(ui.session_expired(), reply_markup=inline.session_expired())
        return

    count = len(payload.get("entries") or [])
    if not raw.isdigit() or not 1 <= int(raw) <= count:
        await message.answer(
            ui.search_jump_invalid(raw, count), reply_markup=inline.cancel_only("cmd:menu")
        )
        return

    outcome = await render_search_card(
        message.bot, message.chat.id, sid=sid, user_id=user.id, index=int(raw) - 1, edit=True
    )
    if outcome == "expired":
        await message.answer(ui.session_expired(), reply_markup=inline.session_expired())


@router.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery) -> None:
    await callback.answer()
