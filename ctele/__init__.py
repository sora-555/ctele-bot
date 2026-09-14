"""
ctele — async Python SDK for CosplayTele (cosplaytele.com)

Reverse-engineered from the site's official Keiyoushi/Tachiyomi extension
(decompiled `classes.jar`). See README.md for the full endpoint/selector
mapping back to the original Kotlin source.

Quick start
-----------
    import asyncio
    from ctele import CTeleClient

    async def main():
        async with CTeleClient() as ctele:
            page = await ctele.get_latest()
            for post in page.items:
                print(post.title, post.url)

            post = await ctele.get_post(page.items[0].url)
            print(post.images)  # direct, full-resolution image URLs

    asyncio.run(main())
"""

from .client import CTeleClient
from .exceptions import CTeleError, ParseError, RequestError
from .models import Category, Page, Post, PostSummary

__all__ = [
    "CTeleClient",
    "CTeleError",
    "RequestError",
    "ParseError",
    "Category",
    "PostSummary",
    "Post",
    "Page",
]

__version__ = "0.1.0"
