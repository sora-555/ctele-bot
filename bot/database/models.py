from datetime import datetime, timezone
from sqlalchemy import String, BigInteger, Boolean, DateTime, Integer, Text, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from bot.database.base import Base
def now(): return datetime.now(timezone.utc)
class User(Base):
    __tablename__='users'; id: Mapped[int]=mapped_column(BigInteger, primary_key=True); username: Mapped[str|None]=mapped_column(String(255)); first_name: Mapped[str|None]=mapped_column(String(255)); last_name: Mapped[str|None]=mapped_column(String(255)); is_active: Mapped[bool]=mapped_column(Boolean,default=True); age_verified: Mapped[bool]=mapped_column(Boolean,default=False); request_count: Mapped[int]=mapped_column(Integer,default=0); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now); last_seen_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class Favorite(Base):
    __tablename__='favorites'; __table_args__=(UniqueConstraint('user_id','post_url'),); id: Mapped[int]=mapped_column(primary_key=True); user_id: Mapped[int]=mapped_column(ForeignKey('users.id'),index=True); post_url: Mapped[str]=mapped_column(String(512)); post_title: Mapped[str]=mapped_column(String(500)); thumbnail: Mapped[str|None]=mapped_column(Text); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class History(Base):
    __tablename__='history'; __table_args__=(UniqueConstraint('user_id','post_url'),); id: Mapped[int]=mapped_column(primary_key=True); user_id: Mapped[int]=mapped_column(ForeignKey('users.id'),index=True); post_url: Mapped[str]=mapped_column(String(512)); post_title: Mapped[str]=mapped_column(String(500)); viewed_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class UserSetting(Base):
    __tablename__='user_settings'; user_id: Mapped[int]=mapped_column(ForeignKey('users.id'),primary_key=True); delivery_mode: Mapped[str]=mapped_column(String(12),default='single'); images_per_page: Mapped[int]=mapped_column(Integer,default=5)
