from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.base import Base


def now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None] = mapped_column(String(255), index=True)
    first_name: Mapped[str | None] = mapped_column(String(255))
    last_name: Mapped[str | None] = mapped_column(String(255))
    language_code: Mapped[str | None] = mapped_column(String(12))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    bot_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    age_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    request_count: Mapped[int] = mapped_column(Integer, default=0)
    last_action: Mapped[str | None] = mapped_column(String(24))
    blocked_reason: Mapped[str | None] = mapped_column(String(255))
    blocked_by: Mapped[int | None] = mapped_column(BigInteger)
    blocked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    suggestion_last_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    @property
    def display_name(self) -> str:
        return " ".join(filter(None, [self.first_name, self.last_name])) or (f"@{self.username}" if self.username else str(self.id))


class Favorite(Base):
    __tablename__ = 'favorites'
    __table_args__ = (UniqueConstraint('user_id', 'post_url'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    post_url: Mapped[str] = mapped_column(String(512))
    post_title: Mapped[str] = mapped_column(String(500))
    thumbnail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SavedImage(Base):
    __tablename__ = 'saved_images'
    __table_args__ = (UniqueConstraint('user_id', 'image_url'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    post_url: Mapped[str] = mapped_column(String(512))
    post_title: Mapped[str] = mapped_column(String(500))
    image_url: Mapped[str] = mapped_column(Text)
    image_index: Mapped[int] = mapped_column(Integer, default=1)
    file_id: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class History(Base):
    __tablename__ = 'history'
    __table_args__ = (UniqueConstraint('user_id', 'post_url'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    post_url: Mapped[str] = mapped_column(String(512))
    post_title: Mapped[str] = mapped_column(String(500))
    viewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class UserSetting(Base):
    __tablename__ = 'user_settings'
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), primary_key=True)
    delivery_mode: Mapped[str] = mapped_column(String(12), default='single')
    images_per_page: Mapped[int] = mapped_column(Integer, default=5)
    show_thumbnails: Mapped[bool] = mapped_column(Boolean, default=True)
    numbered_nav: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_delete_minutes: Mapped[int | None] = mapped_column(Integer)
    favorites_tab: Mapped[str] = mapped_column(String(12), default='posts')


class Admin(Base):
    __tablename__ = 'admins'
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    role: Mapped[str] = mapped_column(String(12), default='admin')
    note: Mapped[str | None] = mapped_column(String(255))
    added_by: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class BroadcastRun(Base):
    __tablename__ = 'broadcast_runs'
    id: Mapped[int] = mapped_column(primary_key=True)
    admin_id: Mapped[int] = mapped_column(BigInteger, index=True)
    chat_id: Mapped[int] = mapped_column(BigInteger)
    message_id: Mapped[int] = mapped_column(Integer)
    segment: Mapped[str] = mapped_column(String(24), default='all')
    status: Mapped[str] = mapped_column(String(12), default='running')
    total: Mapped[int] = mapped_column(Integer, default=0)
    sent: Mapped[int] = mapped_column(Integer, default=0)
    failed: Mapped[int] = mapped_column(Integer, default=0)
    blocked: Mapped[int] = mapped_column(Integer, default=0)
    cursor: Mapped[int] = mapped_column(BigInteger, default=0)
    errors: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditLog(Base):
    __tablename__ = 'audit_log'
    id: Mapped[int] = mapped_column(primary_key=True)
    admin_id: Mapped[int] = mapped_column(BigInteger, index=True)
    action: Mapped[str] = mapped_column(String(32))
    target: Mapped[str | None] = mapped_column(String(64))
    payload: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SearchLog(Base):
    __tablename__ = 'search_log'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    query: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class TrackedMessage(Base):
    __tablename__ = 'tracked_messages'
    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger)
    message_id: Mapped[int] = mapped_column(Integer)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class BotSession(Base):
    """Viewer navigation state; one short-lived row per open screen."""

    __tablename__ = 'bot_sessions'
    sid: Mapped[str] = mapped_column(String(16), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    payload: Mapped[bytes] = mapped_column(LargeBinary)
    expires: Mapped[float] = mapped_column(Float, index=True)


class FriendInvite(Base):
    __tablename__ = 'friend_invites'
    owner_id: Mapped[int] = mapped_column(ForeignKey('users.id'), primary_key=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class FriendRequest(Base):
    __tablename__ = 'friend_requests'
    __table_args__ = (UniqueConstraint('sender_id', 'receiver_id'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    receiver_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    status: Mapped[str] = mapped_column(String(12), default='pending', index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Friendship(Base):
    __tablename__ = 'friendships'
    __table_args__ = (UniqueConstraint('user_id', 'friend_id'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    friend_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    send_allowed: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
