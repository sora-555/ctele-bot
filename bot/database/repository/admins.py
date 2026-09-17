import time

from sqlalchemy import select

from bot.config import settings
from bot.database.models import Admin

_CACHE: dict[int, tuple[float, bool]] = {}
_CACHE_TTL = 30.0


def invalidate(user_id: int | None = None):
    if user_id is None:
        _CACHE.clear()
    else:
        _CACHE.pop(user_id, None)


async def bootstrap(session, ids) -> int:
    created = 0
    for user_id in ids:
        if await session.get(Admin, user_id) is None:
            session.add(Admin(user_id=user_id, role='owner'))
            created += 1
    if created:
        await session.flush()
    invalidate()
    return created


async def is_admin(session, user_id: int | None) -> bool:
    if not user_id:
        return False
    if user_id in settings.admin_id_list:
        return True
    cached = _CACHE.get(user_id)
    now = time.monotonic()
    if cached and cached[0] > now:
        return cached[1]
    value = await session.get(Admin, user_id) is not None
    _CACHE[user_id] = (now + _CACHE_TTL, value)
    return value


async def is_owner(session, user_id: int | None) -> bool:
    if not user_id:
        return False
    if user_id in settings.admin_id_list:
        return True
    row = await session.get(Admin, user_id)
    return row is not None and row.role == 'owner'


async def add(session, user_id: int, role: str = 'admin', note: str | None = None, added_by: int | None = None):
    row = await session.get(Admin, user_id)
    if row is None:
        row = Admin(user_id=user_id, role=role, note=note, added_by=added_by)
        session.add(row)
    else:
        row.role = role
        if note:
            row.note = note
    await session.flush()
    invalidate(user_id)
    return row


async def remove(session, user_id: int) -> bool:
    row = await session.get(Admin, user_id)
    if row is None:
        return False
    await session.delete(row)
    await session.flush()
    invalidate(user_id)
    return True


async def list_all(session):
    rows = await session.scalars(select(Admin).order_by(Admin.created_at))
    return list(rows.all())
