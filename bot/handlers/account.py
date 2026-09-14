from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import func, select

from bot.database.models import Favorite, History, User
from bot.keyboards.inline import main_kb

router = Router()


@router.message(Command("profile"))
async def profile(message: Message, db):
    user = await db.get(User, message.from_user.id)
    if not user:
        return await message.answer("Profile is not available yet. Use /start first.")
    saves = await db.scalar(select(func.count()).select_from(Favorite).where(Favorite.user_id == user.id))
    await message.answer(
        "❖ <b>Your profile</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"ID: <code>{user.id}</code>\n"
        f"Requests: {user.request_count}\n"
        f"Saved posts: {saves or 0}\n"
        f"Status: {'active' if user.is_active else 'blocked'}"
    )


@router.message(Command("favorites"))
async def favorites(message: Message, db):
    rows = (await db.scalars(
        select(Favorite).where(Favorite.user_id == message.from_user.id).order_by(Favorite.created_at.desc())
    )).all()
    if not rows:
        return await message.answer("You have no saved posts yet.", reply_markup=main_kb())
    text = "❖ <b>Saved posts</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
    text += "\n".join(f"• <a href=\"{row.post_url}\">{row.post_title}</a>" for row in rows[:20])
    await message.answer(text)


@router.message(Command("history"))
async def history(message: Message, db):
    rows = (await db.scalars(
        select(History).where(History.user_id == message.from_user.id).order_by(History.viewed_at.desc())
    )).all()
    if not rows:
        return await message.answer("Your viewing history is empty.", reply_markup=main_kb())
    text = "❖ <b>Recently viewed</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
    text += "\n".join(f"• <a href=\"{row.post_url}\">{row.post_title}</a>" for row in rows[:20])
    await message.answer(text)


@router.message(Command("settings"))
async def settings_(message: Message):
    await message.answer(
        "❖ <b>Settings</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        "Single-image mode is active. Album mode remains an extension point."
    )


@router.message(Command("about"))
async def about(message: Message):
    await message.answer(
        "❖ <b>About CosplayTele</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        "A Telegram browser for CosplayTele galleries.\n"
        "Search and gallery controls stay on one evolving screen."
    )
