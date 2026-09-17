from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InputMediaPhoto, Message

from bot.keyboards.inline import gallery_kb, search_kb
from bot.services.sessions import store
from bot.states.user import InputFlow
from bot.texts.ui import gallery_caption, result_card

router = Router()


async def render_result(message, query, data, sid, index=1):
    item = data["items"][index - 1]
    data["index"] = index
    store.update(sid, data)
    text = result_card(query, item, index, data.get("page", 1))
    keyboard = search_kb(sid, index, index > 1, data.get("has_next", True))
    if item.thumbnail:
        try:
            await message.edit_media(
                InputMediaPhoto(media=item.thumbnail, caption=text, parse_mode="HTML"),
                reply_markup=keyboard,
            )
            return
        except Exception:
            pass
    try:
        await message.edit_text(text, reply_markup=keyboard)
    except Exception:
        await message.edit_caption(caption=text, reply_markup=keyboard)


async def render_result_from_state(message, data, sid, index):
    data["index"] = index
    store.update(sid, data)
    item = data["items"][index - 1]
    try:
        if data.get("media") and item.thumbnail:
            await message.bot.edit_message_media(
                chat_id=data["chat_id"],
                message_id=data["message_id"],
                media=InputMediaPhoto(
                    media=item.thumbnail,
                    caption=result_card(data["query"], item, index, data.get("page", 1)),
                    parse_mode="HTML",
                ),
                reply_markup=search_kb(sid, index, index > 1, data.get("has_next", True)),
            )
        else:
            await message.bot.edit_message_text(
                chat_id=data["chat_id"],
                message_id=data["message_id"],
                text=result_card(data["query"], item, index, data.get("page", 1)),
                reply_markup=search_kb(sid, index, index > 1, data.get("has_next", True)),
            )
    finally:
        try:
            await message.delete()
        except Exception:
            pass


async def show_listing(message: Message, page, label: str):
    if not page.items:
        return await message.answer(f"No {label.lower()} posts found.")
    data = {
        "query": label,
        "items": page.items,
        "page": page.page,
        "index": 1,
        "has_next": page.has_next,
    }
    sid = store.create(message.from_user.id, data)
    item = page.items[0]
    keyboard = search_kb(sid, 1, False, page.has_next)
    if item.thumbnail:
        sent = await message.answer_photo(
            item.thumbnail,
            caption=result_card(label, item, 1, page.page),
            parse_mode="HTML",
            reply_markup=keyboard,
        )
    else:
        sent = await message.answer(result_card(label, item, 1, page.page), reply_markup=keyboard)
    data["chat_id"], data["message_id"], data["media"] = (
        sent.chat.id,
        sent.message_id,
        bool(item.thumbnail),
    )
    store.update(sid, data)


async def run_search(message: Message, query: str, ctele, state):
    query = query.strip()
    if not query:
        await state.set_state(InputFlow.search)
        return await message.answer("Send a name, character, or keyword.")
    page = await ctele.search(query, 1)
    if not page.items:
        return await message.answer("No results. Try another search.")
    data = {
        "query": query,
        "items": page.items,
        "page": page.page,
        "index": 1,
        "has_next": page.has_next,
    }
    sid = store.create(message.from_user.id, data)
    item = page.items[0]
    keyboard = search_kb(sid, 1, False, page.has_next)
    if item.thumbnail:
        sent = await message.answer_photo(
            item.thumbnail,
            caption=result_card(query, item, 1, page.page),
            parse_mode="HTML",
            reply_markup=keyboard,
        )
    else:
        sent = await message.answer(result_card(query, item, 1, page.page), reply_markup=keyboard)
    data["chat_id"], data["message_id"], data["media"] = (
        sent.chat.id,
        sent.message_id,
        bool(item.thumbnail),
    )
    store.update(sid, data)


@router.message(Command("search"))
async def search(message: Message, ctele, state):
    await run_search(message, message.text.partition(" ")[2], ctele, state)


@router.message(InputFlow.search)
async def search_input(message: Message, state, ctele):
    await state.clear()
    await run_search(message, message.text or "", ctele, state)


@router.message(Command("latest"))
async def latest(message: Message, ctele):
    await show_listing(message, await ctele.latest(1), "Latest")


@router.callback_query(F.data == "menu:latest")
async def latest_menu(call: CallbackQuery, ctele):
    await call.answer()
    await show_listing(call.message, await ctele.latest(1), "Latest")


@router.message(Command("categories"))
async def categories(message: Message, ctele):
    rows = await ctele.categories()
    if not rows:
        return await message.answer("No categories are available right now.")
    lines = ["❖ <b>Categories</b>", "━━━━━━━━━━━━━━━━━━━━", ""]
    lines.extend(f"• {item.name}" for item in rows[:50])
    await message.answer("\n".join(lines))


@router.callback_query(F.data.startswith("s:"))
async def search_callback(call: CallbackQuery, ctele, state):
    _, sid, action, *args = call.data.split(":")
    data = store.get(sid, call.from_user.id)
    if not data:
        return await call.answer("This session expired. Start a new search.", show_alert=True)
    await call.answer()

    if action == "open":
        post = await ctele.post(data["items"][data["index"] - 1].url)
        if not post.images:
            return await call.message.edit_text("This post has no viewable images.")
        data["post"], data["image"], data["media"] = post, 1, True
        store.update(sid, data)
        media = InputMediaPhoto(
            media=post.images[0],
            caption=gallery_caption(post, 1),
            parse_mode="HTML",
        )
        try:
            await call.message.edit_media(media, reply_markup=gallery_kb(sid, 1, len(post.images)))
        except Exception:
            sent = await call.message.answer_photo(
                post.images[0],
                caption=gallery_caption(post, 1),
                parse_mode="HTML",
                reply_markup=gallery_kb(sid, 1, len(post.images)),
            )
            data["chat_id"], data["message_id"] = sent.chat.id, sent.message_id
        return

    if action == "back":
        return await render_result(call.message, data["query"], data, sid, data["index"])

    if action == "jump":
        await state.set_state(InputFlow.jump_result)
        await state.update_data(sid=sid)
        prompt = (
            f'❖ <b>Jump to a result</b>\n\nCurrent result: {data["index"]}\n'
            "Send a result number, or /cancel."
        )
        try:
            await call.message.edit_caption(
                caption=prompt,
                reply_markup=search_kb(sid, data["index"], data["index"] > 1, data.get("has_next", True)),
            )
        except Exception:
            await call.message.edit_text(
                prompt,
                reply_markup=search_kb(sid, data["index"], data["index"] > 1, data.get("has_next", True)),
            )
        return

    index = data["index"] + (-1 if action == "prev" else 1 if action == "next" else 0)
    if action == "at":
        try:
            index = int(args[0])
        except (IndexError, ValueError):
            return
    if 1 <= index <= len(data["items"]):
        async with store.lock(sid):
            await render_result(call.message, data["query"], data, sid, index)


@router.message(InputFlow.jump_result)
async def jump_result(message: Message, state):
    state_data = await state.get_data()
    sid = state_data.get("sid")
    data = store.get(sid, message.from_user.id) if sid else None
    try:
        index = int(message.text or "")
        assert data and 1 <= index <= len(data["items"])
    except (ValueError, AssertionError):
        return await message.answer("Enter a valid result number, or /cancel.")
    await state.clear()
    await render_result_from_state(message, data, sid, index)