from bot.config import settings
from bot.database.repository.admins import is_admin
from bot.middlewares.user import MAINTENANCE_TEXT, notice, resolve_user


class AccessMiddleware:
    """Maintenance switch: admins keep working, everyone else gets a notice."""

    async def __call__(self, handler, event, data):
        if not settings.maintenance:
            return await handler(event, data)
        tg_user = resolve_user(event)
        session = data.get("db")
        if tg_user is None or session is None:
            return await handler(event, data)
        if await is_admin(session, tg_user.id):
            return await handler(event, data)
        await notice(event, MAINTENANCE_TEXT)
        return None
