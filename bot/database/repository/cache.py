"""Persistent caches: post detail (so galleries cost one fetch) and taxonomy."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import CategoryCache, PostCache
from bot.utils.time import utcnow


def _fresh(fetched_at: datetime | None, ttl_seconds: int) -> bool:
    if fetched_at is None:
        return False
    return (utcnow() - fetched_at).total_seconds() <= ttl_seconds


async def get_post(session: AsyncSession, url: str, *, ttl_seconds: int) -> PostCache | None:
    row = await session.get(PostCache, url)
    if row is None or not _fresh(row.fetched_at, ttl_seconds):
        return None
    row.hits += 1
    await session.flush()
    return row


async def put_post(
    session: AsyncSession,
    *,
    url: str,
    title: str,
    description: str | None,
    genres: list[str],
    upload_date: datetime | None,
    images: list[str],
) -> PostCache:
    row = await session.get(PostCache, url)
    if row is None:
        row = PostCache(url=url)
        session.add(row)
    row.title = title
    row.description = description
    row.genres = list(genres or [])
    row.upload_date = upload_date
    row.images = list(images or [])
    row.image_count = len(images or [])
    row.fetched_at = utcnow()
    await session.flush()
    return row


async def get_categories(session: AsyncSession, *, ttl_seconds: int) -> list[CategoryCache]:
    rows = list(
        (await session.execute(select(CategoryCache).order_by(CategoryCache.position.asc())))
        .scalars()
        .all()
    )
    if not rows or not _fresh(rows[0].fetched_at, ttl_seconds):
        return []
    return rows


async def replace_categories(
    session: AsyncSession, categories: list[tuple[str, str]]
) -> None:
    """Replace the cached taxonomy.

    The source can list the same path more than once, and `path` is the primary
    key, so duplicates are dropped (first occurrence wins) before inserting.
    """
    await session.execute(delete(CategoryCache))
    now = utcnow()
    seen: set[str] = set()
    position = 0
    for name, path in categories:
        key = (path or "").strip()[:255]
        if not key or key in seen:
            continue
        seen.add(key)
        session.add(
            CategoryCache(path=key, name=name[:255], position=position, fetched_at=now)
        )
        position += 1
    await session.flush()


async def clear_listingless(session: AsyncSession) -> None:
    await session.execute(delete(PostCache))


async def cache_stats(session: AsyncSession) -> dict[str, int]:
    posts = int((await session.execute(select(func.count()).select_from(PostCache))).scalar() or 0)
    hits = int(
        (await session.execute(select(func.coalesce(func.sum(PostCache.hits), 0)))).scalar() or 0
    )
    categories = int(
        (await session.execute(select(func.count()).select_from(CategoryCache))).scalar() or 0
    )
    return {"posts": posts, "hits": hits, "categories": categories}


async def clear(session: AsyncSession) -> dict[str, int]:
    before = await cache_stats(session)
    await session.execute(delete(PostCache))
    await session.execute(delete(CategoryCache))
    await session.flush()
    return before