"""Every user-visible string.

Design rules (see AGENTS.md): one header symbol, one list symbol, one separator
and one key/value separator per message; symbols carry meaning, never decoration;
no emoji anywhere.
"""

from __future__ import annotations

from datetime import datetime

from bot.texts.symbols import (
    ACCENT,
    HEADER,
    IMPORTANT,
    ITEM,
    KV,
    PENDING,
    SECTION,
    SEPARATOR,
    SUCCESS,
)
from bot.utils.text import esc, human_int, join_bullets, strip_surrogates, truncate

# Re-exported so handlers can write `ui.LEFT` / `ui.NEXT` style labels without importing
# `bot.texts.symbols` themselves - a missing alias here used to raise AttributeError at
# runtime, which no import check would catch.
from bot.texts import symbols as _symbols

ALERT_CLOSE = _symbols.ALERT_CLOSE
ALERT_OPEN = _symbols.ALERT_OPEN
BULLET = _symbols.BULLET
CHECK = _symbols.CHECK
INACTIVE = _symbols.INACTIVE
LEFT = _symbols.LEFT
NEXT = _symbols.NEXT
PREV = _symbols.PREV
RIGHT = _symbols.RIGHT
TREE_BRANCH = _symbols.TREE_BRANCH
TREE_LAST = _symbols.TREE_LAST

DEFAULT_ITEMS = 6


def autodelete(ttl_label: str) -> str:
    return f"{IMPORTANT} Auto-delete {KV} this is removed in {ttl_label}"


def welcome(name: str, user_id: int, ttl_label: str) -> str:
    return (
        f"{HEADER} 𝗪𝗲𝗹𝗰𝗼𝗺𝗲\n\n{SEPARATOR}\n\n"
        f"{ITEM} User {KV} {esc(name)}\n"
        f"{ITEM} ID {KV} {user_id}\n"
        f"{ITEM} Status {KV} {IMPORTANT} Active\n\n"
        f"{SECTION} 𝗚𝗲𝘁 𝗦𝘁𝗮𝗿𝘁𝗲𝗱\n\n"
        f"{ITEM} /latest {KV} newest posts\n"
        f"{ITEM} /popular {KV} trending now\n"
        f"{ITEM} /search {KV} find anything\n"
        f"{ITEM} /help {KV} all commands\n\n"
        f"{SECTION} 𝗚𝗼𝗼𝗱 𝘁𝗼 𝗞𝗻𝗼𝘄\n\n"
        f"{ITEM} Media {KV} auto-deleted after {ttl_label}\n\n"
        f"{SEPARATOR}"
    )


def age_gate(minimum: int = 18) -> str:
    return (
        f"{HEADER} 𝗔𝗚𝗘 𝗩𝗘𝗥𝗜𝗙𝗜𝗖𝗔𝗧𝗜𝗢𝗡\n\n{SEPARATOR}\n\n"
        "This bot shares content intended for adults only.\n\n"
        f"{ITEM} Requirement {KV} you must be {minimum} or older\n"
        f"{ITEM} Reminder {KV} you can stop using the bot at any time\n\n"
        f"{SEPARATOR}"
    )


def age_gate_declined() -> str:
    return (
        f"{HEADER} 𝗘𝘅𝗶𝘁𝗲𝗱\n\n{SEPARATOR}\n\n"
        f"{ITEM} Return {KV} /start whenever you change your mind\n\n"
        f"{SEPARATOR}"
    )


def main_menu(name: str, favorites: int, status: str) -> str:
    return (
        f"{HEADER} 𝗠𝗮𝗶𝗻 𝗠𝗲𝗻𝘂\n\n{SEPARATOR}\n\n"
        f"{ITEM} User {KV} {esc(name)}\n"
        f"{ITEM} Favorites {KV} {human_int(favorites)}\n"
        f"{ITEM} Status {KV} {status}\n\n"
        f"{ITEM} Send a command, or use the buttons below\n\n"
        f"{SEPARATOR}"
    )


def help_user() -> str:
    return (
        f"{HEADER} 𝗛𝗲𝗹𝗽\n\n{SEPARATOR}\n\n"
        f"{SECTION} 𝗕𝗿𝗼𝘄𝘀𝗲\n\n"
        f"{ITEM} /latest {KV} newest posts\n"
        f"{ITEM} /popular {KV} trending posts\n"
        f"{ITEM} /categories {KV} browse categories\n"
        f"{ITEM} /category {KV} open a category\n"
        f"{ITEM} /search {KV} search posts\n"
        f"{ITEM} /random {KV} random post\n"
        f"{ITEM} /post {KV} open a post link\n\n"
        f"{SECTION} 𝗬𝗼𝘂𝗿 𝗔𝗰𝗰𝗼𝘂𝗻𝘁\n\n"
        f"{ITEM} /favorites {KV} saved posts\n"
        f"{ITEM} /history {KV} recently viewed\n"
        f"{ITEM} /profile {KV} your profile\n"
        f"{ITEM} /settings {KV} preferences\n"
        f"{ITEM} /stats {KV} usage stats\n\n"
        f"{SECTION} 𝗢𝘁𝗵𝗲𝗿\n\n"
        f"{ITEM} /about {KV} bot information\n"
        f"{ITEM} /ping {KV} check latency\n"
        f"{ITEM} /cancel {KV} cancel input\n\n"
        f"{SEPARATOR}"
    )


def help_admin() -> str:
    return (
        f"{SECTION} 𝗔𝗱𝗺𝗶𝗻\n\n"
        f"{ITEM} /admin {KV} control panel\n"
        f"{ITEM} /astats {KV} global statistics\n"
        f"{ITEM} /users {KV} user list\n"
        f"{ITEM} /find {KV} search users\n"
        f"{ITEM} /user {KV} user detail\n"
        f"{ITEM} /block {KV} block a user\n"
        f"{ITEM} /unblock {KV} unblock a user\n"
        f"{ITEM} /blocked {KV} active blocks\n"
        f"{ITEM} /broadcast {KV} message everyone\n"
        f"{ITEM} /logs {KV} audit log\n"
        f"{ITEM} /health {KV} system health\n"
        f"{ITEM} /export {KV} download CSV\n"
        f"{ITEM} /maintenance {KV} lock the bot\n"
        f"{ITEM} /reload {KV} clear caches\n"
        f"{ITEM} /admins {KV} manage roles\n\n"
        f"{SEPARATOR}"
    )


def listing(title: str, page_label: str, count: int, *, hint: str | None = None) -> str:
    body = (
        f"{SECTION} {title}\n\n{SEPARATOR}\n\n"
        f"{ITEM} Page {KV} {page_label}\n"
        f"{ITEM} Results {KV} {count} post" + ("s" if count != 1 else "")
    )
    if hint:
        body += f"\n\n{hint}"
    return body


def search_card(
    *,
    query: str,
    title: str,
    position: int,
    count: int,
    window: str,
    ttl_label: str,
    photo: bool,
) -> str:
    """One search result per screen, so two results are never confused."""
    lines = [
        f"{HEADER} 𝗥𝗲𝘀𝘂𝗹𝘁 {position} / {count}",
        "",
        SEPARATOR,
        "",
        esc(truncate(title, 90)),
        "",
        f"{ITEM} Query {KV} {esc(truncate(query, 40))}",
        f"{ITEM} Window {KV} {window}",
        "",
        f"{ITEM} Tap a number below, or just send the number in chat",
    ]
    if photo:
        lines += ["", autodelete(ttl_label)]
    return "\n".join(lines)


def search_jump_prompt(count: int) -> str:
    return (
        f"{ACCENT} 𝗝𝘂𝗺𝗽 𝘁𝗼 𝗥𝗲𝘀𝘂𝗹𝘁\n\n{SEPARATOR}\n\n"
        "Send the number of the result you want to see.\n\n"
        f"{ITEM} Range {KV} 1 to {count}\n"
        f"{ITEM} Cancel {KV} /cancel\n\n"
        f"{SEPARATOR}"
    )


def search_jump_invalid(value: str, count: int) -> str:
    shown = esc(truncate(value, 20)) or "nothing"
    return (
        f"{PENDING} 𝗨𝗻𝗸𝗻𝗼𝘄𝗻 𝗥𝗲𝘀𝘂𝗹𝘁\n\n{SEPARATOR}\n\n"
        f"{ITEM} You sent {KV} {shown}\n"
        f"{ITEM} Range {KV} 1 to {count}\n\n"
        "Send a number in that range, or step through with Prev and Next.\n\n"
        f"{SEPARATOR}"
    )


def search_no_results(query: str) -> str:
    return (
        f"{PENDING} 𝗡𝗼 𝗥𝗲𝘀𝘂𝗹𝘁𝘀\n\n{SEPARATOR}\n\n"
        f"{ITEM} Query {KV} {esc(truncate(query, 40))}\n"
        f"{ITEM} Tried {KV} text search\n\n"
        f"{ITEM} Suggestion {KV} shorten the keyword or check the spelling\n\n"
        f"{SEPARATOR}"
    )


def search_prompt() -> str:
    return (
        f"{ACCENT} 𝗦𝗲𝗮𝗿𝗰𝗵\n\n{SEPARATOR}\n\n"
        "Send a keyword to search for.\n\n"
        f"{ITEM} Tip {KV} a post or category link works too\n"
        f"{ITEM} Cancel {KV} /cancel\n\n"
        f"{SEPARATOR}"
    )


def categories_text(page_label: str, count: int) -> str:
    return (
        f"{SECTION} 𝗖𝗮𝘁𝗲𝗴𝗼𝗿𝗶𝗲𝘀\n\n{SEPARATOR}\n\n"
        f"{ITEM} Source {KV} live taxonomy\n"
        f"{ITEM} Page {KV} {page_label}\n\n"
        "Select a category to browse."
        if count
        else f"{PENDING} 𝗡𝗼 𝗖𝗮𝘁𝗲𝗴𝗼𝗿𝗶𝗲𝘀\n\n{SEPARATOR}\n\n"
        f"{ITEM} Reason {KV} the source returned an empty list"
    )


def post_card(
    *,
    title: str,
    upload_date: datetime | None,
    image_count: int,
    genres: list[str],
    description: str | None,
    ttl_label: str,
) -> str:
    when = upload_date.strftime("%Y-%m-%d") if upload_date else "-"
    body = (
        f"{HEADER} 𝗣𝗼𝘀𝘁\n\n{SEPARATOR}\n\n"
        f"{SECTION} 𝗜𝗻𝗳𝗼\n\n"
        f"{ITEM} Title {KV} {esc(truncate(title, 120))}\n"
        f"{ITEM} Date {KV} {when}\n"
        f"{ITEM} Images {KV} {human_int(image_count)}\n\n"
        f"{SECTION} 𝗚𝗲𝗻𝗿𝗲𝘀\n\n"
        f"{ITEM} {join_bullets(genres) or '-'}\n"
    )
    if description and description.strip() and description.strip() != title.strip():
        body += f"\n{SECTION} 𝗣𝗿𝗲𝘃𝗶𝗲𝘄\n\n{ITEM} {esc(truncate(description, 200))}\n"
    body += f"\n{autodelete(ttl_label)}\n\n{SEPARATOR}"
    return body


def gallery_caption(
    *, title: str, start: int, end: int, total: int, page_label: str, ttl_label: str, failed: int = 0
) -> str:
    body = (
        f"{HEADER} 𝗚𝗮𝗹𝗹𝗲𝗿𝘆\n\n{SEPARATOR}\n\n"
        f"{ITEM} Post {KV} {esc(truncate(title, 80))}\n"
        f"{ITEM} Images {KV} {start}\u2013{end} of {human_int(total)}\n"
        f"{ITEM} Page {KV} {page_label}\n"
    )
    if failed:
        body += f"\n{IMPORTANT} Note {KV} {failed} image(s) could not be loaded\n"
    body += f"\n{autodelete(ttl_label)}"
    return body


def gallery_single_caption(*, title: str, position: int, total: int, ttl_label: str) -> str:
    return (
        f"{HEADER} 𝗚𝗮𝗹𝗹𝗲𝗿𝘆\n\n{SEPARATOR}\n\n"
        f"{ITEM} Post {KV} {esc(truncate(title, 80))}\n"
        f"{ITEM} Image {KV} {position} of {human_int(total)}\n\n"
        f"{autodelete(ttl_label)}"
    )


def session_expired() -> str:
    return (
        f"{PENDING} 𝗦𝗲𝘀𝘀𝗶𝗼𝗻 𝗘𝘅𝗽𝗶𝗿𝗲𝗱\n\n{SEPARATOR}\n\n"
        "This menu is no longer active.\n\n"
        f"{ITEM} Fix {KV} reopen it from the menu\n\n"
        f"{SEPARATOR}"
    )


def profile(*, user, favorites: int, history: int, ttl_label: str) -> str:
    status = f"{SUCCESS} Active" if user.is_active else f"{IMPORTANT} Blocked"
    verified = f"{SUCCESS} 18+ verified" if user.age_verified else f"{PENDING} Not verified"
    return (
        f"{HEADER} 𝗣𝗿𝗼𝗳𝗶𝗹𝗲\n\n{SEPARATOR}\n\n"
        f"{SECTION} 𝗜𝗱𝗲𝗻𝘁𝗶𝘁𝘆\n\n"
        f"{ITEM} Name {KV} {esc(user.display_name)}\n"
        f"{ITEM} Username {KV} {esc(user.handle)}\n"
        f"{ITEM} ID {KV} {user.id}\n\n"
        f"{SECTION} 𝗔𝗰𝘁𝗶𝘃𝗶𝘁𝘆\n\n"
        f"{ITEM} Requests {KV} {human_int(user.request_count)}\n\n"
        f"{SECTION} 𝗟𝗶𝗯𝗿𝗮𝗿𝘆\n\n"
        f"{ITEM} Favorites {KV} {human_int(favorites)}\n"
        f"{ITEM} History {KV} {human_int(history)}\n\n"
        f"{SECTION} 𝗦𝘁𝗮𝘁𝘂𝘀\n\n{status}\n{verified}\n\n"
        f"{ITEM} Media {KV} auto-deleted after {ttl_label}\n\n"
        f"{SEPARATOR}"
    )


def settings_text(*, images_per_page: int, items_per_page: int, mode: str, spoiler: bool, thumbnails: bool, ttl_label: str) -> str:
    return (
        f"{HEADER} 𝗦𝗲𝘁𝘁𝗶𝗻𝗴𝘀\n\n{SEPARATOR}\n\n"
        f"{SECTION} 𝗗𝗶𝘀𝗽𝗹𝗮𝘆\n\n"
        f"{ITEM} Images per page {KV} {images_per_page}\n"
        f"{ITEM} Posts per page {KV} {items_per_page}\n"
        f"{ITEM} Thumbnails {KV} {IMPORTANT if thumbnails else PENDING} {'On' if thumbnails else 'Off'}\n\n"
        f"{SECTION} 𝗚𝗮𝗹𝗹𝗲𝗿𝘆\n\n"
        f"{ITEM} Mode {KV} {IMPORTANT} {'Album' if mode == 'album' else 'Single'}\n"
        f"{ITEM} Spoiler media {KV} {IMPORTANT if spoiler else PENDING} {'On' if spoiler else 'Off'}\n\n"
        f"{SECTION} 𝗔𝘂𝘁𝗼-𝗗𝗲𝗹𝗲𝘁𝗲\n\n"
        f"{ITEM} Media is removed {KV} {ttl_label} after sending\n\n"
        f"{ITEM} Every tap saves immediately\n\n"
        f"{SEPARATOR}"
    )


def user_stats(*, requests: int, viewed: int, favorites: int, since: datetime | None, last_seen: datetime | None) -> str:
    return (
        f"{HEADER} 𝗬𝗼𝘂𝗿 𝗦𝘁𝗮𝘁𝘀\n\n{SEPARATOR}\n\n"
        f"{ITEM} Requests {KV} {human_int(requests)}\n"
        f"{ITEM} Posts viewed {KV} {human_int(viewed)}\n"
        f"{ITEM} Favorites {KV} {human_int(favorites)}\n"
        f"{ITEM} Member since {KV} {since.strftime('%Y-%m-%d') if since else '-'}\n"
        f"{ITEM} Last active {KV} {last_seen.strftime('%Y-%m-%d %H:%M') if last_seen else '-'}\n\n"
        f"{SEPARATOR}"
    )


def favorites_text(count: int, page_label: str, *, manage: bool = False) -> str:
    if not count:
        return empty_favorites()
    hint = "Tap an entry to remove it." if manage else "Press a number to open its gallery."
    return (
        f"{HEADER} 𝗙𝗮𝘃𝗼𝗿𝗶𝘁𝗲𝘀\n\n{SEPARATOR}\n\n"
        f"{ITEM} Saved {KV} {human_int(count)}\n"
        f"{ITEM} Page {KV} {page_label}\n\n{hint}"
    )


def empty_favorites() -> str:
    return (
        f"{PENDING} 𝗡𝗼𝘁𝗵𝗶𝗻𝗴 𝗦𝗮𝘃𝗲𝗱\n\n{SEPARATOR}\n\n"
        "You have no favorites yet.\n\n"
        f"{ITEM} Tip {KV} press Save on any gallery\n\n"
        f"{SEPARATOR}"
    )


def history_text(count: int, page_label: str) -> str:
    if not count:
        return (
            f"{PENDING} 𝗡𝗼 𝗛𝗶𝘀𝘁𝗼𝗿𝘆\n\n{SEPARATOR}\n\n"
            "You have not opened a post yet.\n\n"
            f"{ITEM} Tip {KV} browse /latest to get started\n\n"
            f"{SEPARATOR}"
        )
    return (
        f"{HEADER} 𝗛𝗶𝘀𝘁𝗼𝗿𝘆\n\n{SEPARATOR}\n\n"
        f"{ITEM} Viewed {KV} {human_int(count)}\n"
        f"{ITEM} Page {KV} {page_label}\n\n"
        "Press a number to open its gallery."
    )


def admin_panel(*, users: int, active_24h: int, blocked: int, new_today: int, mode: str, source_ok: bool, cache_hits: int) -> str:
    return (
        f"{HEADER} 𝗔𝗱𝗺𝗶𝗻 𝗣𝗮𝗻𝗲𝗹\n\n{SEPARATOR}\n\n"
        f"{SECTION} 𝗟𝗶𝘃𝗲 𝗡𝘂𝗺𝗯𝗲𝗿𝘀\n\n"
        f"{ITEM} Users {KV} {human_int(users)}\n"
        f"{ITEM} Active 24h {KV} {human_int(active_24h)}\n"
        f"{ITEM} Blocked {KV} {human_int(blocked)}\n"
        f"{ITEM} New today {KV} {human_int(new_today)}\n\n"
        f"{SECTION} 𝗦𝘆𝘀𝘁𝗲𝗺\n\n"
        f"{ITEM} Mode {KV} {IMPORTANT} {esc(mode)}\n"
        f"{ITEM} Source {KV} {SUCCESS if source_ok else PENDING} {'Reachable' if source_ok else 'Unreachable'}\n"
        f"{ITEM} Cache hits {KV} {human_int(cache_hits)}\n\n"
        f"{SEPARATOR}"
    )


def users_list(*, total: int, page_label: str, legend: str) -> str:
    return (
        f"{HEADER} 𝗨𝘀𝗲𝗿𝘀\n\n{SEPARATOR}\n\n"
        f"{ITEM} Total {KV} {human_int(total)}\n"
        f"{ITEM} Page {KV} {page_label}\n"
        f"{ITEM} Sort {KV} newest first\n\n{legend}"
    )


def find_prompt() -> str:
    return (
        f"{ACCENT} 𝗙𝗶𝗻𝗱 𝗨𝘀𝗲𝗿\n\n{SEPARATOR}\n\n"
        "Send an ID, username, or name fragment.\n\n"
        f"{ITEM} Example {KV} 123456789\n"
        f"{ITEM} Example {KV} @johndoe\n\n"
        f"{ITEM} Cancel {KV} /cancel\n\n"
        f"{SEPARATOR}"
    )


def find_results(query: str, count: int) -> str:
    return (
        f"{HEADER} 𝗙𝗶𝗻𝗱 𝗥𝗲𝘀𝘂𝗹𝘁𝘀\n\n{SEPARATOR}\n\n"
        f"{ITEM} Query {KV} {esc(truncate(query, 40))}\n"
        f"{ITEM} Matches {KV} {count}\n\n"
        "Select a user to open their card."
    )


def user_card(*, user, favorites: int, blocks: int, notes: int, active_block) -> str:
    status = f"{SUCCESS} Active" if user.is_active else f"{IMPORTANT} Blocked"
    if active_block is None:
        block_line = f"{PENDING} No active block"
    else:
        until = active_block.expires_at.strftime("%Y-%m-%d %H:%M") if active_block.expires_at else "permanent"
        block_line = f"{IMPORTANT} Blocked {KV} {esc(active_block.reason or 'no reason')} {KV} until {until}"
    return (
        f"{HEADER} 𝗨𝘀𝗲𝗿 {KV} {user.id}\n\n{SEPARATOR}\n\n"
        f"{SECTION} 𝗣𝗿𝗼𝗳𝗶𝗹𝗲\n\n"
        f"{ITEM} Name {KV} {esc(user.display_name)}\n"
        f"{ITEM} Username {KV} {esc(user.handle)}\n"
        f"{ITEM} Premium {KV} {IMPORTANT if user.is_premium else PENDING} {'Yes' if user.is_premium else 'No'}\n\n"
        f"{SECTION} 𝗔𝗰𝘁𝗶𝘃𝗶𝘁𝘆\n\n"
        f"{ITEM} Requests {KV} {human_int(user.request_count)}\n"
        f"{ITEM} Favorites {KV} {human_int(favorites)}\n\n"
        f"{SECTION} 𝗦𝘁𝗮𝘁𝘂𝘀\n\n{status}\n{block_line}\n\n"
        f"{SECTION} 𝗡𝗼𝘁𝗲𝘀\n\n{ITEM} {human_int(notes)} on file {KV} blocks {human_int(blocks)}\n\n"
        f"{SEPARATOR}"
    )


def block_confirm(*, user_id: int, handle: str, reason: str, until: str) -> str:
    return (
        f"{IMPORTANT} 𝗕𝗹𝗼𝗰𝗸 𝗨𝘀𝗲𝗿\n\n{SEPARATOR}\n\n"
        f"{ITEM} User {KV} {user_id}\n"
        f"{ITEM} Username {KV} {esc(handle)}\n"
        f"{ITEM} Reason {KV} {esc(reason)}\n"
        f"{ITEM} Duration {KV} {esc(until)}\n\n"
        "Confirm this action.\n\n"
        f"{SEPARATOR}"
    )


def block_done(*, user_id: int, admin_id: int, reason: str) -> str:
    return (
        f"{SUCCESS} 𝗕𝗹𝗼𝗰𝗸𝗲𝗱\n\n{SEPARATOR}\n\n"
        f"{ITEM} User {KV} {user_id}\n"
        f"{ITEM} By {KV} {admin_id}\n"
        f"{ITEM} Reason {KV} {esc(reason)}\n"
        f"{ITEM} Logged {KV} audit entry written\n\n"
        f"{SEPARATOR}"
    )


def unblock_done(user_id: int) -> str:
    return (
        f"{SUCCESS} 𝗨𝗻𝗯𝗹𝗼𝗰𝗸𝗲𝗱\n\n{SEPARATOR}\n\n"
        f"{ITEM} User {KV} {user_id}\n"
        f"{ITEM} Status {KV} {SUCCESS} Active\n\n"
        f"{SEPARATOR}"
    )


def blocked_list(total: int, page_label: str) -> str:
    return (
        f"{IMPORTANT} 𝗕𝗹𝗼𝗰𝗸𝗲𝗱 𝗨𝘀𝗲𝗿𝘀\n\n{SEPARATOR}\n\n"
        f"{ITEM} Active blocks {KV} {human_int(total)}\n"
        f"{ITEM} Page {KV} {page_label}\n\n"
        "Tap an entry to open the user card."
    )


def broadcast_prompt() -> str:
    return (
        f"{ACCENT} 𝗕𝗿𝗼𝗮𝗱𝗰𝗮𝘀𝘁\n\n{SEPARATOR}\n\n"
        "Send the message to broadcast.\n\n"
        f"{ITEM} Supports {KV} text or photo with caption\n"
        f"{ITEM} Audience {KV} all non-blocked users\n"
        f"{ITEM} Cancel {KV} /cancel\n\n"
        f"{SEPARATOR}"
    )


def broadcast_preview(*, audience: int, rate: int, body: str) -> str:
    return (
        f"{HEADER} 𝗕𝗿𝗼𝗮𝗱𝗰𝗮𝘀𝘁 𝗣𝗿𝗲𝘃𝗶𝗲𝘄\n\n{SEPARATOR}\n\n"
        f"{ITEM} Audience {KV} {human_int(audience)} users\n"
        f"{ITEM} Rate {KV} {rate} per second\n\n"
        f"{SECTION} 𝗠𝗲𝘀𝘀𝗮𝗴𝗲\n\n{esc(truncate(body, 600))}\n\n"
        f"{SEPARATOR}"
    )


def broadcast_progress(sent: int, failed: int, total: int) -> str:
    return (
        f"{ACCENT} 𝗕𝗿𝗼𝗮𝗱𝗰𝗮𝘀𝘁 𝗥𝘂𝗻𝗻𝗶𝗻𝗴\n\n{SEPARATOR}\n\n"
        f"{ITEM} Sent {KV} {human_int(sent)} / {human_int(total)}\n"
        f"{ITEM} Failed {KV} {human_int(failed)}\n\n"
        f"{SEPARATOR}"
    )


def broadcast_summary(*, sent: int, failed: int, cancelled: bool, duration: str, admin_id: int) -> str:
    title = f"{PENDING} 𝗕𝗿𝗼𝗮𝗱𝗰𝗮𝘀𝘁 𝗦𝘁𝗼𝗽𝗽𝗲𝗱" if cancelled else f"{SUCCESS} 𝗕𝗿𝗼𝗮𝗱𝗰𝗮𝘀𝘁 𝗖𝗼𝗺𝗽𝗹𝗲𝘁𝗲"
    return (
        f"{title}\n\n{SEPARATOR}\n\n"
        f"{ITEM} Delivered {KV} {human_int(sent)}\n"
        f"{ITEM} Failed {KV} {human_int(failed)}\n"
        f"{ITEM} Duration {KV} {duration}\n"
        f"{ITEM} Sent by {KV} {admin_id}\n\n"
        f"{SEPARATOR}"
    )


def export_ready(*, dataset: str, rows: int, columns: str) -> str:
    return (
        f"{SUCCESS} 𝗘𝘅𝗽𝗼𝗿𝘁 𝗥𝗲𝗮𝗱𝘆\n\n{SEPARATOR}\n\n"
        f"{ITEM} Dataset {KV} {esc(dataset)}\n"
        f"{ITEM} Rows {KV} {human_int(rows)}\n"
        f"{ITEM} Columns {KV} {esc(columns)}\n\n"
        f"{SEPARATOR}"
    )


def logs_text(*, entries: int, page_label: str, rows: list[str]) -> str:
    body = "\n".join(f"{ITEM} {strip_surrogates(row)}" for row in rows) or f"{PENDING} No entries on this page"
    return (
        f"{HEADER} 𝗔𝘂𝗱𝗶𝘁 𝗟𝗼𝗴\n\n{SEPARATOR}\n\n"
        f"{ITEM} Entries {KV} {human_int(entries)}\n"
        f"{ITEM} Page {KV} {page_label}\n\n{body}"
    )


def health_text(*, mode: str, uptime: str, version: str, source_ok: bool, latency: int | None, cache: dict, db_bytes: int, sessions: int, pending_deletions: int, ttl_label: str) -> str:
    return (
        f"{HEADER} 𝗛𝗲𝗮𝗹𝘁𝗵\n\n{SEPARATOR}\n\n"
        f"{SECTION} 𝗥𝘂𝗻𝘁𝗶𝗺𝗲\n\n"
        f"{ITEM} Mode {KV} {IMPORTANT} {esc(mode)}\n"
        f"{ITEM} Uptime {KV} {uptime}\n"
        f"{ITEM} Version {KV} {esc(version)}\n\n"
        f"{SECTION} 𝗦𝗼𝘂𝗿𝗰𝗲\n\n"
        f"{SUCCESS if source_ok else IMPORTANT} {'Reachable' if source_ok else 'Unreachable'}\n"
        f"{ITEM} Latency {KV} {f'{latency} ms' if latency else '-'}\n\n"
        f"{SECTION} 𝗗𝗮𝘁𝗮\n\n"
        f"{ITEM} Database {KV} {db_bytes / 1024:.1f} KB\n"
        f"{ITEM} Post cache {KV} {human_int(cache.get('posts', 0))}\n"
        f"{ITEM} Cache hits {KV} {human_int(cache.get('hits', 0))}\n"
        f"{ITEM} Sessions {KV} {human_int(sessions)}\n"
        f"{ITEM} Pending deletes {KV} {human_int(pending_deletions)}\n"
        f"{ITEM} Auto-delete {KV} {ttl_label}\n\n"
        f"{SEPARATOR}"
    )


def admins_text(counts: dict, rows: list[str]) -> str:
    body = "\n".join(f"{ITEM} {strip_surrogates(row)}" for row in rows) or f"{PENDING} Only you so far"
    return (
        f"{HEADER} 𝗔𝗱𝗺𝗶𝗻𝘀\n\n{SEPARATOR}\n\n"
        f"{ITEM} Owners {KV} {counts.get('owner', 0)}\n"
        f"{ITEM} Admins {KV} {counts.get('admin', 0)}\n"
        f"{ITEM} Moderators {KV} {counts.get('moderator', 0)}\n\n"
        f"{SECTION} 𝗘𝗻𝘁𝗿𝗶𝗲𝘀\n\n{body}\n\n"
        f"{SEPARATOR}"
    )


def global_stats(*, totals: dict, users: dict, views: int, favorites: int) -> str:
    return (
        f"{HEADER} 𝗚𝗹𝗼𝗯𝗮𝗹 𝗦𝘁𝗮𝘁𝘀\n\n{SEPARATOR}\n\n"
        f"{SECTION} 𝗨𝘀𝗲𝗿𝘀\n\n"
        f"{ITEM} Total {KV} {human_int(users.get('total', 0))}\n"
        f"{ITEM} New today {KV} {human_int(users.get('new_today', 0))}\n"
        f"{ITEM} Active 24h {KV} {human_int(users.get('active_24h', 0))}\n"
        f"{ITEM} Blocked {KV} {human_int(users.get('blocked', 0))}\n\n"
        f"{SECTION} 𝗨𝘀𝗮𝗴𝗲\n\n"
        f"{ITEM} Requests today {KV} {human_int(totals.get('requests', 0))}\n"
        f"{ITEM} Posts viewed {KV} {human_int(views)}\n"
        f"{ITEM} Favorites {KV} {human_int(favorites)}\n"
        f"{ITEM} Broadcasts {KV} {human_int(totals.get('broadcasts', 0))}\n\n"
        f"{SEPARATOR}"
    )


def source_unavailable(reason: str) -> str:
    return (
        f"{text_alert('𝗜𝗠𝗣𝗢𝗥𝗧𝗔𝗡𝗧')}\n\n"
        f"{IMPORTANT} 𝗦𝗼𝘂𝗿𝗰𝗲 𝗨𝗻𝗮𝘃𝗮𝗶𝗹𝗮𝗯𝗹𝗲\n{SEPARATOR}\n\n"
        "The requested operation could not be completed.\n\n"
        f"{ITEM} Reason {KV} {esc(truncate(reason, 120))}\n"
        f"{ITEM} Retry {KV} try again in a moment\n\n"
        f"{SEPARATOR}"
    )


def source_changed() -> str:
    return (
        f"{text_alert('𝗜𝗠𝗣𝗢𝗥𝗧𝗔𝗡𝗧')}\n\n"
        f"{IMPORTANT} 𝗦𝗼𝘂𝗿𝗰𝗲 𝗨𝗽𝗱𝗮𝘁𝗲𝗱\n{SEPARATOR}\n\n"
        "This page could not be read.\n\n"
        f"{ITEM} Reason {KV} the source changed its layout\n"
        f"{ITEM} Action {KV} the maintainer has been notified\n\n"
        f"{SEPARATOR}"
    )


def text_alert(label: str) -> str:
    return f"\u3010 {label} \u3011"


def rate_limited(rate: int, period: float) -> str:
    return (
        f"{PENDING} 𝗦𝗹𝗼𝘄 𝗗𝗼𝘄𝗻\n\n{SEPARATOR}\n\n"
        "Too many requests.\n\n"
        f"{ITEM} Limit {KV} {rate} per {int(period)} seconds\n"
        f"{ITEM} Retry {KV} in a few seconds\n"
    )


def maintenance_notice() -> str:
    return (
        f"{IMPORTANT} 𝗠𝗮𝗶𝗻𝘁𝗲𝗻𝗮𝗻𝗰𝗲\n\n{SEPARATOR}\n\n"
        "The bot is being updated.\n\n"
        f"{ITEM} Status {KV} {PENDING} Temporary\n"
        f"{ITEM} Please try again shortly\n\n"
        f"{SEPARATOR}"
    )


def blocked_notice(reason: str, since: datetime | None, support: str) -> str:
    return (
        f"{IMPORTANT} 𝗔𝗰𝗰𝗲𝘀𝘀 𝗥𝗲𝘀𝘁𝗿𝗶𝗰𝘁𝗲𝗱\n\n{SEPARATOR}\n\n"
        "You cannot use this bot.\n\n"
        f"{ITEM} Reason {KV} {esc(reason or 'not specified')}\n"
        f"{ITEM} Since {KV} {since.strftime('%Y-%m-%d') if since else '-'}\n"
        f"{ITEM} Question {KV} contact {esc(support)}\n\n"
        f"{SEPARATOR}"
    )


def unknown_input() -> str:
    return (
        f"{PENDING} 𝗨𝗻𝗸𝗻𝗼𝘄𝗻 𝗜𝗻𝗽𝘂𝘁\n\n{SEPARATOR}\n\n"
        "That input was not recognised.\n\n"
        f"{ITEM} Try {KV} /help\n"
        f"{ITEM} Or pick a section below\n\n"
        f"{SEPARATOR}"
    )


def mirror_action(*, action: str, target: str, admin_id: int, reason: str | None, when: datetime) -> str:
    body = (
        f"{IMPORTANT} 𝗔𝗱𝗺𝗶𝗻 𝗔𝗰𝘁𝗶𝗼𝗻\n\n{SEPARATOR}\n\n"
        f"{ITEM} Action {KV} {esc(action)}\n"
        f"{ITEM} Target {KV} {esc(target)}\n"
        f"{ITEM} By {KV} {admin_id}\n"
    )
    if reason:
        body += f"{ITEM} Reason {KV} {esc(reason)}\n"
    body += f"{ITEM} Time {KV} {when.strftime('%Y-%m-%d %H:%M')}\n\n{SEPARATOR}"
    return body


def mirror_error(*, where: str, kind: str, user_id: int | None, when: datetime) -> str:
    return (
        f"{IMPORTANT} 𝗕𝗼𝘁 𝗘𝗿𝗿𝗼𝗿\n\n{SEPARATOR}\n\n"
        f"{ITEM} Where {KV} {esc(where)}\n"
        f"{ITEM} Type {KV} {esc(kind)}\n"
        f"{ITEM} User {KV} {user_id or '-'}\n"
        f"{ITEM} Time {KV} {when.strftime('%Y-%m-%d %H:%M')}\n\n"
        f"{SEPARATOR}"
    )


def about(version: str, ttl_label: str, source: str) -> str:
    return (
        f"{HEADER} 𝗔𝗯𝗼𝘂𝘁\n\n{SEPARATOR}\n\n"
        f"{ITEM} Version {KV} {esc(version)}\n"
        f"{ITEM} Source {KV} {esc(source)}\n"
        f"{ITEM} Media {KV} auto-deleted after {ttl_label}\n\n"
        f"{SECTION} 𝗡𝗼𝘁𝗶𝗰𝗲\n\n"
        "Content belongs to its original creators. Media is fetched from the\n"
        "public source, never re-hosted, and removed from your chat automatically.\n\n"
        f"{SEPARATOR}"
    )