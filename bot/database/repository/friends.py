from datetime import datetime, timezone

from sqlalchemy import and_, or_, select

from bot.database.models import FriendInvite, FriendRequest, Friendship, User


async def invite_for(session, owner_id: int, token: str, expires_at):
    row = await session.get(FriendInvite, owner_id)
    if row is None:
        row = FriendInvite(owner_id=owner_id, token=token, expires_at=expires_at)
        session.add(row)
    else:
        row.token = token
        row.expires_at = expires_at
        row.created_at = datetime.now(timezone.utc)
    await session.flush()
    return row


async def invite_owner(session, token: str):
    row = await session.scalar(select(FriendInvite).where(FriendInvite.token == token))
    if row is None:
        return None
    expires_at = row.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= datetime.now(timezone.utc):
        return None
    return row.owner_id


async def list_friends(session, user_id: int):
    rows = await session.execute(
        select(Friendship, User)
        .join(User, User.id == Friendship.friend_id)
        .where(Friendship.user_id == user_id)
        .order_by(User.first_name, User.last_name, User.username)
    )
    return list(rows.all())


async def friendship(session, user_id: int, friend_id: int):
    return await session.scalar(
        select(Friendship).where(Friendship.user_id == user_id, Friendship.friend_id == friend_id)
    )


async def remove_friend(session, user_id: int, friend_id: int):
    rows = await session.scalars(
        select(Friendship).where(
            or_(
                and_(Friendship.user_id == user_id, Friendship.friend_id == friend_id),
                and_(Friendship.user_id == friend_id, Friendship.friend_id == user_id),
            )
        )
    )
    for row in rows.all():
        await session.delete(row)
    await session.flush()


async def set_send_allowed(session, user_id: int, friend_id: int, allowed: bool):
    row = await friendship(session, user_id, friend_id)
    if row is not None:
        row.send_allowed = allowed
        await session.flush()


async def can_send(session, sender_id: int, receiver_id: int) -> bool:
    row = await friendship(session, receiver_id, sender_id)
    return row is not None and bool(row.send_allowed)


async def request_for(session, sender_id: int, receiver_id: int):
    return await session.scalar(
        select(FriendRequest).where(
            FriendRequest.sender_id == sender_id,
            FriendRequest.receiver_id == receiver_id,
            FriendRequest.status == 'pending',
        )
    )


async def already_friends(session, first_id: int, second_id: int) -> bool:
    return (
        await session.scalar(
            select(Friendship.id).where(
                Friendship.user_id == first_id,
                Friendship.friend_id == second_id,
            )
        )
        is not None
    )


async def create_request(session, sender_id: int, receiver_id: int):
    row = await session.scalar(
        select(FriendRequest).where(
            or_(
                and_(FriendRequest.sender_id == sender_id, FriendRequest.receiver_id == receiver_id),
                and_(FriendRequest.sender_id == receiver_id, FriendRequest.receiver_id == sender_id),
            ),
            FriendRequest.status == 'pending',
        )
    )
    if row is not None:
        return row, False
    row = FriendRequest(sender_id=sender_id, receiver_id=receiver_id)
    session.add(row)
    await session.flush()
    return row, True


async def get_request(session, request_id: int, receiver_id: int):
    return await session.scalar(
        select(FriendRequest).where(
            FriendRequest.id == request_id,
            FriendRequest.receiver_id == receiver_id,
            FriendRequest.status == 'pending',
        )
    )


async def resolve_user(session, user_id: int):
    return await session.get(User, user_id)


async def finish_request(session, row: FriendRequest, accepted: bool):
    row.status = 'accepted' if accepted else 'declined'
    if accepted:
        session.add_all(
            [
                Friendship(user_id=row.sender_id, friend_id=row.receiver_id),
                Friendship(user_id=row.receiver_id, friend_id=row.sender_id),
            ]
        )
    await session.flush()
