"""Admin roles. `ADMIN_IDS` from the environment is bootstrap-only."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import ROLE_OWNER, Admin


async def get_role(session: AsyncSession, user_id: int) -> str | None:
    row = await session.get(Admin, user_id)
    return row.role if row else None


async def grant(
    session: AsyncSession, *, user_id: int, role: str, granted_by: int | None = None
) -> Admin:
    row = await session.get(Admin, user_id)
    if row is None:
        row = Admin(user_id=user_id, role=role, granted_by=granted_by)
        session.add(row)
    else:
        row.role = role
        row.granted_by = granted_by
    await session.flush()
    return row


async def revoke(session: AsyncSession, user_id: int) -> bool:
    row = await session.get(Admin, user_id)
    if row is None:
        return False
    await session.delete(row)
    await session.flush()
    return True


async def list_all(session: AsyncSession) -> list[Admin]:
    rows = await session.execute(select(Admin).order_by(Admin.granted_at.asc()))
    return list(rows.scalars().all())


async def all_ids(session: AsyncSession) -> list[int]:
    return [int(row) for row in (await session.execute(select(Admin.user_id))).scalars().all()]


async def owners(session: AsyncSession) -> list[int]:
    stmt = select(Admin.user_id).where(Admin.role == ROLE_OWNER)
    return [int(row) for row in (await session.execute(stmt)).scalars().all()]


async def count_by_role(session: AsyncSession) -> dict[str, int]:
    stmt = select(Admin.role, func.count()).group_by(Admin.role)
    return {str(role): int(count) for role, count in (await session.execute(stmt)).all()}


async def bootstrap(session: AsyncSession, owner_ids: list[int]) -> int:
    """Insert the configured owners if they are not admins yet."""
    added = 0
    for user_id in owner_ids:
        if await session.get(Admin, user_id) is None:
            session.add(Admin(user_id=user_id, role=ROLE_OWNER, granted_by=None))
            added += 1
    await session.flush()
    return added