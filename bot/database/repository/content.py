"""Per-user content: favorites and view history."""

from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import Favorite, HistoryEntry
from bot.utils.time import utcnow


async def is_favorite(session: AsyncSession, user_id: int, post_url: str) -> bool:
    stmt = select(Favorite.id).where(Favorite.user_id == user_id, Favorite.post_url == post_url)
    return (await session.execute(stmt)).first() is not None


async def add_favorite(
    session: AsyncSession, *, user_id: int, post_url: str, title: str, thumbnail: str | None
) -> None:
    existing = (
        await session.execute(
            select(Favorite).where(Favorite.user_id == user_id, Favorite.post_url == post_url)
        )
    ).scalar_one_or_none()
    if existing is not None:
        return
    session.add(
        Favorite(
            user_id=user_id,
            post_url=post_url,
            post_title=title[:512],
            thumbnail=thumbnail,
        )
    )
    await session.flush()


async def remove_favorite(session: AsyncSession, *, user_id: int, post_url: str) -> bool:
    result = await session.execute(
        delete(Favorite).where(Favorite.user_id == user_id, Favorite.post_url == post_url)
    )
    await session.flush()
    return bool(result.rowcount)


async def remove_favorite_by_id(session: AsyncSession, *, user_id: int, favorite_id: int) -> bool:
    result = await session.execute(
        delete(Favorite).where(Favorite.id == favorite_id, Favorite.user_id == user_id)
    )
    await session.flush()
    return bool(result.rowcount)


async def toggle_favorite(
    session: AsyncSession, *, user_id: int, post_url: str, title: str, thumbnail: str | None
) -> bool:
    """Returns True when the post ended up saved."""
    if await is_favorite(session, user_id, post_url):
        await remove_favorite(session, user_id=user_id, post_url=post_url)
        return False
    await add_favorite(
        session, user_id=user_id, post_url=post_url, title=title, thumbnail=thumbnail
    )
    return True


async def list_favorites(
    session: AsyncSession, user_id: int, *, page: int, per_page: int
) -> tuple[list[Favorite], int]:
    total = int(
        (
            await session.execute(
                select(func.count()).select_from(Favorite).where(Favorite.user_id == user_id)
            )
        ).scalar()
        or 0
    )
    stmt = (
        select(Favorite)
        .where(Favorite.user_id == user_id)
        .order_by(Favorite.created_at.desc())
        .offset(max(page - 1, 0) * per_page)
        .limit(per_page)
    )
    return list((await session.execute(stmt)).scalars().all()), total


async def count_favorites(session: AsyncSession, user_id: int) -> int:
    stmt = select(func.count()).select_from(Favorite).where(Favorite.user_id == user_id)
    return int((await session.execute(stmt)).scalar() or 0)


async def record_view(
    session: AsyncSession, *, user_id: int, post_url: str, title: str, thumbnail: str | None
) -> None:
    row = (
        await session.execute(
            select(HistoryEntry).where(
                HistoryEntry.user_id == user_id, HistoryEntry.post_url == post_url
            )
        )
    ).scalar_one_or_none()
    if row is None:
        session.add(
            HistoryEntry(
                user_id=user_id,
                post_url=post_url,
                post_title=title[:512],
                thumbnail=thumbnail,
                viewed_at=utcnow(),
            )
        )
    else:
        row.viewed_at = utcnow()
        row.post_title = title[:512]
        row.thumbnail = thumbnail
    await session.flush()


async def list_history(
    session: AsyncSession, user_id: int, *, page: int, per_page: int
) -> tuple[list[HistoryEntry], int]:
    total = int(
        (
            await session.execute(
                select(func.count()).select_from(HistoryEntry).where(HistoryEntry.user_id == user_id)
            )
        ).scalar()
        or 0
    )
    stmt = (
        select(HistoryEntry)
        .where(HistoryEntry.user_id == user_id)
        .order_by(HistoryEntry.viewed_at.desc())
        .offset(max(page - 1, 0) * per_page)
        .limit(per_page)
    )
    return list((await session.execute(stmt)).scalars().all()), total


async def count_history(session: AsyncSession, user_id: int) -> int:
    stmt = select(func.count()).select_from(HistoryEntry).where(HistoryEntry.user_id == user_id)
    return int((await session.execute(stmt)).scalar() or 0)


async def clear_history(session: AsyncSession, user_id: int) -> int:
    result = await session.execute(delete(HistoryEntry).where(HistoryEntry.user_id == user_id))
    await session.flush()
    return int(result.rowcount or 0)


async def prune_history(session: AsyncSession, user_id: int, *, keep: int = 100) -> None:
    newest = (
        select(HistoryEntry.id)
        .where(HistoryEntry.user_id == user_id)
        .order_by(HistoryEntry.viewed_at.desc())
        .limit(keep)
    )
    await session.execute(
        delete(HistoryEntry).where(
            HistoryEntry.user_id == user_id, HistoryEntry.id.notin_(newest)
        )
    )
    await session.flush()

async def count_all_favorites(session: AsyncSession) -> int:
    return int((await session.execute(select(func.count()).select_from(Favorite))).scalar() or 0)


async def count_all_history(session: AsyncSession) -> int:
    return int((await session.execute(select(func.count()).select_from(HistoryEntry))).scalar() or 0)