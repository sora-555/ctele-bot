from bot.database.base import SessionLocal


class DatabaseMiddleware:
    async def __call__(self, handler, event, data):
        async with SessionLocal() as session:
            data["db"] = session
            return await handler(event, data)
