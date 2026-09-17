from bot.config import settings


def window(current: int, total: int, radius: int | None = None) -> list[int]:
    """Numbers around the current one, clamped to the item count."""
    if total <= 0:
        return []
    if radius is None and total <= max(1, settings.nav_short_list_threshold):
        return list(range(1, total + 1))
    span = radius if radius is not None else max(1, settings.nav_window_size // 2)
    start = max(1, current - span)
    end = min(total, current + span)
    return list(range(start, end + 1))


def page_count(total: int, per_page: int) -> int:
    if per_page <= 0:
        return 1
    return max(1, (max(0, total) + per_page - 1) // per_page)


def page_slice(index: int, per_page: int) -> tuple[int, int]:
    """Return (page, offset) for a 1-based global index."""
    per_page = max(1, per_page)
    page = (max(1, index) - 1) // per_page + 1
    return page, (page - 1) * per_page


def human_eta(seconds: float) -> str:
    remaining = int(max(0, seconds))
    if remaining < 60:
        return f"{remaining} sec"
    minutes, rest = divmod(remaining, 60)
    if minutes < 60:
        return f"{minutes} min {rest} sec"
    hours, minutes = divmod(minutes, 60)
    return f"{hours} h {minutes} min"
