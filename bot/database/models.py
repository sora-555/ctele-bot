"""ORM models.

Deliberately relationship-free: every eager/lazy loader is a foot-gun under
asyncio (``MissingGreenlet``), so repositories fetch related rows with explicit
queries instead. Enumerated values are stored as plain strings.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Index,
    JSON,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.base import Base
from bot.utils.time import utcnow

ROLE_OWNER = "owner"
ROLE_ADMIN = "admin"
ROLE_MODERATOR = "moderator"
ROLES = (ROLE_OWNER, ROLE_ADMIN, ROLE_MODERATOR)
ROLE_RANK = {ROLE_MODERATOR: 1, ROLE_ADMIN: 2, ROLE_OWNER: 3}

DELIVERY_ALBUM = "album"
DELIVERY_SINGLE = "single"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    username: Mapped[str | None] = mapped_column(String(64), index=True)
    first_name: Mapped[str | None] = mapped_column(String(128))
    last_name: Mapped[str | None] = mapped_column(String(128))
    language_code: Mapped[str | None] = mapped_column(String(8))
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    is_bot: Mapped[bool] = mapped_column(Boolean, default=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    block_reason: Mapped[str | None] = mapped_column(String(256))
    blocked_at: Mapped[datetime | None] = mapped_column(DateTime)
    blocked_by: Mapped[int | None] = mapped_column(BigInteger)
    banned_until: Mapped[datetime | None] = mapped_column(DateTime, index=True)

    age_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    age_verified_at: Mapped[datetime | None] = mapped_column(DateTime)
    request_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    @property
    def display_name(self) -> str:
        parts = [self.first_name or "", self.last_name or ""]
        name = " ".join(p for p in parts if p).strip()
        return name or (f"@{self.username}" if self.username else str(self.id))

    @property
    def handle(self) -> str:
        return f"@{self.username}" if self.username else "-"


class UserSetting(Base):
    __tablename__ = "user_settings"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    images_per_page: Mapped[int] = mapped_column(Integer, default=5)
    items_per_page: Mapped[int] = mapped_column(Integer, default=6)
    delivery_mode: Mapped[str] = mapped_column(String(16), default=DELIVERY_ALBUM)
    spoiler_media: Mapped[bool] = mapped_column(Boolean, default=False)
    show_thumbnails: Mapped[bool] = mapped_column(Boolean, default=True)
    notifications: Mapped[bool] = mapped_column(Boolean, default=True)
    language: Mapped[str] = mapped_column(String(8), default="en")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class Admin(Base):
    __tablename__ = "admins"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    role: Mapped[str] = mapped_column(String(16), default=ROLE_ADMIN)
    granted_by: Mapped[int | None] = mapped_column(BigInteger)
    granted_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Block(Base):
    __tablename__ = "blocks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    admin_id: Mapped[int | None] = mapped_column(BigInteger)
    reason: Mapped[str | None] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    lifted_at: Mapped[datetime | None] = mapped_column(DateTime)
    lifted_by: Mapped[int | None] = mapped_column(BigInteger)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class UserNote(Base):
    __tablename__ = "user_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    admin_id: Mapped[int | None] = mapped_column(BigInteger)
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Favorite(Base):
    __tablename__ = "favorites"
    __table_args__ = (
        UniqueConstraint("user_id", "post_url", name="uq_favorite_user_post"),
        Index("ix_favorites_user_created", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    post_url: Mapped[str] = mapped_column(String(512))
    post_title: Mapped[str] = mapped_column(String(512))
    thumbnail: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class HistoryEntry(Base):
    __tablename__ = "history"
    __table_args__ = (
        UniqueConstraint("user_id", "post_url", name="uq_history_user_post"),
        Index("ix_history_user_viewed", "user_id", "viewed_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    post_url: Mapped[str] = mapped_column(String(512))
    post_title: Mapped[str] = mapped_column(String(512))
    thumbnail: Mapped[str | None] = mapped_column(String(512))
    viewed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class PostCache(Base):
    __tablename__ = "post_cache"

    url: Mapped[str] = mapped_column(String(512), primary_key=True)
    title: Mapped[str] = mapped_column(String(512))
    description: Mapped[str | None] = mapped_column(Text)
    genres: Mapped[list[str]] = mapped_column(JSON, default=list)
    upload_date: Mapped[datetime | None] = mapped_column(DateTime)
    images: Mapped[list[str]] = mapped_column(JSON, default=list)
    image_count: Mapped[int] = mapped_column(Integer, default=0)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    hits: Mapped[int] = mapped_column(Integer, default=0)


class CategoryCache(Base):
    __tablename__ = "category_cache"

    path: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    position: Mapped[int] = mapped_column(Integer, default=0)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    admin_id: Mapped[int | None] = mapped_column(BigInteger, index=True)
    action: Mapped[str] = mapped_column(String(48), index=True)
    target_type: Mapped[str | None] = mapped_column(String(32))
    target_id: Mapped[str | None] = mapped_column(String(64))
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class Broadcast(Base):
    __tablename__ = "broadcasts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    admin_id: Mapped[int | None] = mapped_column(BigInteger)
    kind: Mapped[str] = mapped_column(String(16), default="text")
    content: Mapped[str | None] = mapped_column(Text)
    file_id: Mapped[str | None] = mapped_column(String(512))
    parse_mode: Mapped[str | None] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), default="draft", index=True)
    total: Mapped[int] = mapped_column(Integer, default=0)
    sent_ok: Mapped[int] = mapped_column(Integer, default=0)
    sent_fail: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)


class DailyStat(Base):
    __tablename__ = "daily_stats"

    day: Mapped[date] = mapped_column(Date, primary_key=True)
    new_users: Mapped[int] = mapped_column(Integer, default=0)
    active_users: Mapped[int] = mapped_column(Integer, default=0)
    requests: Mapped[int] = mapped_column(Integer, default=0)
    blocks: Mapped[int] = mapped_column(Integer, default=0)
    broadcasts: Mapped[int] = mapped_column(Integer, default=0)


class ScheduledDeletion(Base):
    __tablename__ = "scheduled_deletions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, index=True)
    message_id: Mapped[int] = mapped_column(BigInteger, index=True)
    user_id: Mapped[int | None] = mapped_column(BigInteger)
    kind: Mapped[str] = mapped_column(String(16), default="media")
    delete_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    attempts: Mapped[int] = mapped_column(Integer, default=0)


class Meta(Base):
    __tablename__ = "meta"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str | None] = mapped_column(Text)