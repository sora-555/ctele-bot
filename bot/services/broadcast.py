"""Rate-limited, resumable broadcast engine."""

import asyncio
import logging
import time
from datetime import datetime, timezone

from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError, TelegramRetryAfter
from sqlalchemy import select

from bot.config import settings
from bot.database.base import SessionLocal, retry_locked
from bot.database.models import BroadcastRun
from bot.database.repository import users as users_repo

log = logging.getLogger(__name__)

SEGMENTS = [
    ('all', 'All active users'),
    ('new7', 'New in the last 7 days'),
    ('saved', 'Saved something'),
    ('never_saved', 'Never saved anything'),
]


def now():
    return datetime.now(timezone.utc)


class BroadcastEngine:
    def __init__(self):
        self._tasks: dict[int, asyncio.Task] = {}
        self._control: dict[int, dict] = {}
        self._progress: dict[int, tuple[int, int]] = {}

    def running(self, run_id: int) -> bool:
        task = self._tasks.get(run_id)
        return task is not None and not task.done()

    def control(self, run_id: int, action: str) -> dict:
        state = self._control.setdefault(run_id, {'pause': False, 'cancel': False})
        if action == 'pause':
            state['pause'] = True
        elif action == 'resume':
            state['pause'] = False
        elif action == 'cancel':
            state['cancel'] = True
        return state

    async def count(self, segment: str) -> int:
        async with SessionLocal() as session:
            return await users_repo.count_segment(session, segment)

    async def start(self, run_id: int, bot, progress: tuple[int, int] | None = None) -> bool:
        if self.running(run_id):
            return False
        if progress is not None:
            self._progress[run_id] = progress
        self._control.setdefault(run_id, {'pause': False, 'cancel': False})
        self._tasks[run_id] = asyncio.create_task(self._run(run_id, bot))
        return True

    async def resume_pending(self, bot) -> list[int]:
        async with SessionLocal() as session:
            run_ids = list(await session.scalars(
                select(BroadcastRun.id).where(BroadcastRun.status.in_(('running', 'paused')))
            ))
        started = []
        for run_id in run_ids:
            if await self.start(run_id, bot):
                started.append(run_id)
        return started

    async def _load(self, run_id: int):
        async with SessionLocal() as session:
            return await session.get(BroadcastRun, run_id)

    async def _store(self, run_id: int, **fields):
        async def write():
            async with SessionLocal() as session:
                run = await session.get(BroadcastRun, run_id)
                if run is None:
                    return None
                for key, value in fields.items():
                    setattr(run, key, value)
                await session.commit()
                return run

        return await retry_locked(write)

    async def _send_one(self, bot, source_chat: int, source_message: int, user_id: int):
        async def deliver():
            await bot.copy_message(chat_id=user_id, from_chat_id=source_chat, message_id=source_message)

        try:
            await deliver()
            return 'sent', None
        except TelegramRetryAfter as exc:
            await asyncio.sleep(int(getattr(exc, 'retry_after', 5)) + 1)
            try:
                await deliver()
                return 'sent', None
            except TelegramForbiddenError:
                await users_repo.mark_blocked_by_bot(user_id)
                return 'blocked', None
            except Exception as error:
                return 'failed', str(error)[:120]
        except TelegramForbiddenError:
            await users_repo.mark_blocked_by_bot(user_id)
            return 'blocked', None
        except TelegramAPIError as exc:
            return 'failed', str(exc)[:120]
        except Exception as exc:
            return 'failed', str(exc)[:120]

    async def _run(self, run_id: int, bot):
        run = await self._load(run_id)
        if run is None:
            return
        source_chat, source_message, segment = run.chat_id, run.message_id, run.segment
        cursor = run.cursor or 0
        sent, failed, blocked = 0, 0, 0
        errors: list[str] = []
        last_report = 0.0
        batch_size = max(1, settings.broadcast_rate)
        try:
            while True:
                state = self._control.setdefault(run_id, {'pause': False, 'cancel': False})
                if state.get('cancel'):
                    await self._finish(run_id, bot, 'cancelled', sent, failed, blocked, cursor, errors)
                    return
                if state.get('pause'):
                    await self._store(run_id, status='paused')
                    await self._report(run_id, bot)
                    await asyncio.sleep(1.5)
                    continue
                async with SessionLocal() as session:
                    batch = await users_repo.segment_batch(session, segment, cursor, batch_size)
                if not batch:
                    await self._finish(run_id, bot, 'done', sent, failed, blocked, cursor, errors)
                    return
                started = time.monotonic()
                outcomes = await asyncio.gather(
                    *(self._send_one(bot, source_chat, source_message, user_id) for user_id in batch)
                )
                for outcome, message in outcomes:
                    if outcome == 'sent':
                        sent += 1
                    elif outcome == 'blocked':
                        blocked += 1
                    else:
                        failed += 1
                        if message and len(errors) < 5:
                            errors.append(message)
                cursor = batch[-1]
                elapsed = time.monotonic() - started
                if elapsed < 1.0:
                    await asyncio.sleep(1.0 - elapsed)
                if time.monotonic() - last_report >= 5:
                    last_report = time.monotonic()
                    await self._store(run_id, status='running', sent=sent, failed=failed, blocked=blocked, cursor=cursor)
                    await self._report(run_id, bot)
        except asyncio.CancelledError:
            await self._store(run_id, status='interrupted', sent=sent, failed=failed, blocked=blocked, cursor=cursor)
            raise
        except Exception:
            log.exception('broadcast %s failed', run_id)
            await self._finish(run_id, bot, 'failed', sent, failed, blocked, cursor, errors)

    async def _finish(self, run_id, bot, status, sent, failed, blocked, cursor, errors):
        await self._store(
            run_id,
            status=status,
            sent=sent,
            failed=failed,
            blocked=blocked,
            cursor=cursor,
            errors='\n'.join(errors)[:1000] if errors else None,
            finished_at=now(),
        )
        run = await self._load(run_id)
        if run is None:
            return
        from bot.keyboards.inline import admin_back_kb
        from bot.texts import ui

        text = ui.broadcast_summary(run)
        target = self._progress.pop(run_id, None)
        if target:
            try:
                await bot.edit_message_text(
                    chat_id=target[0],
                    message_id=target[1],
                    text=text,
                    reply_markup=admin_back_kb(),
                )
            except Exception:
                pass
        channel = settings.log_channel
        if channel is not None:
            try:
                await bot.send_message(channel, text)
            except Exception:
                log.warning('could not mirror the broadcast summary to %s', channel)

    async def _report(self, run_id, bot):
        target = self._progress.get(run_id)
        if not target:
            return
        from bot.keyboards.inline import broadcast_control_kb
        from bot.services.pagination import human_eta
        from bot.texts import ui

        run = await self._load(run_id)
        if run is None:
            return
        processed = (run.sent or 0) + (run.failed or 0) + (run.blocked or 0)
        rate = max(1, settings.broadcast_rate)
        remaining = max(0, (run.total or 0) - processed)
        text = ui.broadcast_progress(run, human_eta(remaining / rate), rate)
        try:
            await bot.edit_message_text(
                chat_id=target[0],
                message_id=target[1],
                text=text,
                reply_markup=broadcast_control_kb(run_id, paused=run.status == 'paused'),
            )
        except Exception:
            pass


engine = BroadcastEngine()
