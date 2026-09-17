from datetime import datetime, timezone

from sqlalchemy import func, select

from bot.database.models import Favorite, History, SavedImage, TrackedMessage, User


def _now():
    return datetime.now(timezone.utc)


async def toggle_favorite(session, user_id: int, url: str, title: str, thumbnail: str | None = None) -> bool:
    row = await session.scalar(select(Favorite).where(Favorite.user_id == user_id, Favorite.post_url == url))
    if row is not None:
        await session.delete(row)
        await session.flush()
        return False
    session.add(Favorite(user_id=user_id, post_url=url, post_title=(title or '')[:500], thumbnail=thumbnail))
    await session.flush()
    return True


async def is_favorite(session, user_id: int, url: str) -> bool:
    return await session.scalar(select(Favorite.id).where(Favorite.user_id == user_id, Favorite.post_url == url)) is not None


async def list_favorites(session, user_id: int, limit: int, offset: int = 0):
    total = await session.scalar(select(func.count()).select_from(Favorite).where(Favorite.user_id == user_id)) or 0
    rows = await session.scalars(
        select(Favorite)
        .where(Favorite.user_id == user_id)
        .order_by(Favorite.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(rows.all()), total


async def remove_favorite(session, user_id: int, post_url: str) -> bool:
    row = await session.scalar(select(Favorite).where(Favorite.user_id == user_id, Favorite.post_url == post_url))
    if row is None:
        return False
    await session.delete(row)
    await session.flush()
    return True


async def toggle_saved_image(session, user_id: int, post_url: str, post_title: str, image_url: str, image_index: int) -> bool:
    row = await session.scalar(select(SavedImage).where(SavedImage.user_id == user_id, SavedImage.image_url == image_url))
    if row is not None:
        await session.delete(row)
        await session.flush()
        return False
    session.add(
        SavedImage(
            user_id=user_id,
            post_url=post_url,
            post_title=(post_title or '')[:500],
            image_url=image_url,
            image_index=image_index,
        )
    )
    await session.flush()
    return True


async def is_image_saved(session, user_id: int, image_url: str) -> bool:
    return await session.scalar(select(SavedImage.id).where(SavedImage.user_id == user_id, SavedImage.image_url == image_url)) is not None


async def list_saved_images(session, user_id: int, limit: int, offset: int = 0):
    total = await session.scalar(select(func.count()).select_from(SavedImage).where(SavedImage.user_id == user_id)) or 0
    rows = await session.scalars(
        select(SavedImage)
        .where(SavedImage.user_id == user_id)
        .order_by(SavedImage.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(rows.all()), total


async def remove_saved_image(session, user_id: int, image_url: str) -> bool:
    row = await session.scalar(select(SavedImage).where(SavedImage.user_id == user_id, SavedImage.image_url == image_url))
    if row is None:
        return False
    await session.delete(row)
    await session.flush()
    return True


async def saved_image_indexes(session, user_id: int, post_url: str) -> set[int]:
    rows = await session.scalars(
        select(SavedImage.image_index).where(SavedImage.user_id == user_id, SavedImage.post_url == post_url)
    )
    return set(rows.all())


async def count_saved_images(session, user_id: int) -> int:
    return await session.scalar(select(func.count()).select_from(SavedImage).where(SavedImage.user_id == user_id)) or 0


async def count_favorites(session, user_id: int) -> int:
    return await session.scalar(select(func.count()).select_from(Favorite).where(Favorite.user_id == user_id)) or 0


async def record_view(session, user_id: int, post_url: str, post_title: str):
    row = await session.scalar(select(History).where(History.user_id == user_id, History.post_url == post_url))
    if row is None:
        if await session.get(User, user_id) is None:
            session.add(User(id=user_id, created_at=_now(), request_count=0, is_active=True))
            await session.flush()
        session.add(History(user_id=user_id, post_url=post_url, post_title=(post_title or '')[:500]))
    else:
        row.viewed_at = _now()
    await session.flush()


async def list_history(session, user_id: int, limit: int, offset: int = 0):
    total = await session.scalar(select(func.count()).select_from(History).where(History.user_id == user_id)) or 0
    rows = await session.scalars(
        select(History)
        .where(History.user_id == user_id)
        .order_by(History.viewed_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(rows.all()), total


async def remove_history(session, user_id: int, post_url: str) -> bool:


    row = await session.scalar(select(History).where(History.user_id == user_id, History.post_url == post_url))
    if row is None:
        return False
    await session.delete(row)
    await session.flush()
    return True


async def count_history(session, user_id: int) -> int:
    return await session.scalar(select(func.count()).select_from(History).where(History.user_id == user_id)) or 0


async def track_message(session, chat_id: int, message_id: int, user_id: int, minutes: int):


    from datetime import timedelta

    session.add(
        TrackedMessage(
            chat_id=chat_id,
            message_id=message_id,
            user_id=user_id,
            expires_at=_now() + timedelta(minutes=minutes),
        )
    )
    await session.flush()


async def purge_tracked(session, limit: int = 50) -> list[tuple[int, int, int]]:
    rows = await session.scalars(
        select(TrackedMessage).where(TrackedMessage.expires_at <= _now()).order_by(TrackedMessage.id).limit(limit)
    )
    entries = [(row.id, row.chat_id, row.message_id) for row in rows.all()]
    for entry_id, _chat_id, _message_id in entries:
        row = await session.get(TrackedMessage, entry_id)
        if row is not None:
            await session.delete(row)
    await session.flush()
    return entries
