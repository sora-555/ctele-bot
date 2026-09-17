import random
import time

from ctele import CTeleClient


class CTeleService:
    """Thin, cache-aware wrapper around the external ctele SDK."""

    def __init__(self, settings):
        self.settings = settings
        headers = {"Referer": settings.source_referer} if settings.source_referer else None
        self.client = CTeleClient(
            base_url=settings.source_base_url,
            user_agent=settings.source_user_agent,
            headers=headers,
            timeout=settings.request_timeout,
            max_retries=settings.max_retries,
        )
        self._posts: dict[str, tuple[float, object]] = {}
        self._categories: tuple[float, list] | None = None

    async def close(self):
        await self.client.close()

    async def search(self, query, page=1):
        return await self.client.search(query, page)

    async def latest(self, page=1):
        return await self.client.get_latest(page)

    async def popular(self, page=0, limit=None):
        return await self.client.get_popular(page, limit=limit or self.settings.items_per_page)

    async def random_post(self):
        page = await self.popular(0, limit=20)
        items = list(page.items)
        return random.choice(items) if items else None

    async def categories(self, refresh=False):
        cached = self._categories
        if not refresh and cached and cached[0] > time.monotonic():
            return cached[1]
        rows = await self.client.get_categories(refresh=refresh)
        self._categories = (time.monotonic() + self.settings.category_cache_ttl, rows)
        return rows

    async def category(self, path, page=1):
        return await self.client.browse_category(path, page)

    async def post(self, url):
        cached = self._posts.get(url)
        now = time.monotonic()
        if cached and cached[0] > now:
            return cached[1]
        post = await self.client.get_post(url)
        if len(self._posts) > 400:
            self._posts.clear()
        self._posts[url] = (now + self.settings.post_cache_ttl, post)
        return post
