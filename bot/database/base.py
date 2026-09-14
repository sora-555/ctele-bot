from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from bot.config import settings
class Base(DeclarativeBase): pass
engine = create_async_engine(settings.database_url, echo=False)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
async def init_db():
    from bot.database import models
    async with engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)
