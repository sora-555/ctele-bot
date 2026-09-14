"""Async client for CosplayTele.

Wraps the endpoints reverse-engineered from the site's Keiyoushi
extension in a small, framework-agnostic `httpx`-based client. Works
standing alone, as a FastAPI dependency, or inside an aiogram handler —
see examples/ for both.
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator
from urllib.parse import urlparse, urlsplit, urlunsplit

import httpx

from ._constants import (
    BASE_URL,
    DEFAULT_CATEGORIES,
    DEFAULT_PAGE_SIZE,
    DEFAULT_POPULAR_RANGE,
    DEFAULT_USER_AGENT,
    REQUEST_TIMEOUT,
)
from .exceptions import ParseError, RequestError
from .models import Category, Page, Post, PostSummary
from .parsing import parse_categories, parse_listing, parse_popular_json, parse_post, path_is_taxonomy


class CTeleClient:
    """Async client for cosplaytele.com.

    Own its HTTP client (default) or bring your own `httpx.AsyncClient`
    to share connection pooling with the rest of your app::

        # standalone
        async with CTeleClient() as ctele:
            ...

        # sharing a client you already manage (FastAPI app state, etc.)
        ctele = CTeleClient(client=my_shared_httpx_client)
    """

    def __init__(
        self,
        base_url: str = BASE_URL,
        *,
        client: httpx.AsyncClient | None = None,
        headers: dict[str, str] | None = None,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout: float = REQUEST_TIMEOUT,
        max_retries: int = 2,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._owns_client = client is None
        self._max_retries = max_retries
        self._categories_cache: list[Category] | None = None

        # The extension's headersBuilder() adds Referer on every request —
        # most WP hotlink-protection plugins gate on exactly this header.
        merged_headers = {
            "User-Agent": user_agent,
            "Referer": f"{self.base_url}/",
        }
        if headers:
            merged_headers.update(headers)

        self._client = client or httpx.AsyncClient(
            timeout=timeout, headers=merged_headers, follow_redirects=True
        )

    async def __aenter__(self) -> "CTeleClient":
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the underlying HTTP client — a no-op if you passed your
        own `httpx.AsyncClient` in (you own its lifecycle in that case).
        """
        if self._owns_client:
            await self._client.aclose()

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------

    async def _get(self, url: str, *, params: dict | None = None) -> httpx.Response:
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                response = await self._client.get(url, params=params)
            except httpx.TransportError as exc:
                last_error = exc
                continue
            if response.status_code >= 500 and attempt < self._max_retries:
                last_error = RequestError(
                    "server error", url=str(response.url), status_code=response.status_code
                )
                continue
            if response.status_code >= 400:
                raise RequestError(
                    "request failed", url=str(response.url), status_code=response.status_code
                )
            return response
        if isinstance(last_error, RequestError):
            raise last_error
        raise RequestError(f"network error: {last_error}", url=url)

    def _resolve(self, url_or_path: str) -> str:
        """Turn a bare path or a full URL into a full URL on this site."""
        if url_or_path.startswith(("http://", "https://")):
            return url_or_path
        return f"{self.base_url}/{url_or_path.lstrip('/')}"

    def _own_host(self) -> str:
        return urlparse(self.base_url).hostname or ""

    # ------------------------------------------------------------------
    # listings
    # ------------------------------------------------------------------

    async def get_popular(
        self,
        page: int = 0,
        *,
        limit: int = DEFAULT_PAGE_SIZE,
        time_range: str = DEFAULT_POPULAR_RANGE,
    ) -> Page[PostSummary]:
        """Popular posts via the `wordpress-popular-posts` REST endpoint.

        `page` is 0-indexed (``page=0`` -> offset 0..limit-1) — this SDK's
        own convention, chosen so it maps directly onto the underlying
        `offset = page * limit` formula with no off-by-one surprises.
        """
        url = f"{self.base_url}/wp-json/wordpress-popular-posts/v1/popular-posts"
        params = {
            "offset": page * limit,
            "limit": limit,
            "range": time_range,
            "embed": "true",
            "_embed": "wp:featuredmedia",
            "_fields": "title,link,_embedded,_links.wp:featuredmedia",
        }
        response = await self._get(url, params=params)
        try:
            data = response.json()
        except ValueError as exc:
            raise ParseError(f"popular-posts endpoint returned non-JSON: {exc}", url=str(response.url)) from exc

        items = parse_popular_json(data)
        return Page(items=items, page=page, has_next=len(items) >= limit)

    async def get_latest(self, page: int = 1) -> Page[PostSummary]:
        """Latest posts. `page` is 1-indexed, matching WordPress's own
        `/page/N/` archive numbering.
        """
        url = f"{self.base_url}/page/{page}/"
        response = await self._get(url)
        items, has_next = parse_listing(response.text, str(response.url))
        return Page(items=items, page=page, has_next=has_next)

    async def search(self, query: str, page: int = 1) -> Page[PostSummary]:
        """Text search — or paste a CosplayTele URL to jump straight to a
        post or paginate a category/tag archive, same as the app's own
        search box accepts either.
        """
        query = query.strip()

        if query.startswith(("http://", "https://")):
            own_page = await self._resolve_own_url(query, page)
            if own_page is not None:
                return own_page
            # Not a URL on this site — fall through and search for the
            # literal text, matching the original extension's fallback.

        if not query:
            return await self.get_latest(page)

        url = f"{self.base_url}/page/{page}/"
        response = await self._get(url, params={"s": query})
        items, has_next = parse_listing(response.text, str(response.url))
        return Page(items=items, page=page, has_next=has_next)

    async def browse_category(self, category: Category | str, page: int = 1) -> Page[PostSummary]:
        """Paginate a category or tag archive.

        `category` accepts a `Category` from :meth:`get_categories`, a
        relative path (``"category/cosplay"``), or a full URL.
        """
        path = category.path if isinstance(category, Category) else category
        path = path.strip()

        if path.startswith(("http://", "https://")):
            return await self._browse_url(path, page)

        path = path.strip("/")
        url = f"{self.base_url}/{path}/page/{page}/" if path else f"{self.base_url}/page/{page}/"
        response = await self._get(url)
        items, has_next = parse_listing(response.text, str(response.url))
        return Page(items=items, page=page, has_next=has_next)

    async def get_categories(self, *, refresh: bool = False) -> list[Category]:
        """The site's full, live category/tag taxonomy.

        Cached in memory after the first successful fetch. Falls back to
        a small built-in list (mirroring the extension's own default
        filter options) if `/explore-categories/` can't be reached and
        nothing is cached yet.
        """
        if self._categories_cache is not None and not refresh:
            return self._categories_cache

        try:
            response = await self._get(f"{self.base_url}/explore-categories/")
        except RequestError:
            return self._categories_cache or [Category(name=n, path=p) for n, p in DEFAULT_CATEGORIES]

        categories = parse_categories(response.text, str(response.url))
        if not categories:
            return [Category(name=n, path=p) for n, p in DEFAULT_CATEGORIES]

        self._categories_cache = categories
        return categories

    # ------------------------------------------------------------------
    # single post
    # ------------------------------------------------------------------

    async def get_post(self, url_or_path: str) -> Post:
        """Full detail for one post: title, description, genres, upload
        date, and the full-resolution image URLs for its gallery.
        """
        response = await self._get(self._resolve(url_or_path))
        return parse_post(response.text, str(response.url))

    async def get_images(self, url_or_path: str) -> list[str]:
        """Convenience shortcut for just the image URLs of a post."""
        post = await self.get_post(url_or_path)
        return post.images

    async def download_image(self, url: str) -> bytes:
        """Download one image's raw bytes (sends the site's Referer, so
        this works even where hotlinking the bare URL would be blocked).
        """
        response = await self._get(url)
        return response.content

    async def download_images(self, urls: list[str], *, concurrency: int = 5) -> list[bytes]:
        """Download several images concurrently, in URL order."""
        semaphore = asyncio.Semaphore(concurrency)

        async def _one(url: str) -> bytes:
            async with semaphore:
                return await self.download_image(url)

        return list(await asyncio.gather(*(_one(url) for url in urls)))

    # ------------------------------------------------------------------
    # auto-paginating iterators
    # ------------------------------------------------------------------

    async def iter_latest(
        self, *, start_page: int = 1, max_pages: int | None = None
    ) -> AsyncIterator[PostSummary]:
        """Yield every post across all "latest" pages until exhausted."""
        async for item in self._paginate(
            lambda page: self.get_latest(page), start_page=start_page, max_pages=max_pages
        ):
            yield item

    async def iter_search(
        self, query: str, *, start_page: int = 1, max_pages: int | None = None
    ) -> AsyncIterator[PostSummary]:
        """Yield every search result across all pages until exhausted."""
        async for item in self._paginate(
            lambda page: self.search(query, page), start_page=start_page, max_pages=max_pages
        ):
            yield item

    async def iter_category(
        self, category: Category | str, *, start_page: int = 1, max_pages: int | None = None
    ) -> AsyncIterator[PostSummary]:
        """Yield every post in a category/tag archive across all pages."""
        async for item in self._paginate(
            lambda page: self.browse_category(category, page), start_page=start_page, max_pages=max_pages
        ):
            yield item

    async def iter_popular(
        self,
        *,
        start_page: int = 0,
        limit: int = DEFAULT_PAGE_SIZE,
        time_range: str = DEFAULT_POPULAR_RANGE,
        max_pages: int | None = None,
    ) -> AsyncIterator[PostSummary]:
        """Yield every popular post across all pages until exhausted."""
        async for item in self._paginate(
            lambda page: self.get_popular(page, limit=limit, time_range=time_range),
            start_page=start_page,
            max_pages=max_pages,
        ):
            yield item

    async def _paginate(self, fetch_page, *, start_page: int, max_pages: int | None) -> AsyncIterator[PostSummary]:
        page = start_page
        fetched = 0
        while True:
            result: Page[PostSummary] = await fetch_page(page)
            for item in result.items:
                yield item
            if not result.has_next:
                return
            fetched += 1
            if max_pages is not None and fetched >= max_pages:
                return
            page += 1

    # ------------------------------------------------------------------
    # "paste a URL into search" resolution — ports h.fetchSearchManga
    # ------------------------------------------------------------------

    async def _resolve_own_url(self, url: str, page: int) -> Page[PostSummary] | None:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        own_host = self._own_host()
        if host not in (own_host, f"www.{own_host}"):
            return None

        segments = [s for s in parsed.path.split("/") if s]
        if not segments:
            return None  # bare domain root — let the caller fall back to a literal-text search

        if path_is_taxonomy(segments):
            return await self._browse_url(url, page)

        post = await self.get_post(url)
        summary = PostSummary(title=post.title, url=post.url, thumbnail=None)
        return Page(items=[summary], page=1, has_next=False)

    async def _browse_url(self, url: str, page: int) -> Page[PostSummary]:
        scheme, netloc, path, query, fragment = urlsplit(url)
        segments = [s for s in path.split("/") if s]
        if "page" in segments:
            idx = segments.index("page")
            if idx + 1 < len(segments):
                segments[idx + 1] = str(page)
            else:
                segments.append(str(page))
        else:
            segments += ["page", str(page)]
        new_path = "/" + "/".join(segments) + "/"
        target = urlunsplit((scheme, netloc, new_path, query, fragment))

        response = await self._get(target)
        items, has_next = parse_listing(response.text, str(response.url))
        return Page(items=items, page=page, has_next=has_next)
