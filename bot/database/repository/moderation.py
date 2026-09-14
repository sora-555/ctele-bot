"""Moderation: block history, admin notes, audit log and scheduled deletions."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import AuditLog, Block, ScheduledDeletion, UserNote
from bot.utils.time import utcnow


async def create_block(
    session: AsyncSession,
    *,
    user_id: int,
    admin_id: int | None,
    reason: str | None,
    expires_at: datetime | None = None,
    kind: str = "block",
) -> Block:
    row = Block(
        user_id=user_id,
        admin_id=admin_id,
        reason=reason,
        expires_at=expires_at,
        is_active=True,
    )
    session.add(row)
    await session.flush()
    return row


async def lift_blocks(
    session: AsyncSession, *, user_id: int, admin_id: int | None
) -> int:
    result = await session.execute(
        update(Block)
        .where(Block.user_id == user_id, Block.is_active.is_(True))
        .values(is_active=False, lifted_at=utcnow(), lifted_by=admin_id)
    )
    await session.flush()
    return int(result.rowcount or 0)


async def active_block(session: AsyncSession, user_id: int) -> Block | None:
    stmt = (
        select(Block)
        .where(Block.user_id == user_id, Block.is_active.is_(True))
        .order_by(Block.created_at.desc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_blocks_page(
    session: AsyncSession, *, page: int, per_page: int, active_only: bool = True
) -> tuple[list[Block], int]:
    filters = [Block.is_active.is_(True)] if active_only else []
    total = int(
        (await session.execute(select(func.count()).select_from(Block).where(*filters))).scalar() or 0
    )
    stmt = (
        select(Block)
        .where(*filters)
        .order_by(Block.created_at.desc())
        .offset(max(page - 1, 0) * per_page)
        .limit(per_page)
    )
    return list((await session.execute(stmt)).scalars().all()), total


async def count_active_blocks(session: AsyncSession) -> int:
    stmt = select(func.count()).select_from(Block).where(Block.is_active.is_(True))
    return int((await session.execute(stmt)).scalar() or 0)


async def expired_block_user_ids(session: AsyncSession) -> list[int]:
    stmt = select(Block.user_id).where(
        Block.is_active.is_(True), Block.expires_at.is_not(None), Block.expires_at <= utcnow()
    )
    return [int(row) for row in (await session.execute(stmt)).scalars().all()]


async def add_note(
    session: AsyncSession, *, user_id: int, admin_id: int | None, text: str
) -> UserNote:
    row = UserNote(user_id=user_id, admin_id=admin_id, text=text[:2000])
    session.add(row)
    await session.flush()
    return row


async def list_notes(session: AsyncSession, user_id: int, *, limit: int = 20) -> list[UserNote]:
    stmt = (
        select(UserNote)
        .where(UserNote.user_id == user_id)
        .order_by(UserNote.created_at.desc())
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars().all())


async def count_notes(session: AsyncSession, user_id: int) -> int:
    stmt = select(func.count()).select_from(UserNote).where(UserNote.user_id == user_id)
    return int((await session.execute(stmt)).scalar() or 0)


async def log_action(
    session: AsyncSession,
    *,
    admin_id: int | None,
    action: str,
    target_type: str | None = None,
    target_id: str | int | None = None,
    details: dict[str, Any] | None = None,
) -> AuditLog:
    row = AuditLog(
        admin_id=admin_id,
        action=action[:48],
        target_type=target_type,
        target_id=None if target_id is None else str(target_id)[:64],
        details=details,
    )
    session.add(row)
    await session.flush()
    return row


async def list_logs_page(
    session: AsyncSession, *, page: int, per_page: int, action: str | None = None
) -> tuple[list[AuditLog], int]:
    filters = [AuditLog.action == action] if action else []
    total = int(
        (
            await session.execute(select(func.count()).select_from(AuditLog).where(*filters))
        ).scalar()
        or 0
    )
    stmt = (
        select(AuditLog)
        .where(*filters)
        .order_by(AuditLog.created_at.desc())
        .offset(max(page - 1, 0) * per_page)
        .limit(per_page)
    )
    return list((await session.execute(stmt)).scalars().all()), total


async def count_logs(session: AsyncSession) -> int:
    return int((await session.execute(select(func.count()).select_from(AuditLog))).scalar() or 0)


async def audit_actions(session: AsyncSession) -> list[str]:
    stmt = select(AuditLog.action).group_by(AuditLog.action).order_by(func.count().desc())
    return [str(row) for row in (await session.execute(stmt)).scalars().all()]


async def schedule_deletions(
    session: AsyncSession,
    *,
    chat_id: int,
    message_ids: list[int],
    user_id: int | None,
    delete_at: datetime,
    kind: str = "media",
) -> int:
    wanted = list(dict.fromkeys(message_ids))
    if not wanted:
        return 0
    # Editing a card reuses its message id, so the same message would be scheduled again
    # on every page the user walks through. Skip whatever is already queued.
    existing = set(
        (
            await session.execute(
                select(ScheduledDeletion.message_id).where(
                    ScheduledDeletion.chat_id == chat_id,
                    ScheduledDeletion.message_id.in_(wanted),
                )
            )
        )
        .scalars()
        .all()
    )
    fresh = [message_id for message_id in wanted if message_id not in existing]
    for message_id in fresh:
        session.add(
            ScheduledDeletion(
                chat_id=chat_id,
                message_id=message_id,
                user_id=user_id,
                kind=kind,
                delete_at=delete_at,
            )
        )
    await session.flush()
    return len(fresh)


async def due_deletions(
    session: AsyncSession, *, limit: int = 200
) -> list[ScheduledDeletion]:
    stmt = (
        select(ScheduledDeletion)
        .where(ScheduledDeletion.delete_at <= utcnow())
        .order_by(ScheduledDeletion.delete_at.asc())
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars().all())


async def drop_deletions(session: AsyncSession, ids: list[int]) -> None:
    if not ids:
        return
    await session.execute(delete(ScheduledDeletion).where(ScheduledDeletion.id.in_(ids)))
    await session.flush()


async def bump_deletion_attempts(session: AsyncSession, ids: list[int]) -> None:
    if not ids:
        return
    await session.execute(
        update(ScheduledDeletion)
        .where(ScheduledDeletion.id.in_(ids))
        .values(attempts=ScheduledDeletion.attempts + 1)
    )
    await session.flush()


async def count_deletions(session: AsyncSession) -> int:
    return int(
        (await session.execute(select(func.count()).select_from(ScheduledDeletion))).scalar() or 0
    )