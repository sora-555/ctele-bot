"""User records and per-user preferences."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import DELIVERY_ALBUM, User, UserSetting
from bot.utils.time import utcnow


async def get(session: AsyncSession, user_id: int) -> User | None:
    return await session.get(User, user_id)


async def get_many(session: AsyncSession, user_ids: list[int]) -> list[User]:
    if not user_ids:
        return []
    rows = await session.execute(select(User).where(User.id.in_(user_ids)))
    return list(rows.scalars().all())


async def upsert(
    session: AsyncSession,
    *,
    user_id: int,
    username: str | None,
    first_name: str | None,
    last_name: str | None,
    language_code: str | None,
    is_premium: bool = False,
    is_bot: bool = False,
) -> tuple[User, bool]:
    user = await session.get(User, user_id)
    created = False
    if user is None:
        user = User(
            id=user_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code,
            is_premium=is_premium,
            is_bot=is_bot,
            created_at=utcnow(),
            updated_at=utcnow(),
            last_seen_at=utcnow(),
        )
        session.add(user)
        created = True
    else:
        user.username = username
        user.first_name = first_name
        user.last_name = last_name
        user.language_code = language_code
        user.is_premium = is_premium
        user.last_seen_at = utcnow()
        user.updated_at = utcnow()
    await session.flush()
    return user, created


async def touch(session: AsyncSession, user_id: int) -> None:
    await session.execute(
        update(User)
        .where(User.id == user_id)
        .values(request_count=User.request_count + 1, last_seen_at=utcnow())
    )


async def mark_age_verified(session: AsyncSession, user_id: int) -> None:
    await session.execute(
        update(User).where(User.id == user_id).values(age_verified=True, age_verified_at=utcnow())
    )


async def set_blocked(
    session: AsyncSession,
    user_id: int,
    *,
    is_active: bool,
    reason: str | None = None,
    admin_id: int | None = None,
    until: datetime | None = None,
) -> None:
    await session.execute(
        update(User)
        .where(User.id == user_id)
        .values(
            is_active=is_active,
            block_reason=None if is_active else reason,
            blocked_at=None if is_active else utcnow(),
            blocked_by=None if is_active else admin_id,
            banned_until=None if is_active else until,
        )
    )


async def list_page(
    session: AsyncSession,
    *,
    page: int,
    per_page: int,
    only_blocked: bool = False,
) -> tuple[list[User], int]:
    filters = []
    if only_blocked:
        filters.append(User.is_active.is_(False))
    total = int(
        (await session.execute(select(func.count()).select_from(User).where(*filters))).scalar() or 0
    )
    stmt = (
        select(User)
        .where(*filters)
        .order_by(User.created_at.desc())
        .offset(max(page - 1, 0) * per_page)
        .limit(per_page)
    )
    rows = list((await session.execute(stmt)).scalars().all())
    return rows, total


async def search(session: AsyncSession, query: str, *, limit: int = 10) -> list[User]:
    text = query.strip()
    if not text:
        return []
    stmt = select(User)
    if text.isdigit():
        stmt = stmt.where(User.id == int(text))
    elif text.startswith("@"):
        stmt = stmt.where(func.lower(User.username) == text[1:].lower())
    else:
        like = f"%{text.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(User.username).like(like),
                func.lower(User.first_name).like(like),
                func.lower(User.last_name).like(like),
            )
        )
    stmt = stmt.order_by(User.created_at.desc()).limit(limit)
    return list((await session.execute(stmt)).scalars().all())


async def count_all(session: AsyncSession) -> int:
    return int((await session.execute(select(func.count()).select_from(User))).scalar() or 0)


async def count_active_since(session: AsyncSession, since: datetime) -> int:
    stmt = select(func.count()).select_from(User).where(User.last_seen_at >= since)
    return int((await session.execute(stmt)).scalar() or 0)


async def count_new_since(session: AsyncSession, since: datetime) -> int:
    stmt = select(func.count()).select_from(User).where(User.created_at >= since)
    return int((await session.execute(stmt)).scalar() or 0)


async def count_blocked(session: AsyncSession) -> int:
    stmt = select(func.count()).select_from(User).where(User.is_active.is_(False))
    return int((await session.execute(stmt)).scalar() or 0)


async def count_age_verified(session: AsyncSession) -> int:
    stmt = select(func.count()).select_from(User).where(User.age_verified.is_(True))
    return int((await session.execute(stmt)).scalar() or 0)


async def recipient_ids(session: AsyncSession, *, include_blocked: bool = False) -> list[int]:
    stmt = select(User.id).where(User.is_bot.is_(False))
    if not include_blocked:
        stmt = stmt.where(User.is_active.is_(True))
    return [int(row) for row in (await session.execute(stmt)).scalars().all()]


async def settings_for(session: AsyncSession, user_id: int) -> UserSetting:
    setting = await session.get(UserSetting, user_id)
    if setting is None:
        setting = UserSetting(user_id=user_id, delivery_mode=DELIVERY_ALBUM)
        session.add(setting)
        await session.flush()
    return setting


async def update_settings(session: AsyncSession, user_id: int, **values) -> UserSetting:
    setting = await settings_for(session, user_id)
    for key, value in values.items():
        if hasattr(setting, key) and value is not None:
            setattr(setting, key, value)
    setting.updated_at = utcnow()
    await session.flush()
    return setting


async def reset_settings(session: AsyncSession, user_id: int) -> UserSetting:
    return await update_settings(
        session,
        user_id,
        images_per_page=5,
        items_per_page=6,
        delivery_mode=DELIVERY_ALBUM,
        spoiler_media=False,
        show_thumbnails=True,
    )