"""Small text helpers shared by handlers and keyboards."""

from __future__ import annotations

import html


def strip_surrogates(value: str) -> str:
    """Drop unpaired surrogates.

    Text decoded from broken HTML can carry lone surrogates, and a string holding
    one cannot be encoded to UTF-8 - so a single bad title would otherwise take
    down the whole send. Strip them as the text crosses into a message.
    """
    if not value:
        return value
    if not any(0xD800 <= ord(char) <= 0xDFFF for char in value):
        return value
    return "".join(char for char in value if not 0xD800 <= ord(char) <= 0xDFFF)


def esc(value: object) -> str:
    """Escape a dynamic value for HTML parse mode."""
    return html.escape(strip_surrogates(str(value)), quote=False)


def truncate(value: str, limit: int) -> str:
    value = " ".join(strip_surrogates(value or "").split())
    if len(value) <= limit:
        return value
    return value[: max(limit - 1, 1)].rstrip() + "\u2026"


def human_int(value: int) -> str:
    return f"{value:,}"


def join_bullets(values: list[str], *, limit: int = 6) -> str:
    if not values:
        return "-"
    shown = [esc(v) for v in values[:limit]]
    return " \u00b7 ".join(shown)


def plural(count: int, singular: str, plural_form: str | None = None) -> str:
    if count == 1:
        return f"{count} {singular}"
    return f"{count} {plural_form or singular + 's'}"