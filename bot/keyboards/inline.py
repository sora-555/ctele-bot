"""Inline keyboards for browsing, galleries and account screens.

Buttons carry a 6-character session id instead of a URL because Telegram caps
`callback_data` at 64 bytes.
"""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.services.pagination import PageInfo
from bot.texts.symbols import ACCENT, HEADER, IMPORTANT, ITEM, NEXT, PENDING, PREV, SUCCESS

NOOP = "noop"


def _numbers(item_count: int, sid: str, prefix: str, labels: list[str]) -> list[list[InlineKeyboardButton]]:
    rows: list[list[InlineKeyboardButton]] = []
    for start in range(0, min(item_count, len(labels)), 2):
        row = [
            InlineKeyboardButton(text=labels[index], callback_data=f"{prefix}:{sid}:{index}")
            for index in range(start, min(start + 2, item_count))
        ]
        rows.append(row)
    return rows


def nav_row(prefix: str, sid: str, info: PageInfo, *, middle_label: str | None = None) -> list[InlineKeyboardButton]:
    return [
        InlineKeyboardButton(
            text=f"{PREV} Prev" if info.has_prev else f"{PREV}",
            callback_data=f"{prefix}:{sid}:{info.page - 1}" if info.has_prev else NOOP,
        ),
        InlineKeyboardButton(
            text=middle_label or f"Page {info.label}", callback_data=NOOP
        ),
        InlineKeyboardButton(
            text=f"Next {NEXT}" if info.has_next else f"{NEXT}",
            callback_data=f"{prefix}:{sid}:{info.page + 1}" if info.has_next else NOOP,
        ),
    ]


def age_gate() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="I am 18+", callback_data="age:yes")
    builder.button(text="Exit", callback_data="age:no")
    builder.adjust(2)
    return builder.as_markup()


def welcome() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=f"{IMPORTANT} Latest", callback_data="cmd:latest")
    builder.button(text="Popular", callback_data="cmd:popular")
    builder.button(text="Search", callback_data="cmd:search")
    builder.button(text="Favorites", callback_data="cmd:favorites")
    builder.adjust(2, 2)
    return builder.as_markup()


def main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=f"{IMPORTANT} Latest", callback_data="cmd:latest")
    builder.button(text="Popular", callback_data="cmd:popular")
    builder.button(text="Search", callback_data="cmd:search")
    builder.button(text="Categories", callback_data="cmd:categories")
    builder.button(text="Favorites", callback_data="cmd:favorites")
    builder.button(text="History", callback_data="cmd:history")
    builder.button(text="Profile", callback_data="cmd:profile")
    builder.button(text="Settings", callback_data="cmd:settings")
    builder.adjust(2, 2, 2, 2)
    return builder.as_markup()


def listing(sid: str, info: PageInfo, labels: list[str], *, back_label: str | None = None, back_data: str | None = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for row in _numbers(len(labels), sid, "po", labels):
        builder.row(*row)
    builder.row(*nav_row("ls", sid, info))
    tail = []
    if back_label and back_data:
        tail.append(InlineKeyboardButton(text=back_label, callback_data=back_data))
    tail.append(InlineKeyboardButton(text="Menu", callback_data="cmd:menu"))
    builder.row(*tail)
    return builder.as_markup()


def search_card(
    sid: str,
    *,
    count: int,
    index: int,
    has_prev: bool,
    has_next: bool,
    per_row: int = 5,
) -> InlineKeyboardMarkup:
    """One result at a time: page controls on top, quick-jump numbers below.

    The number row is a shortcut into the in-chat jump flow - tapping one asks for the
    number in the chat instead of guessing which result the user meant.
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=f"{PREV} Prev" if has_prev else PREV,
            callback_data=f"sv:{sid}:p" if has_prev else NOOP,
        ),
        InlineKeyboardButton(text=f"{ITEM} Open", callback_data=f"po:{sid}:{index}"),
        InlineKeyboardButton(
            text=f"Next {NEXT}" if has_next else NEXT,
            callback_data=f"sv:{sid}:n" if has_next else NOOP,
        ),
    )
    numbers = [
        InlineKeyboardButton(text=str(position + 1), callback_data=f"sn:{sid}:{position}")
        for position in range(count)
    ]
    for start in range(0, len(numbers), per_row):
        builder.row(*numbers[start : start + per_row])
    builder.row(
        InlineKeyboardButton(text=f"{ACCENT} New Search", callback_data="cmd:search"),
        InlineKeyboardButton(text=f"{HEADER} Menu", callback_data="cmd:menu"),
    )
    return builder.as_markup()


def no_results() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="New Search", callback_data="cmd:search")
    builder.button(text="Latest", callback_data="cmd:latest")
    builder.adjust(2)
    return builder.as_markup()


def categories(sid: str, info: PageInfo, labels: list[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for row in _numbers(len(labels), sid, "ct", labels):
        builder.row(*row)
    builder.row(*nav_row("ls", sid, info))
    builder.row(
        InlineKeyboardButton(text="Refresh", callback_data=f"cr:{sid}"),
        InlineKeyboardButton(text="Menu", callback_data="cmd:menu"),
    )
    return builder.as_markup()


def post_card(sid: str, *, is_favorite: bool, post_url: str, back_label: str = "Back", back_data: str = "cmd:menu") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=f"{ITEM} Open Gallery", callback_data=f"pv:{sid}:1"))
    builder.row(
        InlineKeyboardButton(
            text=f"{SUCCESS} Saved" if is_favorite else "Save", callback_data=f"fv:{sid}"
        ),
        InlineKeyboardButton(text="Open Original", callback_data="noop"),
    )
    builder.row(
        InlineKeyboardButton(text=back_label, callback_data=back_data),
        InlineKeyboardButton(text="Menu", callback_data="cmd:menu"),
    )
    return builder.as_markup()


def gallery(sid: str, info: PageInfo, *, is_favorite: bool, post_url: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=f"{SUCCESS} Saved" if is_favorite else "Save", callback_data=f"fv:{sid}"
        ),
        InlineKeyboardButton(text=f"{ITEM} Details", callback_data=f"gd:{sid}"),
    )
    builder.row(
        InlineKeyboardButton(
            text=f"{PREV} Prev" if info.has_prev else PREV,
            callback_data=f"g:{sid}:{info.page - 1}" if info.has_prev else NOOP,
        ),
        InlineKeyboardButton(text=info.label, callback_data=NOOP),
        InlineKeyboardButton(
            text=f"Next {NEXT}" if info.has_next else NEXT,
            callback_data=f"g:{sid}:{info.page + 1}" if info.has_next else NOOP,
        ),
    )
    return builder.as_markup()


def gallery_retry(sid: str, info: PageInfo) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Retry Page", callback_data=f"g:{sid}:{info.page}"))
    builder.row(
        InlineKeyboardButton(text=f"{ITEM} Details", callback_data=f"gd:{sid}"),
        InlineKeyboardButton(text=f"{PREV} Prev" if info.has_prev else PREV, callback_data=f"g:{sid}:{info.page - 1}" if info.has_prev else NOOP),
        InlineKeyboardButton(text=f"Next {NEXT}" if info.has_next else NEXT, callback_data=f"g:{sid}:{info.page + 1}" if info.has_next else NOOP),
    )
    return builder.as_markup()


def session_expired() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Latest", callback_data="cmd:latest")
    builder.button(text="Menu", callback_data="cmd:menu")
    builder.adjust(2)
    return builder.as_markup()


def settings(*, images_per_page: int, items_per_page: int, mode: str, spoiler: bool, thumbnails: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=f"Images per page {IMAGE_SEP} {images_per_page}", callback_data=NOOP)
    )
    builder.row(
        InlineKeyboardButton(text="\u2013", callback_data="st:images:-1"),
        InlineKeyboardButton(text=str(images_per_page), callback_data=NOOP),
        InlineKeyboardButton(text="+", callback_data="st:images:1"),
    )
    builder.row(
        InlineKeyboardButton(
            text=f"{IMPORTANT} Album" if mode == "album" else "Album", callback_data="st:mode:album"
        ),
        InlineKeyboardButton(
            text=f"{IMPORTANT} Single" if mode == "single" else "Single", callback_data="st:mode:single"
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text=f"{IMPORTANT if thumbnails else PENDING} Thumbnails", callback_data="st:thumb:toggle"
        ),
        InlineKeyboardButton(
            text=f"{IMPORTANT if spoiler else PENDING} Spoiler", callback_data="st:spoiler:toggle"
        ),
    )
    builder.row(
        InlineKeyboardButton(text="Reset Defaults", callback_data="st:reset:1"),
        InlineKeyboardButton(text="Menu", callback_data="cmd:menu"),
    )
    return builder.as_markup()


IMAGE_SEP = "\u00b7"


def profile() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Favorites", callback_data="cmd:favorites")
    builder.button(text="History", callback_data="cmd:history")
    builder.button(text="Settings", callback_data="cmd:settings")
    builder.button(text="Menu", callback_data="cmd:menu")
    builder.adjust(2, 2)
    return builder.as_markup()


def media_list(sid: str, info: PageInfo, labels: list[str], *, prefix: str = "fe", manage: bool = False, with_clear: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    button_prefix = "fr" if manage else prefix
    for row in _numbers(len(labels), sid, button_prefix, labels):
        builder.row(*row)
    builder.row(*nav_row("ls", sid, info))
    tail = [
        InlineKeyboardButton(text="Manage" if not manage else "Done", callback_data=f"fx:{sid}"),
    ]
    if with_clear:
        tail.append(InlineKeyboardButton(text=f"{IMPORTANT} Clear", callback_data="hc:ask"))
    tail.append(InlineKeyboardButton(text="Menu", callback_data="cmd:menu"))
    builder.row(*tail)
    return builder.as_markup()


def clear_history_confirm() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=f"{IMPORTANT} Clear History", callback_data="hc:yes")
    builder.button(text="Cancel", callback_data="hc:no")
    builder.adjust(2)
    return builder.as_markup()


def confirm(yes_data: str, no_data: str, *, yes_label: str = "Confirm", no_label: str = "Cancel") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=yes_label, callback_data=yes_data)
    builder.button(text=no_label, callback_data=no_data)
    builder.adjust(2)
    return builder.as_markup()


def cancel_only(data: str, *, label: str = "Cancel") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=label, callback_data=data)
    return builder.as_markup()


def back_to_menu(*, back_label: str = "Latest", back_data: str = "cmd:latest") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=back_label, callback_data=back_data)
    builder.button(text="Menu", callback_data="cmd:menu")
    builder.adjust(2)
    return builder.as_markup()