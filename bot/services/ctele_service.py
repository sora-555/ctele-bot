"""Async wrapper around the ctele SDK.

Adds the three things the SDK deliberately leaves to its caller: a global
concurrency cap, retries with backoff, and caching (in-memory for listings,
SQLite for post detail so paging a gallery costs a single fetch).
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import OrderedDict

from ctele import CTeleClient
from ctele.exceptions import CTeleError, RequestError
from ctele.models import Category, Post, PostSummary

from bot.config import Settings
from bot.database import repository as repo
from bot.database.base import session_scope

log = logging.getLogger(__name__)


class ListingResult:
    __slots__ = ("items", "page", "has_next", "cached")

    def __init__(self, items: list[PostSummary], page: int, has_next: bool, cached: bool = False):
        self.items = items
        self.page = page
        self.has_next = has_next
        self.cached = cached

    def __len__(self) -> int:
        return len(self.items)


class SourceError(Exception):
    """Any failure coming out of the source, already made human-readable."""

    def __init__(self, message: str, *, transient: bool = True):
        super().__init__(message)
        self.transient = transient


class CTeleService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        kwargs: dict = {
            "timeout": settings.request_timeout,
            "max_retries": 0,  # retries are handled here so backoff is ours
        }
        if settings.source_user_agent:
            kwargs["user_agent"] = settings.source_user_agent
        if settings.source_referer:
            kwargs["headers"] = {"Referer": settings.source_referer}
        self._client = CTeleClient(settings.source_base_url, **kwargs)
        self._semaphore = asyncio.Semaphore(max(settings.source_concurrency, 1))
        self._cache: OrderedDict[str, tuple[float, ListingResult]] = OrderedDict()
        self.last_error: str | None = None
        self.request_count = 0

    async def close(self) -> None:
        await self._client.close()

    # ------------------------------------------------------------------ internals

    async def _call(self, factory, *args, **kwargs):
        attempts = max(self._settings.max_retries, 0) + 1
        last: Exception | None = None
        for attempt in range(attempts):
            try:
                async with self._semaphore:
                    result = await factory(*args, **kwargs)
                self.request_count += 1
                self.last_error = None
                return result
            except RequestError as exc:
                last = exc
                if attempt < attempts - 1:
                    await asyncio.sleep(0.4 * (attempt + 1))
            except CTeleError as exc:
                last = exc
                break
        message = str(last) if last else "unknown source error"
        self.last_error = message
        log.warning("source call failed: %s", message)
        raise SourceError(message, transient=isinstance(last, RequestError))

    def _cache_get(self, key: str) -> ListingResult | None:
        entry = self._cache.get(key)
        if entry is None:
            return None
        stored_at, result = entry
        if time.monotonic() - stored_at > self._settings.listing_cache_ttl:
            self._cache.pop(key, None)
            return None
        self._cache.move_to_end(key)
        return ListingResult(result.items, result.page, result.has_next, cached=True)

    def _cache_put(self, key: str, result: ListingResult) -> None:
        if not result.items:
            return
        self._cache[key] = (time.monotonic(), result)
        self._cache.move_to_end(key)
        while len(self._cache) > 256:
            self._cache.popitem(last=False)

    def clear_cache(self) -> int:
        size = len(self._cache)
        self._cache.clear()
        return size

    async def _listing(self, key: str, factory, page: int) -> ListingResult:
        cached = self._cache_get(key)
        if cached is not None:
            return cached
        source_page = await self._call(factory)
        result = ListingResult(list(source_page.items), page, bool(source_page.has_next))
        self._cache_put(key, result)
        return result

    # ------------------------------------------------------------------ listings

    async def latest(self, page: int = 1) -> ListingResult:
        page = max(page, 1)
        return await self._listing(f"latest:{page}", lambda: self._client.get_latest(page), page)

    async def popular(self, page: int = 0, *, time_range: str = "last7days") -> ListingResult:
        page = max(page, 0)
        return await self._listing(
            f"popular:{time_range}:{page}",
            lambda: self._client.get_popular(page, time_range=time_range),
            page + 1,
        )

    async def search(self, query: str, page: int = 1) -> ListingResult:
        page = max(page, 1)
        return await self._listing(
            f"search:{query.strip().lower()}:{page}",
            lambda: self._client.search(query, page),
            page,
        )

    async def category(self, path: str, page: int = 1) -> ListingResult:
        page = max(page, 1)
        return await self._listing(
            f"category:{path.strip().lower()}:{page}",
            lambda: self._client.browse_category(path, page),
            page,
        )

    async def categories(self, *, refresh: bool = False) -> list[Category]:
        async with session_scope() as session:
            if not refresh:
                stored = await repo.get_categories(
                    session, ttl_seconds=self._settings.category_cache_ttl
                )
                if stored:
                    return [Category(name=row.name, path=row.path) for row in stored]
        categories = await self._call(self._client.get_categories, refresh=refresh)
        unique: list[tuple[str, str]] = []
        seen: set[str] = set()
        for category in categories:
            path = (category.path or "").strip()
            if not path or path in seen:
                continue
            seen.add(path)
            unique.append((category.name, path))
        if unique:
            async with session_scope() as session:
                await repo.replace_categories(session, unique)
        return [Category(name=name, path=path) for name, path in unique]

    async def random_post(self) -> PostSummary | None:
        import random

        page = random.randint(1, 3)
        result = await self.latest(page)
        return random.choice(result.items) if result.items else None

    # ------------------------------------------------------------------ post detail

    async def post(self, url: str, *, refresh: bool = False) -> Post:
        if not refresh:
            async with session_scope() as session:
                cached = await repo.get_post(
                    session, url, ttl_seconds=self._settings.post_cache_ttl
                )
                if cached is not None:
                    return Post(
                        title=cached.title,
                        url=cached.url,
                        description=cached.description,
                        genres=list(cached.genres or []),
                        upload_date=cached.upload_date,
                        images=list(cached.images or []),
                    )
        post = await self._call(self._client.get_post, url)
        async with session_scope() as session:
            await repo.put_post(
                session,
                url=post.url,
                title=post.title,
                description=post.description,
                genres=post.genres,
                upload_date=post.upload_date,
                images=post.images,
            )
        return post

    async def images(self, url: str) -> list[str]:
        return list((await self.post(url)).images)

    async def download(self, url: str) -> bytes:
        return await self._call(self._client.download_image, url)

    async def health(self) -> tuple[bool, int | None, str | None]:
        started = time.perf_counter()
        try:
            await self._call(self._client.get_latest, 1)
        except SourceError as exc:
            return False, None, str(exc)
        return True, int((time.perf_counter() - started) * 1000), None