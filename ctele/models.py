"""Plain dataclass models returned by the SDK.

Deliberately stdlib-only (no pydantic) so this package doesn't fight your
FastAPI app's pydantic version, and drops into an aiogram bot with zero
extra weight. Wrap these in your own pydantic models at the API boundary
if you need response-model validation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Generic, Iterator, TypeVar

T = TypeVar("T")


@dataclass(slots=True)
class Category:
    """A browsable taxonomy entry (WordPress ``category`` or ``tag``).

    ``path`` is relative to the site root and safe to pass straight into
    :meth:`CTeleClient.browse_category`, e.g. ``"category/cosplay"``.
    """

    name: str
    path: str


@dataclass(slots=True)
class PostSummary:
    """One entry in a listing (popular / latest / search / category)."""

    title: str
    url: str
    thumbnail: str | None = None


@dataclass(slots=True)
class Post:
    """Full detail for a single post — one post == one photo gallery."""

    title: str
    url: str
    description: str | None
    genres: list[str] = field(default_factory=list)
    upload_date: datetime | None = None
    images: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Page(Generic[T]):
    """A single page of paginated results.

    Iterate it directly (``for post in page: ...``) or index it
    (``page[0]``); ``len(page)`` gives the item count on this page.
    """

    items: list[T]
    page: int
    has_next: bool

    def __iter__(self) -> Iterator[T]:
        return iter(self.items)

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, index: int) -> T:
        return self.items[index]
