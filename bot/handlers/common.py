"""Shared building blocks for the browsing screens.

A "listing" is any paginated list of posts (source- or database-backed). The
rendered page is kept in the session store so a button press never re-fetches
what it already showed, and every media message that goes out is scheduled for
auto-deletion.
"""

from __future__ import annotations

import logging

from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.types import InputMediaPhoto

from bot.database import repository as repo
from bot.database.base import session_scope
from bot.keyboards import inline
from bot.loader import services
from bot.services.ctele_service import SourceError
from bot.services.delivery import send_media_page, send_preview_photo
from bot.services.pagination import PageInfo, known, slice_page, unknown
from bot.texts import ui
from bot.utils.text import truncate
from bot.utils.time import utcnow

log = logging.getLogger(__name__)


async def safe_delete(bot, chat_id: int, message_ids: list[int]) -> None:
    for message_id in dict.fromkeys(message_ids or []):
        try:
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
        except TelegramAPIError:
            pass


async def safe_edit_markup(bot, chat_id: int, message_id: int, markup) -> None:
    try:
        await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=markup)
    except TelegramBadRequest as exc:
        if "not modified" not in str(exc):
            log.debug("markup edit failed: %s", exc)


async def safe_edit_text(bot, chat_id: int, message_id: int, text: str, markup=None) -> None:
    try:
        await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=markup)
    except TelegramBadRequest as exc:
        if "not modified" not in str(exc):
            raise


async def _try_edit(method, **kwargs) -> bool:
    """Edit a message in place.

    True when the edit landed - or when Telegram said the content already matches, which
    means the card on screen is exactly what we wanted it to be. False only when the edit
    is genuinely impossible, so the caller can fall back to replacing the message.
    """
    try:
        await method(**kwargs)
        return True
    except TelegramBadRequest as exc:
        if "not modified" in str(exc).lower():
            return True
        log.debug("in-place edit rejected: %s", exc)
    except TelegramAPIError as exc:
        log.debug("in-place edit failed: %s", exc)
    return False


async def show_screen(bot, chat_id: int, *, text: str, markup=None, edit_id: int | None = None) -> None:
    """Render a text screen, rewriting the message the user tapped when there is one.

    Every button that leads to another screen goes through here, so walking a chain of
    buttons rewrites a single message instead of stacking a new one on top of the last.
    """
    if edit_id and await _try_edit(
        bot.edit_message_text,
        chat_id=chat_id,
        message_id=edit_id,
        text=text,
        reply_markup=markup,
    ):
        return
    await bot.send_message(chat_id, text, reply_markup=markup)


def numbered_label(index: int, title: str) -> str:
    return f"{index} \u00b7 {truncate(title, 22)}"


def _without(message_ids: list[int] | None, keep: int | None) -> list[int]:
    """The ids worth deleting, minus the message we are about to edit in place."""
    return [message_id for message_id in (message_ids or []) if message_id != keep]


async def present_card(
    bot,
    chat_id: int,
    *,
    text: str,
    markup,
    photo_url: str | None = None,
    edit_id: int | None = None,
    edit_is_photo: bool = False,
    prefer_caption: bool = False,
    spoiler: bool = False,
) -> tuple[int | None, bool]:
    """Show a card, editing the message the user is already looking at when possible.

    Chained button taps rewrite the existing message instead of deleting it and posting a
    replacement, so walking from a result to its gallery and back keeps one card in the
    chat. Telegram cannot turn a photo message into a text one, so that case is handled by
    rewriting the caption when ``prefer_caption`` is set, and only falls back to replacing
    the message when even that is refused. Returns ``(message_id, is_photo)``.
    """
    if edit_id:
        if edit_is_photo and prefer_caption:
            # The user is already looking at this image; keep it and rewrite the words
            # around it instead of jumping them back to the post's first picture.
            if await _try_edit(
                bot.edit_message_caption,
                chat_id=chat_id,
                message_id=edit_id,
                caption=text,
                reply_markup=markup,
            ):
                return edit_id, True
        if photo_url:
            if await _try_edit(
                bot.edit_message_media,
                chat_id=chat_id,
                message_id=edit_id,
                media=InputMediaPhoto(media=photo_url, caption=text, has_spoiler=spoiler),
                reply_markup=markup,
            ):
                return edit_id, True
        elif not edit_is_photo:
            if await _try_edit(
                bot.edit_message_text,
                chat_id=chat_id,
                message_id=edit_id,
                text=text,
                reply_markup=markup,
            ):
                return edit_id, False
        await safe_delete(bot, chat_id, [edit_id])

    if photo_url:
        message = await send_preview_photo(
            bot, chat_id, photo_url, caption=text, reply_markup=markup, spoiler=spoiler
        )
        if message is not None:
            return message.message_id, True
    message = await bot.send_message(chat_id, text, reply_markup=markup)
    return message.message_id, False


def _title_for(kind: str) -> str:
    return {
        "latest": "𝗟𝗮𝘁𝗲𝘀𝘁 𝗣𝗼𝘀𝘁𝘀",
        "popular": "𝗣𝗼𝗽𝘂𝗹𝗮𝗿 𝗣𝗼𝘀𝘁𝘀",
        "category": "𝗖𝗮𝘁𝗲𝗴𝗼𝗿𝘆",
    }.get(kind, "𝗣𝗼𝘀𝘁𝘀")


async def _post_entries(items) -> list[dict]:
    return [
        {
            "kind": "post",
            "label": item.title,
            "title": item.title,
            "url": item.url,
            "thumbnail": getattr(item, "thumbnail", None),
        }
        for item in items
    ]


async def _collect(
    kind: str,
    *,
    page: int,
    query: str | None,
    path: str | None,
    time_range: str | None,
    user_id: int,
    session,
) -> tuple[list[dict], PageInfo]:
    svc = services()
    per_page = svc.settings.items_per_page

    if kind in ("latest", "popular", "search", "category"):
        if kind == "latest":
            result = await svc.ctele.latest(page)
        elif kind == "popular":
            result = await svc.ctele.popular(page - 1, time_range=time_range or "last7days")
        elif kind == "search":
            result = await svc.ctele.search(query or "", page)
        else:
            result = await svc.ctele.category(path or "", page)
        return await _post_entries(result.items), unknown(page, per_page, result.has_next)

    if kind == "categories":
        categories = await svc.ctele.categories()
        info = known(len(categories), per_page, page)
        entries = [
            {
                "kind": "category",
                "label": item.name,
                "title": item.name,
                "path": item.path,
                "url": None,
                "thumbnail": None,
            }
            for item in slice_page(categories, per_page, info.page)
        ]
        return entries, info

    if kind == "favorites":
        rows, total = await repo.list_favorites(session, user_id, page=page, per_page=per_page)
        entries = [
            {
                "kind": "favorite",
                "label": row.post_title,
                "title": row.post_title,
                "url": row.post_url,
                "thumbnail": row.thumbnail,
                "id": row.id,
            }
            for row in rows
        ]
        return entries, known(total, per_page, page)

    if kind == "history":
        rows, total = await repo.list_history(session, user_id, page=page, per_page=per_page)
        entries = [
            {
                "kind": "history",
                "label": row.post_title,
                "title": row.post_title,
                "url": row.post_url,
                "thumbnail": row.thumbnail,
                "id": row.id,
            }
            for row in rows
        ]
        return entries, known(total, per_page, page)

    raise ValueError(f"unknown listing kind: {kind}")


def _listing_markup(sid: str, kind: str, info: PageInfo, labels: list[str], manage: bool):
    if kind == "categories":
        return inline.categories(sid, info, labels)
    if kind == "favorites":
        return inline.media_list(sid, info, labels, prefix="fe", manage=manage)
    if kind == "history":
        return inline.media_list(sid, info, labels, prefix="fe", with_clear=True)
    return inline.listing(sid, info, labels)


def _window_label(info: PageInfo, count: int) -> str:
    first = info.start_index + 1
    last = first + count - 1
    if info.total_pages:
        return f"{first}-{last} of {info.total}"
    return f"{first}-{last}, more available" if info.has_next else f"{first}-{last}"


async def _paint_search_card(bot, chat_id: int, *, sid: str, user_id: int, index: int, edit: bool = True) -> bool:
    """Draw the single-result card, editing the previous one when asked to."""
    svc = services()
    payload = svc.sessions.get(sid, user_id=user_id)
    if payload is None:
        return False

    entries = payload["entries"]
    info: PageInfo = payload["info"]
    if not entries:
        return False
    index = max(0, min(index, len(entries) - 1))
    entry = entries[index]
    thumbnail = entry.get("thumbnail") if svc.settings.search_thumbnails else None

    text = ui.search_card(
        query=payload.get("query") or "",
        title=entry.get("title") or "",
        position=index + 1,
        count=len(entries),
        window=_window_label(info, len(entries)),
        ttl_label=svc.deletions.ttl_label,
        photo=bool(thumbnail),
    )
    markup = inline.search_card(
        sid,
        count=len(entries),
        index=index,
        has_prev=index > 0 or info.has_prev,
        has_next=index + 1 < len(entries) or info.has_next,
    )
    message_id, is_photo = await present_card(
        bot,
        chat_id,
        text=text,
        markup=markup,
        photo_url=thumbnail,
        edit_id=payload.get("card_id") if edit else None,
        edit_is_photo=bool(payload.get("is_photo")),
    )
    if message_id is None:
        return False

    svc.sessions.update(sid, index=index, card_id=message_id, is_photo=is_photo, message_ids=[message_id])
    if is_photo:
        await svc.deletions.schedule(
            chat_id=chat_id, message_ids=[message_id], user_id=user_id, kind="card"
        )
    return True


async def open_search_card(
    bot,
    chat_id: int,
    *,
    user_id: int,
    query: str,
    page: int = 1,
    clear_ids: list[int] | None = None,
) -> str | None:
    """First render of /search: one result at a time, bigger and unmistakable."""
    svc = services()
    async with session_scope() as session:
        try:
            entries, info = await _collect(
                "search", page=page, query=query, path=None, time_range=None, user_id=user_id, session=session
            )
        except SourceError as exc:
            await safe_delete(bot, chat_id, clear_ids or [])
            await bot.send_message(chat_id, ui.source_unavailable(str(exc)))
            return None

    await safe_delete(bot, chat_id, clear_ids or [])

    if not entries:
        await bot.send_message(chat_id, ui.search_no_results(query), reply_markup=inline.no_results())
        return None

    sid = svc.sessions.new(
        {
            "user_id": user_id,
            "kind": "search",
            "query": query,
            "page": info.page,
            "info": info,
            "entries": entries,
            "index": 0,
            "card_id": None,
            "is_photo": False,
            "manage": False,
        }
    )
    if not await _paint_search_card(bot, chat_id, sid=sid, user_id=user_id, index=0, edit=False):
        return None
    return sid


async def render_search_card(
    bot,
    chat_id: int,
    *,
    sid: str,
    user_id: int,
    index: int | None = None,
    edit: bool = True,
) -> str:
    """Move the search card to another result.

    Returns ``ok``, ``expired``, ``range`` (past the first/last result) or
    ``unavailable`` (the source refused the next page) so callers can answer with the
    right toast.
    """
    svc = services()
    payload = svc.sessions.get(sid, user_id=user_id)
    if payload is None:
        return "expired"

    info: PageInfo = payload["info"]
    entries = payload["entries"]
    if index is None:
        index = int(payload.get("index", 0))

    page_to_load: int | None = None
    if index < 0:
        if not info.has_prev:
            return "range"
        page_to_load, index = info.page - 1, -1
    elif index >= len(entries):
        if not info.has_next:
            return "range"
        page_to_load, index = info.page + 1, 0

    if page_to_load is not None:
        async with session_scope() as session:
            try:
                entries, info = await _collect(
                    "search",
                    page=page_to_load,
                    query=payload.get("query") or "",
                    path=None,
                    time_range=None,
                    user_id=user_id,
                    session=session,
                )
            except SourceError:
                return "unavailable"
        if not entries:
            return "range"
        if index < 0:
            index = len(entries) - 1
        svc.sessions.update(sid, entries=entries, info=info, page=info.page)

    if not await _paint_search_card(bot, chat_id, sid=sid, user_id=user_id, index=index, edit=edit):
        return "expired"
    return "ok"


async def _send_empty_state(bot, chat_id: int, kind: str, query: str | None) -> None:
    if kind == "favorites":
        await bot.send_message(chat_id, ui.empty_favorites(), reply_markup=inline.back_to_menu())
    elif kind == "history":
        await bot.send_message(chat_id, ui.no_history(), reply_markup=inline.back_to_menu())
    elif kind == "search":
        await bot.send_message(chat_id, ui.search_no_results(query or ""), reply_markup=inline.no_results())
    else:
        await bot.send_message(
            chat_id,
            ui.listing(_title_for(kind), "1", 0, hint="Nothing here yet."),
            reply_markup=inline.back_to_menu(),
        )


async def show_listing(
    bot,
    chat_id: int,
    *,
    user_id: int,
    kind: str,
    page: int = 1,
    query: str | None = None,
    path: str | None = None,
    time_range: str | None = None,
    manage: bool = False,
    clear_ids: list[int] | None = None,
    edit_id: int | None = None,
) -> str | None:
    """Render (or re-render) a listing page and return its session id.

    ``edit_id`` is the message the user is already looking at. Paging a listing rewrites
    that message instead of deleting it and posting a replacement, so the chat keeps a
    single card no matter how far the user browses.
    """
    svc = services()
    failure: SourceError | None = None
    entries: list[dict] = []
    info: PageInfo | None = None

    async with session_scope() as session:
        try:
            entries, info = await _collect(
                kind, page=page, query=query, path=path, time_range=time_range, user_id=user_id, session=session
            )
            if info.page != page:
                entries, info = await _collect(
                    kind, page=info.page, query=query, path=path, time_range=time_range, user_id=user_id, session=session
                )
        except SourceError as exc:
            failure = exc

    # Telegram calls stay outside the write transaction: a slow edit must never hold a lock.
    await safe_delete(bot, chat_id, _without(clear_ids, edit_id))

    if failure is not None or info is None:
        await bot.send_message(chat_id, ui.source_unavailable(str(failure or "unavailable")))
        return None

    if not entries:
        await _send_empty_state(bot, chat_id, kind, query)
        return None

    labels = [numbered_label(position + 1, entry["title"]) for position, entry in enumerate(entries)]
    sid = svc.sessions.new(
        {
            "user_id": user_id,
            "kind": kind,
            "page": info.page,
            "query": query,
            "path": path,
            "time_range": time_range,
            "entries": entries,
            "manage": manage,
        }
    )

    if kind == "categories":
        text = ui.categories_text(info.label, len(entries))
    elif kind == "favorites":
        text = ui.favorites_text(info.total or 0, info.label, manage=manage)
    elif kind == "history":
        text = ui.history_text(info.total or 0, info.label)
    else:
        text = ui.listing(_title_for(kind), info.label, len(entries))

    message_id, _ = await present_card(
        bot, chat_id, text=text, markup=_listing_markup(sid, kind, info, labels, manage), edit_id=edit_id
    )
    svc.sessions.update(sid, card_id=message_id)
    return sid


# ---------------------------------------------------------------------- galleries


async def open_gallery(
    bot,
    chat_id: int,
    *,
    user_id: int,
    post_url: str,
    page: int = 1,
    clear_ids: list[int] | None = None,
    edit_id: int | None = None,
    edit_is_photo: bool = False,
) -> str | None:
    """Open a post's gallery.

    Arriving from a photo card (a search result or another gallery) reuses that message for
    the first image when the delivery mode is "single". Albums cannot be edited into, so
    those still replace the card instead of rewriting it.
    """
    svc = services()
    try:
        post = await svc.ctele.post(post_url)
    except SourceError as exc:
        await safe_delete(bot, chat_id, clear_ids or [])
        await bot.send_message(chat_id, ui.source_unavailable(str(exc)))
        return None

    async with session_scope() as session:
        await repo.record_view(
            session,
            user_id=user_id,
            post_url=post.url,
            title=post.title,
            thumbnail=post.images[0] if post.images else None,
        )
        await repo.prune_history(session, user_id, keep=100)
        setting = await repo.settings_for(session, user_id)

    reuse = edit_id if (edit_id and edit_is_photo and setting.delivery_mode == "single") else None

    sid = svc.sessions.new(
        {
            "user_id": user_id,
            "kind": "gallery",
            "post_url": post.url,
            "title": post.title,
            "images": list(post.images),
            "page": page,
            "mode": setting.delivery_mode,
            "spoiler": setting.spoiler_media,
            "per_page": setting.images_per_page,
            "message_ids": [reuse] if reuse else [],
        }
    )
    await safe_delete(bot, chat_id, _without(clear_ids, reuse))
    ok = await render_gallery_page(bot, chat_id, sid=sid, user_id=user_id, edit_in_place=bool(reuse))
    return sid if ok else None


async def render_gallery_page(bot, chat_id: int, *, sid: str, user_id: int, edit_in_place: bool = False) -> bool:
    svc = services()
    payload = svc.sessions.get(sid, user_id=user_id)
    if payload is None:
        await bot.send_message(chat_id, ui.session_expired(), reply_markup=inline.session_expired())
        return False

    images: list[str] = payload.get("images") or []
    if not images:
        await bot.send_message(chat_id, ui.source_unavailable("this post has no images"), reply_markup=inline.back_to_menu())
        return False

    per_page = max(2, min(10, payload.get("per_page") or svc.settings.images_per_page))
    info = known(len(images), per_page, payload["page"])
    chunk = slice_page(images, per_page, info.page)
    mode = payload.get("mode") or "album"
    spoiler = bool(payload.get("spoiler"))
    previous_ids: list[int] = list(payload.get("message_ids") or [])

    async with session_scope() as session:
        is_favorite = await repo.is_favorite(session, user_id, payload["post_url"])

    start = info.start_index + 1
    end = info.start_index + len(chunk)

    if mode == "single" and edit_in_place and previous_ids:
        caption = ui.gallery_single_caption(
            title=payload["title"], position=start, total=len(images), ttl_label=svc.deletions.ttl_label
        )
        try:
            await bot.edit_message_media(
                chat_id=chat_id,
                message_id=previous_ids[0],
                media=InputMediaPhoto(media=chunk[0], caption=caption, has_spoiler=spoiler),
                reply_markup=inline.gallery(sid, info, is_favorite=is_favorite, post_url=payload["post_url"]),
            )
            svc.sessions.update(sid, page=info.page)
            return True
        except TelegramAPIError as exc:
            log.debug("in-place gallery edit failed, sending fresh message: %s", exc)

    caption = ui.gallery_caption(
        title=payload["title"],
        start=start,
        end=end,
        total=len(images),
        page_label=info.label,
        ttl_label=svc.deletions.ttl_label,
    )
    if mode == "single":
        caption = ui.gallery_single_caption(
            title=payload["title"], position=start, total=len(images), ttl_label=svc.deletions.ttl_label
        )
    markup = inline.gallery(sid, info, is_favorite=is_favorite, post_url=payload["post_url"])

    outcome = await send_media_page(
        bot,
        chat_id,
        chunk,
        caption=caption,
        reply_markup=markup if mode == "single" else None,
        spoiler=spoiler,
        mode=mode,
        fallback=svc.settings.image_fallback_upload,
        downloader=svc.ctele.download,
    )

    if not outcome.messages:
        await bot.send_message(
            chat_id,
            ui.source_unavailable("the images could not be delivered"),
            reply_markup=inline.gallery_retry(sid, info),
        )
        return False

    if previous_ids:
        await safe_delete(bot, chat_id, previous_ids)

    if outcome.failed:
        try:
            await bot.edit_message_caption(
                chat_id=chat_id,
                message_id=outcome.messages[0].message_id,
                caption=ui.gallery_caption(
                    title=payload["title"],
                    start=start,
                    end=end,
                    total=len(images),
                    page_label=info.label,
                    ttl_label=svc.deletions.ttl_label,
                    failed=outcome.failed,
                ),
            )
        except TelegramAPIError:
            pass

    if mode != "single":
        await safe_edit_markup(bot, chat_id, outcome.messages[0].message_id, markup)

    svc.sessions.update(sid, page=info.page, message_ids=outcome.message_ids)

    await svc.deletions.schedule_messages(outcome.messages, user_id=user_id)
    return True


# ---------------------------------------------------------------------- post card

CARD_CAPTION_LIMIT = 1000


async def open_post_card(
    bot,
    chat_id: int,
    *,
    user_id: int,
    post_url: str,
    clear_ids: list[int] | None = None,
    edit_id: int | None = None,
    edit_is_photo: bool = False,
    back_label: str = "Back",
    back_data: str = "cmd:menu",
) -> str | None:
    """Show the detail card for one post and return its session id.

    Going back from a gallery rewrites that message when it can, so "Details" and "Open
    Gallery" behave as two views of one card rather than two separate posts.
    """
    svc = services()
    try:
        post = await svc.ctele.post(post_url)
    except SourceError as exc:
        await safe_delete(bot, chat_id, clear_ids or [])
        await bot.send_message(chat_id, ui.source_unavailable(str(exc)))
        return None

    async with session_scope() as session:
        is_favorite = await repo.is_favorite(session, user_id, post.url)
        setting = await repo.settings_for(session, user_id)

    sid = svc.sessions.new(
        {
            "user_id": user_id,
            "kind": "post",
            "post_url": post.url,
            "title": post.title,
            "message_ids": [],
        }
    )
    text = ui.post_card(
        title=post.title,
        upload_date=post.upload_date,
        image_count=len(post.images),
        genres=list(post.genres),
        description=post.description,
        ttl_label=svc.deletions.ttl_label,
    )
    markup = inline.post_card(
        sid,
        is_favorite=is_favorite,
        post_url=post.url,
        back_label=back_label,
        back_data=back_data,
    )

    thumbnail = post.images[0] if post.images else None
    photo_url = thumbnail if (thumbnail and setting.show_thumbnails and len(text) <= CARD_CAPTION_LIMIT) else None

    await safe_delete(bot, chat_id, _without(clear_ids, edit_id))
    message_id, is_photo = await present_card(
        bot,
        chat_id,
        text=text,
        markup=markup,
        photo_url=photo_url,
        edit_id=edit_id,
        edit_is_photo=edit_is_photo,
        prefer_caption=True,
    )

    svc.sessions.update(sid, message_ids=[message_id], is_photo=is_photo)
    if is_photo:
        await svc.deletions.schedule(
            chat_id=chat_id, message_ids=[message_id], user_id=user_id, kind="card"
        )
    return sid


# ---------------------------------------------------------------------- mirroring


async def mirror_to_log_channel(bot, text: str) -> None:
    """Copy an admin action or error to LOG_CHANNEL_ID, if configured."""
    channel = services().settings.log_channel
    if not channel:
        return
    try:
        await bot.send_message(channel, text)
    except TelegramAPIError as exc:
        log.debug("log channel mirror failed: %s", exc)


async def mirror_action(bot, *, action: str, target: str, admin_id: int, reason: str | None = None) -> None:
    await mirror_to_log_channel(
        bot,
        ui.mirror_action(
            action=action, target=target, admin_id=admin_id, reason=reason, when=utcnow()
        ),
    )


async def mirror_error(bot, *, where: str, kind: str, user_id: int | None) -> None:
    await mirror_to_log_channel(
        bot, ui.mirror_error(where=where, kind=kind, user_id=user_id, when=utcnow())
    )
