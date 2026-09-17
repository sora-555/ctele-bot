import time
from collections import defaultdict, deque

from aiogram.types import CallbackQuery

from bot.config import settings
from bot.middlewares.user import inner_event, resolve_user

WARN_TEXT = "Please slow down for a moment."


class ThrottleMiddleware:
    def __init__(self, limit: int | None = None, period: float | None = None):
        self.limit = limit or settings.throttle_rate
        self.period = period or settings.throttle_period
        self._buckets = defaultdict(deque)

    async def __call__(self, handler, event, data):
        tg_user = resolve_user(event)
        if tg_user is None:
            return await handler(event, data)
        target = inner_event(event)
        kind = "callback" if isinstance(target, CallbackQuery) else "message"
        bucket = self._buckets[(tg_user.id, kind)]
        now = time.monotonic()
        while bucket and now - bucket[0] > self.period:
            bucket.popleft()
        if len(bucket) >= self.limit:
            if isinstance(target, CallbackQuery):
                await target.answer(WARN_TEXT, show_alert=False)
            elif hasattr(target, "answer"):
                await target.answer(WARN_TEXT)
            return None
        bucket.append(now)
        return await handler(event, data)
