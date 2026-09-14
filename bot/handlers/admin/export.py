"""CSV exports, delivered as a document (admins only, never auto-deleted)."""

from __future__ import annotations

import csv
import io
from datetime import datetime

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from sqlalchemy import select

from bot.database.models import Favorite, HistoryEntry, User
from bot.filters.admin import IsAdmin, RoleAtLeast
from bot.keyboards import admin as admin_kb
from bot.texts import ui
from bot.utils.time import utcnow

router = Router(name="admin-export")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

DATASETS = ("users", "favorites", "history")


def _stamp() -> str:
    return utcnow().strftime("%Y-%m-%d")


def _csv(header: list[str], rows: list[list[object]]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(header)
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8-sig")


def _iso(value: datetime | None) -> str:
    return value.isoformat(timespec="seconds") if value else ""


async def build_export(session, dataset: str) -> tuple[bytes, int, str]:
    if dataset == "favorites":
        records = (await session.execute(select(Favorite).order_by(Favorite.created_at.desc()))).scalars().all()
        payload = _csv(
            ["id", "user_id", "post_title", "post_url", "saved_at"],
            [[r.id, r.user_id, r.post_title, r.post_url, _iso(r.created_at)] for r in records],
        )
        return payload, len(records), "id, user_id, post_title, post_url, saved_at"

    if dataset == "history":
        records = (await session.execute(select(HistoryEntry).order_by(HistoryEntry.viewed_at.desc()))).scalars().all()
        payload = _csv(
            ["id", "user_id", "post_title", "post_url", "viewed_at"],
            [[r.id, r.user_id, r.post_title, r.post_url, _iso(r.viewed_at)] for r in records],
        )
        return payload, len(records), "id, user_id, post_title, post_url, viewed_at"

    records = (await session.execute(select(User).order_by(User.created_at.desc()))).scalars().all()
    payload = _csv(
        [
            "id",
            "username",
            "first_name",
            "last_name",
            "language_code",
            "is_active",
            "age_verified",
            "requests",
            "joined",
            "last_seen",
        ],
        [
            [
                r.id,
                r.username or "",
                r.first_name or "",
                r.last_name or "",
                r.language_code or "",
                r.is_active,
                r.age_verified,
                r.request_count,
                _iso(r.created_at),
                _iso(r.last_seen_at),
            ]
            for r in records
        ],
    )
    return payload, len(records), "id, username, first_name, joined, last_seen, requests, blocked"


async def deliver(bot, chat_id: int, session, dataset: str) -> None:
    payload, rows, columns = await build_export(session, dataset)
    document = BufferedInputFile(payload, filename=f"{dataset}_{_stamp()}.csv")
    await bot.send_document(
        chat_id,
        document=document,
        caption=ui.export_ready(dataset=dataset, rows=rows, columns=columns),
        reply_markup=admin_kb.back_to_admin(),
    )


@router.message(Command("export"), RoleAtLeast("admin"))
async def cmd_export(message: Message, session, user) -> None:
    from bot.database import repository as repo

    dataset = next(
        (token.lower() for token in (message.text or "").split()[1:] if token.lower() in DATASETS),
        "users",
    )
    await repo.log_action(session, admin_id=user.id, action="export", target_type="dataset", target_id=dataset)
    await deliver(message.bot, message.chat.id, session, dataset)


@router.callback_query(F.data.startswith("a:export:"), RoleAtLeast("admin"))
async def cb_export(callback: CallbackQuery, session, user) -> None:
    from bot.database import repository as repo

    dataset = callback.data.split(":")[2]
    if dataset not in DATASETS:
        dataset = "users"
    await callback.answer("Building CSV")
    await repo.log_action(session, admin_id=user.id, action="export", target_type="dataset", target_id=dataset)
    await deliver(callback.bot, callback.message.chat.id, session, dataset)
