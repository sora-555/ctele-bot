"""Message builders.

Every builder returns Telegram HTML that follows telegram_skills.md: one header
symbol, one list symbol, one separator, one key/value separator, no emoji.
"""

from html import escape

from bot.texts import symbols as S


def safe(value) -> str:
    return escape(str(value or ""), quote=False)


def kv(label, value) -> str:
    return f"{S.BULLET} {label} {S.DOT} {value}"


def bullet(text) -> str:
    return f"{S.BULLET} {text}"


def screen(title, body: str = "", footer: str = "") -> str:
    parts = [f"{S.HEADER} <b>{safe(title)}</b>", S.RULE]
    if body:
        parts.append("")
        parts.append(body)
    if footer:
        parts.append("")
        parts.append(S.RULE)
        parts.append(footer)
    return "\n".join(parts)


def main_menu(user, saved_posts: int = 0, saved_images: int = 0, last_title: str | None = None) -> str:
    body = [kv("Name", safe(user.first_name or "there"))]
    if saved_posts or saved_images:
        body.append(kv("Saved", f"{saved_posts} posts {S.DOT} {saved_images} images"))
    if last_title:
        body.append(kv("Continue", safe(last_title)))
    body.append("")
    body.append(f"{S.SECTION} <b>Browse</b>")
    body.append(bullet("Search any character, series or model"))
    body.append(bullet("Latest, popular and random picks"))
    body.append(bullet("Categories with full listings"))
    return screen("CosplayTele", "\n".join(body))


def help_text() -> str:
    body = [
        f"{S.SECTION} <b>Browse</b>",
        bullet("/search &lt;query&gt;"),
        bullet("/latest, /categories, /random, /popular"),
        "",
        f"{S.SECTION} <b>Your library</b>",
        bullet("/favorites, /history, /profile, /settings"),
        "",
        f"{S.SECTION} <b>Other</b>",
        bullet("/menu, /help, /about, /cancel"),
    ]
    return screen("Commands", "\n".join(body))


def about_text(base_url: str) -> str:
    return screen(
        "About",
        "\n".join(
            [
                "A Telegram browser for CosplayTele galleries.",
                "Search, gallery controls and saved items stay on one evolving screen.",
                "",
                kv("Source", safe(base_url)),
                kv("Delivery", "single image, editable message"),
            ]
        ),
    )


def search_prompt() -> str:
    return screen(
        "Search",
        "\n".join(
            [
                "Send a name, character, series or model.",
                "You can also paste a cosplaytele.com link.",
                "",
                kv("Tip", "/cancel to leave search"),
            ]
        ),
    )


def result_card(title, item, index, total, has_next: bool = False, note: str | None = None, ttl_minutes: int | None = None) -> str:
    position = f"{index} / {total}{'+' if has_next else ''}"
    body = [f"<b>{safe(item.get('title'))}</b>", "", kv("Result", position)]
    if item.get("subtitle"):
        body.append(kv("Source", safe(item["subtitle"])))
    if note:
        body.append(kv("Info", note))
    if ttl_minutes:
        body.append(kv("Auto-delete", f"{ttl_minutes} min"))
    return screen(title, "\n".join(body))


def gallery_caption(post, index, saved: bool = False, ttl_minutes: int | None = None) -> str:
    total = len(post.images)
    body = [f"<b>{safe(post.title)}</b>", "", kv("Image", f"{index} / {total}")]
    if saved:
        body.append(f"{S.STAR_ON} Saved image")
    if ttl_minutes:
        body.append(kv("Auto-delete", f"{ttl_minutes} min"))
    return screen("Gallery", "\n".join(body))


def info_text(post, index, saved_images: int = 0) -> str:
    genres = ", ".join(safe(item) for item in post.genres) or "unknown"
    published = post.upload_date.strftime("%Y-%m-%d") if post.upload_date else "unknown"
    body = [
        f"<b>{safe(post.title)}</b>",
        "",
        kv("Images", len(post.images)),
        kv("Category", genres),
        kv("Published", published),
    ]
    if saved_images:
        body.append(kv("Saved", f"{saved_images} from this post"))
    body.append("")
    body.append(kv("Position", f"image {index} of {len(post.images)}"))
    return screen("Post information", "\n".join(body))


def saved_home(tab: str, posts: int, images: int) -> str:
    body = [
        kv("Saved posts", posts),
        kv("Saved images", images),
        "",
        kv("Tab", "posts" if tab == "posts" else "images"),
    ]
    return screen("Saved", "\n".join(body))


def saved_empty(tab: str) -> str:
    if tab == "images":
        hint = "Open any gallery and tap Save image to keep a single image."
    else:
        hint = "Open any gallery and tap Save post to keep the whole set."
    return screen("Saved", "\n".join([f"{S.SECTION} <b>Nothing here yet</b>", "", bullet(hint)]))


def history_empty() -> str:
    return screen(
        "History",
        "\n".join([f"{S.SECTION} <b>Nothing here yet</b>", "", bullet("Galleries you open show up here.")]),
    )


def categories_text(count: int) -> str:
    return screen(
        "Categories",
        "\n".join([kv("Available", count), "", bullet("Pick a category to browse its posts.")]),
    )


def profile_text(user, saved_posts: int, saved_images: int, viewed: int) -> str:
    body = [
        kv("Name", safe(" ".join(filter(None, [user.first_name, user.last_name])) or "unknown")),
        kv("Username", f"@{safe(user.username)}" if user.username else "not set"),
        kv("User id", f"<code>{user.id}</code>"),
        "",
        kv("Joined", user.created_at.strftime("%Y-%m-%d") if user.created_at else "unknown"),
        kv("Interactions", user.request_count or 0),
        "",
        kv("Saved posts", saved_posts),
        kv("Saved images", saved_images),
        kv("Viewed", viewed),
        kv("Status", f"{S.CHECK} active" if user.is_active else f"{S.CROSS} blocked"),
    ]
    return screen("Your profile", "\n".join(body))


def settings_text(setting, ttl_minutes: int, auto_delete: bool) -> str:
    body = [
        kv("Delivery", "album" if setting.delivery_mode == "album" else "single image"),
        kv("Images per page", setting.images_per_page),
        kv("Thumbnails", "on" if setting.show_thumbnails else "off"),
        kv("Numbered rows", "on" if setting.numbered_nav else "off"),
        kv("Auto-delete", f"{ttl_minutes} min" if auto_delete else "off"),
        "",
        bullet("Tap a row to change it. Changes apply instantly."),
    ]
    return screen("Settings", "\n".join(body))


def jump_prompt(label: str, current: int, total: int) -> str:
    return screen("Jump", "\n".join([kv(label, current), kv("Range", f"1 to {total}"), "", "/cancel to stop"]))


def admin_home(stats: dict) -> str:
    body = [
        f"{S.SECTION} <b>Users</b>",
        kv("Total", stats.get("total", 0)),
        kv("Active", stats.get("active", 0)),
        kv("New today", stats.get("new_today", 0)),
        kv("Blocked by bot", stats.get("bot_blocked", 0)),
        "",
        f"{S.SECTION} <b>Content</b>",
        kv("Saved posts", stats.get("favorites", 0)),
        kv("Saved images", stats.get("saved_images", 0)),
        kv("Views logged", stats.get("history", 0)),
        "",
        f"{S.SECTION} <b>Traffic</b>",
        kv("Active 24h", stats.get("dau", 0)),
        kv("Active 7d", stats.get("wau", 0)),
    ]
    return screen("Admin panel", "\n".join(body))


def user_card(user, saved_posts: int, saved_images: int, viewed: int) -> str:
    status = f"{S.CHECK} active" if user.is_active else f"{S.CROSS} blocked"
    if user.bot_blocked:
        status = f"{S.CROSS} blocked the bot"
    body = [
        kv("Name", safe(" ".join(filter(None, [user.first_name, user.last_name])) or "unknown")),
        kv("Username", f"@{safe(user.username)}" if user.username else "not set"),
        kv("User id", f"<code>{user.id}</code>"),
        kv("Language", safe(user.language_code) or "unknown"),
        "",
        kv("Joined", user.created_at.strftime("%Y-%m-%d %H:%M") if user.created_at else "unknown"),
        kv("Last seen", user.last_seen_at.strftime("%Y-%m-%d %H:%M") if user.last_seen_at else "unknown"),
        kv("Interactions", user.request_count or 0),
        "",
        kv("Saved posts", saved_posts),
        kv("Saved images", saved_images),
        kv("Viewed", viewed),
        kv("Status", status),
    ]
    if user.blocked_reason:
        body.append(kv("Reason", safe(user.blocked_reason)))
    return screen("User card", "\n".join(body))


def users_page(rows, total: int, page: int, pages: int) -> str:
    body = [kv("Users", total), kv("Page", f"{page} / {pages}"), "", bullet("Pick a user to open the card.")]
    return screen("Users", "\n".join(body))


def find_prompt() -> str:
    return screen(
        "Find user",
        "\n".join(
            [
                "Send a user id, @username or a name fragment.",
                "",
                bullet("Example: 5103772471"),
                bullet("Example: @cosplayfan"),
                "",
                "/cancel to stop",
            ]
        ),
    )


def broadcast_prompt() -> str:
    return screen(
        "Broadcast",
        "\n".join(
            [
                f"{S.SECTION} <b>Compose</b>",
                bullet("Send the message to deliver (text, photo, video, album)."),
                bullet("Link previews and formatting are preserved."),
                "",
                kv("Next", "preview, segment, confirm"),
                "",
                "/cancel to stop",
            ]
        ),
    )


def broadcast_preview(segment_label: str, recipients: int) -> str:
    return screen(
        "Broadcast preview",
        "\n".join(
            [
                "<b>Draft above</b>",
                "",
                kv("Segment", segment_label),
                kv("Recipients", recipients),
                "",
                bullet("Nothing is sent until you confirm."),
            ]
        ),
    )


def broadcast_progress(run, eta: str, rate: int) -> str:
    processed = (run.sent or 0) + (run.failed or 0) + (run.blocked or 0)
    total = run.total or 0
    percent = int(processed * 100 / total) if total else 0
    body = [
        kv("Status", run.status),
        kv("Progress", f"{processed} / {total} ({percent}%)"),
        "",
        kv("Sent", run.sent or 0),
        kv("Blocked", run.blocked or 0),
        kv("Failed", run.failed or 0),
        "",
        kv("Rate", f"{rate} per second"),
        kv("Remaining", eta),
    ]
    return screen("Broadcast running", "\n".join(body))


def broadcast_summary(run) -> str:
    body = [
        kv("Status", run.status),
        kv("Recipients", run.total or 0),
        "",
        kv("Sent", run.sent or 0),
        kv("Blocked", run.blocked or 0),
        kv("Failed", run.failed or 0),
    ]
    if run.errors:
        body.append("")
        body.append(kv("Sample errors", safe(run.errors[:300])))
    return screen("Broadcast finished", "\n".join(body))


def stats_text(stats: dict, top_posts, top_queries) -> str:
    body = [
        f"{S.SECTION} <b>Users</b>",
        kv("Total", stats.get("total", 0)),
        kv("Active", stats.get("active", 0)),
        kv("New today", stats.get("new_today", 0)),
        kv("New 7d", stats.get("new_week", 0)),
        kv("Active 24h", stats.get("dau", 0)),
        kv("Active 7d", stats.get("wau", 0)),
    ]
    if top_posts:
        body.append("")
        body.append(f"{S.SECTION} <b>Top saved posts</b>")
        for title, count in top_posts:
            body.append(f"{S.BULLET} {safe(title)[:60]} {S.DOT} {count}")
    if top_queries:
        body.append("")
        body.append(f"{S.SECTION} <b>Top searches</b>")
        for query, count in top_queries:
            body.append(f"{S.BULLET} {safe(query)} {S.DOT} {count}")
    return screen("Statistics", "\n".join(body))


def notice(title: str, message: str) -> str:
    return screen(title, message)
