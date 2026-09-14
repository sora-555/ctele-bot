"""Daily counters, kept cheap so /astats never runs a heavy aggregate."""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import DailyStat
from bot.utils.time import utcnow


def today() -> date:
    return utcnow().date()


async def touch(
    session: AsyncSession,
    *,
    day: date | None = None,
    new_users: int = 0,
    active_users: int = 0,
    requests: int = 0,
    blocks: int = 0,
    broadcasts: int = 0,
) -> None:
    target = day or today()
    row = await session.get(DailyStat, target)
    if row is None:
        row = DailyStat(day=target, new_users=0, active_users=0, requests=0, blocks=0, broadcasts=0)
        session.add(row)
    row.new_users += new_users
    row.active_users += active_users
    row.requests += requests
    row.blocks += blocks
    row.broadcasts += broadcasts
    await session.flush()


async def get_day(session: AsyncSession, day: date) -> DailyStat | None:
    return await session.get(DailyStat, day)


async def recent(session: AsyncSession, *, days: int = 7) -> list[DailyStat]:
    floor = today() - timedelta(days=days - 1)
    stmt = select(DailyStat).where(DailyStat.day >= floor).order_by(DailyStat.day.asc())
    return list((await session.execute(stmt)).scalars().all())


async def totals(session: AsyncSession) -> dict[str, int]:
    stmt = select(
        func.coalesce(func.sum(DailyStat.requests), 0),
        func.coalesce(func.sum(DailyStat.new_users), 0),
        func.coalesce(func.sum(DailyStat.blocks), 0),
        func.coalesce(func.sum(DailyStat.broadcasts), 0),
    )
    requests, new_users, blocks, broadcasts = (await session.execute(stmt)).one()
    return {
        "requests": int(requests),
        "new_users": int(new_users),
        "blocks": int(blocks),
        "broadcasts": int(broadcasts),
    }