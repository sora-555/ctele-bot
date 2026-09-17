import logging

from aiogram.types import CallbackQuery, Message

from bot.database.repository.users import upsert

log = logging.getLogger(__name__)

BLOCKED_TEXT = "This bot is not available for your account."
MAINTENANCE_TEXT = "The bot is under maintenance right now. Please try again later."


def resolve_user(event):
    """Return the Telegram user behind an update or a bare event object.

    Outer middlewares on dp.update receive an Update wrapper, which has no
    from_user of its own, so the inner event is unwrapped first.
    """
    user = getattr(event, "from_user", None)
    if user is not None:
        return user
    return getattr(getattr(event, "event", None), "from_user", None)


def inner_event(event):
    return getattr(event, "event", None) or event


async def notice(event, text: str):
    target = inner_event(event)
    if isinstance(target, CallbackQuery):
        await target.answer(text, show_alert=True)
    elif isinstance(target, Message):
        await target.answer(text)


class UserMiddleware:
    """Provision the user on any interaction, then apply the access gate."""

    async def __call__(self, handler, event, data):
        tg_user = resolve_user(event)
        session = data.get("db")
        if tg_user is None or session is None:
            return await handler(event, data)
        try:
            user = await upsert(session, tg_user)
        except Exception:
            log.exception("could not provision user %s", tg_user.id)
            return await handler(event, data)
        data["user"] = user
        data["db_user"] = user
        if not user.is_active:
            await notice(event, BLOCKED_TEXT)
            return None
        return await handler(event, data)
