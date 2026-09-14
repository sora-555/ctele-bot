from html import escape

from aiogram import F, Router
from aiogram.types import CallbackQuery, InputMediaPhoto, Message

from bot.database.repository.content import toggle_favorite
from bot.keyboards.inline import gallery_kb
from bot.services.sessions import store
from bot.states.user import InputFlow
from bot.texts.ui import gallery_caption

router = Router()


@router.callback_query(F.data.startswith("g:"))
async def gallery(call: CallbackQuery, ctele, db, state):
    _, sid, action = call.data.split(":")
    data = store.get(sid, call.from_user.id)
    if not data or "post" not in data:
        return await call.answer("This session expired.", show_alert=True)

    post = data["post"]
    number = data.get("image", 1)
    total = len(post.images)
    if not total:
        return await call.answer("This post has no viewable images.", show_alert=True)

    if action == "prev":
        number -= 1
    elif action == "next":
        number += 1
    elif action == "first":
        number = 1
    elif action == "last":
        number = total
    elif action == "minus5":
        number -= 5
    elif action == "plus5":
        number += 5
    elif action == "jump":
        await call.answer()
        await call.message.edit_caption(
            caption=(
                f"❖ <b>Jump to an image</b>\n\nSend a number from 1 to {total}.\n"
                f"Current image: {number}\n\n/cancel"
            ),
            reply_markup=gallery_kb(sid, number, total),
        )
        await state.set_state(InputFlow.jump_image)
        await state.update_data(sid=sid)
        return
    elif action == "save":
        saved = await toggle_favorite(
            db,
            call.from_user.id,
            post.url,
            post.title,
            post.images[0] if post.images else None,
        )
        return await call.answer("Saved." if saved else "Removed from favorites.")
    elif action == "info":
        await call.answer()
        genres = ", ".join(escape(item) for item in post.genres) or "—"
        published = post.upload_date.strftime("%Y-%m-%d") if post.upload_date else "—"
        return await call.message.edit_caption(
            caption=(
                "❖ <b>Post information</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
                f"<b>{escape(post.title)}</b>\n\n"
                f"▸ Images: {total}\n▸ Category: {genres}\n▸ Published: {published}"
            ),
            reply_markup=gallery_kb(sid, number, total),
        )
    elif action == "back":
        from bot.handlers.browse import render_result

        await call.answer()
        return await render_result(call.message, data["query"], data, sid, data["index"])

    number = max(1, min(total, number))
    data["image"] = number
    await call.answer()
    async with store.lock(sid):
        await call.message.edit_media(
            InputMediaPhoto(
                media=post.images[number - 1],
                caption=gallery_caption(post, number),
                parse_mode="HTML",
            ),
            reply_markup=gallery_kb(sid, number, total),
        )


@router.message(InputFlow.jump_image)
async def jump_image(message: Message, state):
    state_data = await state.get_data()
    sid = state_data.get("sid")
    data = store.get(sid, message.from_user.id) if sid else None
    try:
        number = int((message.text or "").strip())
        assert data and data.get("post") and 1 <= number <= len(data["post"].images)
    except (ValueError, AssertionError):
        return await message.answer("Enter a valid image number, or /cancel.")

    data["image"] = number
    await state.clear()
    post = data["post"]
    try:
        await message.bot.edit_message_media(
            chat_id=data["chat_id"],
            message_id=data["message_id"],
            media=InputMediaPhoto(
                media=post.images[number - 1],
                caption=gallery_caption(post, number),
                parse_mode="HTML",
            ),
            reply_markup=gallery_kb(sid, number, len(post.images)),
        )
    finally:
        try:
            await message.delete()
        except Exception:
            pass