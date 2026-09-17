from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from bot.database.models import AuditLog, BroadcastRun, Favorite, History, SavedImage, SearchLog, User


def _now():
    return datetime.now(timezone.utc)


async def _count(session, model, *conditions) -> int:
    return await session.scalar(select(func.count()).select_from(model).where(*conditions)) or 0


async def overview(session) -> dict:
    now = _now()
    day = now - timedelta(days=1)
    week = now - timedelta(days=7)
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return {
        'total': await _count(session, User),
        'active': await _count(session, User, User.is_active.is_(True)),
        'bot_blocked': await _count(session, User, User.bot_blocked.is_(True)),
        'new_today': await _count(session, User, User.created_at >= midnight),
        'new_week': await _count(session, User, User.created_at >= week),
        'dau': await _count(session, User, User.last_seen_at >= day),
        'wau': await _count(session, User, User.last_seen_at >= week),
        'favorites': await _count(session, Favorite),
        'saved_images': await _count(session, SavedImage),
        'history': await _count(session, History),
    }


async def top_saved_posts(session, limit: int = 10):
    rows = await session.execute(
        select(Favorite.post_title, func.count().label('total'))
        .group_by(Favorite.post_title)
        .order_by(func.count().desc())
        .limit(limit)
    )
    return [(title, total) for title, total in rows.all()]


async def top_queries(session, limit: int = 10):
    rows = await session.execute(
        select(SearchLog.query, func.count().label('total'))
        .group_by(SearchLog.query)
        .order_by(func.count().desc())
        .limit(limit)
    )
    return [(query, total) for query, total in rows.all()]


async def user_search_history(session, user_id: int, limit: int = 20):
    rows = await session.scalars(
        select(SearchLog)
        .where(SearchLog.user_id == user_id)
        .order_by(SearchLog.created_at.desc())
        .limit(limit)
    )
    return list(rows.all())


async def log_search(session, user_id: int, query: str):
    value = (query or '').strip()[:255]
    if value:
        session.add(SearchLog(user_id=user_id, query=value))
        await session.flush()


async def audit(session, admin_id: int, action: str, target=None, payload: str | None = None):
    session.add(
        AuditLog(
            admin_id=admin_id,
            action=action[:32],
            target=str(target)[:64] if target is not None else None,
            payload=payload,
        )
    )
    await session.flush()


async def recent_audit(session, limit: int = 12):
    rows = await session.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(limit))
    return list(rows.all())


async def recent_broadcasts(session, limit: int = 5):
    rows = await session.scalars(select(BroadcastRun).order_by(BroadcastRun.id.desc()).limit(limit))
    return list(rows.all())
