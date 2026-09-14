from bot.database.repository.users import upsert


class UserMiddleware:
    async def __call__(self, handler, event, data):
        user = getattr(event, "from_user", None)
        session = data.get("db")
        if user is not None and session is not None:
            data["db_user"] = await upsert(session, user)
        return await handler(event, data)
