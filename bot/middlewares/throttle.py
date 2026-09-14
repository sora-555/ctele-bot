import time
from collections import defaultdict, deque

from aiogram.types import CallbackQuery, Message


class ThrottleMiddleware:
    def __init__(self, limit: int = 6, period: float = 10):
        self.limit = limit
        self.period = period
        self._events = defaultdict(deque)

    async def __call__(self, handler, event, data):
        user = getattr(event, "from_user", None)
        if user is not None:
            now = time.monotonic()
            bucket = self._events[user.id]
            while bucket and now - bucket[0] > self.period:
                bucket.popleft()
            if len(bucket) >= self.limit:
                if isinstance(event, CallbackQuery):
                    await event.answer("Please wait a moment.", show_alert=False)
                elif isinstance(event, Message):
                    await event.answer("Please wait a moment.")
                return None
            bucket.append(now)
        return await handler(event, data)
