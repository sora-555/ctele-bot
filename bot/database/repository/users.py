from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_, select

from bot.database.models import Favorite, History, SavedImage, User

SEGMENTS = {
    'all': 'Active users',
    'new7': 'New in the last 7 days',
    'saved': 'Saved something',
    'never_saved': 'Never saved anything',
}


def _now():
    return datetime.now(timezone.utc)


async def upsert(session, tg_user):
    """Create the user on first sight and refresh the profile afterwards."""
    user = await session.get(User, tg_user.id)
    if user is None:
        user = User(id=tg_user.id, created_at=_now(), request_count=0, is_active=True)
        session.add(user)
    for field, value in (
        ('username', getattr(tg_user, 'username', None)),
        ('first_name', getattr(tg_user, 'first_name', None)),
        ('last_name', getattr(tg_user, 'last_name', None)),
    ):
        if getattr(user, field) != value:
            setattr(user, field, value)
    language = getattr(tg_user, 'language_code', None)
    if language and user.language_code != language:
        user.language_code = language
    user.last_seen_at = _now()
    user.request_count = (user.request_count or 0) + 1
    await session.flush()
    return user


async def get(session, user_id: int):
    return await session.get(User, user_id)


async def set_active(session, user_id: int, active: bool, admin_id: int | None = None, reason: str | None = None):
    user = await session.get(User, user_id)
    if user is None:
        return None
    user.is_active = active
    if active:
        user.blocked_reason = None
        user.blocked_by = None
        user.blocked_at = None
    else:
        user.blocked_reason = reason
        user.blocked_by = admin_id
        user.blocked_at = _now()
    await session.flush()
    return user


async def mark_bot_blocked(session, user_id: int, blocked: bool = True):
    user = await session.get(User, user_id)
    if user is not None and bool(user.bot_blocked) != blocked:
        user.bot_blocked = blocked
        await session.flush()
    return user


async def mark_blocked_by_bot(user_id: int, blocked: bool = True):
    """Session-free helper used by the broadcast engine workers."""
    from bot.database.base import SessionLocal, retry_locked

    async def write():
        async with SessionLocal() as session:
            await mark_bot_blocked(session, user_id, blocked)
            await session.commit()

    await retry_locked(write)


def _filter(query: str):
    value = (query or '').strip().lstrip('@')
    if not value:
        return None
    like = f'%{value}%'
    conditions = [
        User.username.ilike(like),
        User.first_name.ilike(like),
        User.last_name.ilike(like),
    ]
    if value.isdigit():
        conditions.append(User.id == int(value))
    return or_(*conditions)


async def search(session, query: str, limit: int = 8, offset: int = 0):
    statement = select(User)
    condition = _filter(query)
    if condition is not None:
        statement = statement.where(condition)
    total = await session.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = (await session.scalars(statement.order_by(User.last_seen_at.desc()).limit(limit).offset(offset))).all()
    return list(rows), total


async def page(session, limit: int = 8, offset: int = 0):
    return await search(session, '', limit, offset)


def segment_condition(segment: str):
    active = User.is_active.is_(True)
    if segment == 'new7':
        return active & (User.created_at >= _now() - timedelta(days=7))
    if segment == 'saved':
        return active & User.id.in_(select(Favorite.user_id))
    if segment == 'never_saved':
        return active & User.id.notin_(select(Favorite.user_id))
    return active


async def count_segment(session, segment: str) -> int:
    return await session.scalar(select(func.count()).select_from(User).where(segment_condition(segment))) or 0


async def segment_batch(session, segment: str, after: int = 0, limit: int = 200) -> list[int]:
    statement = (
        select(User.id)
        .where(segment_condition(segment), User.id > after)
        .order_by(User.id)
        .limit(limit)
    )
    return list(await session.scalars(statement))


async def user_stats(session, user_id: int) -> dict:
    favorites = await session.scalar(select(func.count()).select_from(Favorite).where(Favorite.user_id == user_id)) or 0
    images = await session.scalar(select(func.count()).select_from(SavedImage).where(SavedImage.user_id == user_id)) or 0
    viewed = await session.scalar(select(func.count()).select_from(History).where(History.user_id == user_id)) or 0
    return {'favorites': favorites, 'saved_images': images, 'history': viewed}
