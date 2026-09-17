from bot.database.base import SessionLocal


class DatabaseMiddleware:
    """One session and one transaction per update."""

    async def __call__(self, handler, event, data):
        async with SessionLocal() as session:
            data['db'] = session
            try:
                result = await handler(event, data)
            except Exception:
                await session.rollback()
                raise
            await session.commit()
            return result
