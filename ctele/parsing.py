"""Pure parsing functions — no I/O, no client state.

Each function here is a direct port of one method from the decompiled
extension (class `h` unless noted). Keeping these free of any network
code makes them trivial to unit test against saved/synthetic HTML
fixtures (see tests/test_parsing.py) — useful the day CosplayTele tweaks
its theme and a selector needs updating.

Original class -> function map:
    h.popularMangaParse   -> parse_popular_json
    h.searchMangaParse /
    h.latestUpdatesParse  -> parse_listing            (same "main div.box" logic)
    h.b (taxonomy links)  -> extract_taxonomy
    h.mangaDetailsParse /
    h.chapterListParse /
    h.pageListParse       -> parse_post               (merged: one page, one fetch)
"""

from __future__ import annotations

import html as html_lib
import re
from datetime import datetime
from urllib.parse import urljoin

from selectolax.parser import HTMLParser

from ._constants import BASE_URL, TAXONOMY_HREF_RE
from .exceptions import ParseError
from .models import Category, Post, PostSummary


def abs_url(page_url: str, maybe_relative: str | None) -> str | None:
    """Resolve a possibly-relative href/src against the page it came from.

    Mirrors jsoup's `attr("abs:...")`, which resolves against the
    document's base URI (the URL it was actually fetched from) rather
    than a fixed site root — matters for anything served under a
    redirect or subpath.
    """
    if not maybe_relative:
        return None
    return urljoin(page_url, maybe_relative)


def extract_taxonomy(tree: HTMLParser, page_url: str) -> list[Category]:
    """Pull `category`/`tag` links out of `#main`.

    Ported from `h.b(Document)`. Used both for a post's own genre list
    (called against a post's detail page) and for the full site taxonomy
    (called against /explore-categories/) — CosplayTele's extension
    reuses the exact same routine for both, so we do too.
    """
    results: list[Category] = []
    for a in tree.css("#main a"):
        href = a.attributes.get("href")
        abs_href = abs_url(page_url, href)
        if not abs_href or not TAXONOMY_HREF_RE.fullmatch(abs_href):
            continue
        text = a.text(deep=True, strip=True)
        if not text:
            continue
        idx = abs_href.find(BASE_URL)
        path = abs_href[idx + len(BASE_URL):] if idx != -1 else abs_href
        results.append(Category(name=text, path=path.lstrip("/")))
    return results


def parse_categories(html_text: str, page_url: str) -> list[Category]:
    """Parse the `/explore-categories/` page into the full taxonomy list."""
    tree = HTMLParser(html_text)
    return extract_taxonomy(tree, page_url)


def parse_listing(html_text: str, page_url: str) -> tuple[list[PostSummary], bool]:
    """Parse a `main div.box` grid page: search results, latest, or a
    category/tag archive. Ported from `h.searchMangaParse` /
    `h.latestUpdatesParse` (identical logic in the original).
    """
    tree = HTMLParser(html_text)
    items: list[PostSummary] = []

    for card in tree.css("main div.box"):
        img = card.css_first("img")
        thumbnail = abs_url(page_url, img.attributes.get("src")) if img else None

        link = card.css_first("h5 a")
        if link is None:
            raise ParseError("Title is mandatory", url=page_url)
        title = link.text(deep=True, strip=True)
        href = link.attributes.get("href")
        if not href:
            raise ParseError("Title is mandatory", url=page_url)

        items.append(PostSummary(title=title, url=abs_url(page_url, href), thumbnail=thumbnail))

    has_next = tree.css_first(".next.page-number") is not None
    return items, has_next


def parse_popular_json(data: list[dict]) -> list[PostSummary]:
    """Parse the `wordpress-popular-posts` REST payload.

    Ported from `h.popularMangaParse`, and the DTO chain `u`/`x`/`k`/`n`
    (PopularPostDto -> RenderedStringDto / EmbeddedDto -> FeaturedMediaDto).
    JSON shape:
        [{"title": {"rendered": str}, "link": str,
          "_embedded": {"wp:featuredmedia": [{"source_url": str}]} | None}]
    """
    items: list[PostSummary] = []
    for entry in data:
        title = html_lib.unescape((entry.get("title") or {}).get("rendered", ""))
        url = entry.get("link", "")

        thumbnail = None
        embedded = entry.get("_embedded") or {}
        media = embedded.get("wp:featuredmedia")
        if isinstance(media, list) and media and isinstance(media[0], dict):
            thumbnail = media[0].get("source_url")

        items.append(PostSummary(title=title, url=url, thumbnail=thumbnail))
    return items


def parse_post(html_text: str, page_url: str) -> Post:
    """Parse a single post page into full detail + image list.

    Ported from `h.mangaDetailsParse` (title/description/genre),
    `h.chapterListParse` (upload date, from the lone "Gallery" chapter),
    and `h.pageListParse` (gallery images) — merged into one call since
    they all read the same fetched page in the original extension.
    """
    tree = HTMLParser(html_text)

    title_el = tree.css_first(".entry-title")
    if title_el is None:
        raise ParseError("Title is mandatory", url=page_url)
    title = title_el.text(deep=True, strip=True)
    # The original sets description = title verbatim (no separate
    # synopsis selector exists on this theme) — kept as-is for fidelity.
    description = title

    genres = [c.name for c in extract_taxonomy(tree, page_url)]

    upload_date: datetime | None = None
    time_el = tree.css_first("time.updated")
    if time_el is not None:
        raw = time_el.attributes.get("datetime")
        if raw:
            date_part = raw.split("T", 1)[0]
            try:
                upload_date = datetime.strptime(date_part, "%Y-%m-%d")
            except ValueError:
                upload_date = None

    images: list[str] = []
    for img in tree.css(".gallery-item img"):
        src = abs_url(page_url, img.attributes.get("src"))
        if src:
            images.append(src)

    return Post(
        title=title,
        url=page_url,
        description=description,
        genres=genres,
        upload_date=upload_date,
        images=images,
    )


def path_is_taxonomy(path_segments: list[str]) -> bool:
    """True if a URL's first path segment marks it as a category/tag
    archive rather than a single post — ported from the `"category"` /
    `"tag"` check in `h.fetchSearchManga`.
    """
    return bool(path_segments) and path_segments[0] in ("category", "tag")
