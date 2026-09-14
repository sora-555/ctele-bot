"""Page arithmetic shared by every paginated screen."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence, TypeVar

T = TypeVar("T")


@dataclass(slots=True)
class PageInfo:
    page: int
    per_page: int
    total: int | None = None
    total_pages: int | None = None
    has_prev: bool = False
    has_next: bool = False

    @property
    def label(self) -> str:
        if self.total_pages:
            return f"{self.page} / {self.total_pages}"
        return str(self.page)

    @property
    def start_index(self) -> int:
        return (self.page - 1) * self.per_page


def known(total: int, per_page: int, page: int) -> PageInfo:
    """Pagination when the total row count is known (DB-backed lists)."""
    per_page = max(per_page, 1)
    total_pages = max(math.ceil(total / per_page), 1)
    page = min(max(page, 1), total_pages)
    return PageInfo(
        page=page,
        per_page=per_page,
        total=total,
        total_pages=total_pages,
        has_prev=page > 1,
        has_next=page < total_pages,
    )


def unknown(page: int, per_page: int, has_next: bool) -> PageInfo:
    """Pagination for source listings where only "is there more" is known."""
    page = max(page, 1)
    return PageInfo(
        page=page,
        per_page=per_page,
        total=None,
        total_pages=None,
        has_prev=page > 1,
        has_next=has_next,
    )


def slice_page(items: Sequence[T], per_page: int, page: int) -> list[T]:
    per_page = max(per_page, 1)
    start = (max(page, 1) - 1) * per_page
    return list(items[start : start + per_page])


def clamp_page_size(value: int, *, low: int, high: int) -> int:
    return max(low, min(high, value))