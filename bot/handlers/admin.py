from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select, func

from bot.config import settings
from bot.database.models import User

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in settings.admin_id_list


def denied(message: Message) -> bool:
    return not is_admin(message.from_user.id)


@router.message(Command("admin"))
async def admin(message: Message, db):
    if denied(message):
        return await message.answer("This command is restricted.")
    total = await db.scalar(select(func.count()).select_from(User)) or 0
    active = await db.scalar(select(func.count()).select_from(User).where(User.is_active.is_(True))) or 0
    await message.answer(
        "❖ <b>Admin panel</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Users: {total}\nActive: {active}\n\n"
        "/users — recent users\n"
        "/block &lt;telegram_id&gt; — block a user\n"
        "/unblock &lt;telegram_id&gt; — restore a user"
    )


@router.message(Command("users"))
async def users(message: Message, db):
    if denied(message):
        return await message.answer("This command is restricted.")
    rows = (await db.scalars(select(User).order_by(User.last_seen_at.desc()).limit(20))).all()
    if not rows:
        return await message.answer("No users yet.")
    lines = ["❖ <b>Recent users</b>", "━━━━━━━━━━━━━━━━━━━━", ""]
    lines.extend(
        f"<code>{row.id}</code> · @{row.username or '—'} · {'active' if row.is_active else 'blocked'}"
        for row in rows
    )
    await message.answer("\n".join(lines))


async def _set_active(message: Message, db, active: bool):
    if denied(message):
        return await message.answer("This command is restricted.")
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) != 2 or not parts[1].isdigit():
        return await message.answer("Usage: /block <telegram_id>" if not active else "Usage: /unblock <telegram_id>")
    user = await db.get(User, int(parts[1]))
    if not user:
        return await message.answer("User not found.")
    user.is_active = active
    await db.commit()
    await message.answer("User unblocked." if active else "User blocked.")


@router.message(Command("block"))
async def block(message: Message, db):
    await _set_active(message, db, False)


@router.message(Command("unblock"))
async def unblock(message: Message, db):
    await _set_active(message, db, True)