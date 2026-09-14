from datetime import datetime, timezone
from sqlalchemy import select
from bot.database.models import User
async def upsert(session, tg_user):
    u=await session.get(User,tg_user.id)
    if not u: u=User(id=tg_user.id,created_at=datetime.now(timezone.utc)); session.add(u)
    u.username=tg_user.username; u.first_name=tg_user.first_name; u.last_name=tg_user.last_name; u.last_seen_at=datetime.now(timezone.utc); u.request_count=(u.request_count or 0)+1
    await session.commit(); return u
