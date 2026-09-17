from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.config import settings
from bot.services.pagination import window
from bot.texts import symbols as S

BACK_LABELS = {
    'search': 'Main menu',
    'listing': 'Main menu',
    'saved_posts': 'Main menu',
    'saved_images': 'Main menu',
    'history': 'Main menu',
}


def _btn(text, data):
    return InlineKeyboardButton(text=text, callback_data=data)


def _chunks(values, size):
    size = max(1, size)
    return [list(values[i:i + size]) for i in range(0, len(values), size)]


def main_kb(has_continue: bool = False):
    rows = []
    if has_continue:
        rows.append([_btn("Continue where you left off", "menu:continue")])
    rows += [
        [_btn("Search", "menu:search"), _btn("Random", "menu:random")],
        [_btn("Latest", "menu:latest"), _btn("Popular", "menu:popular")],
        [_btn("Categories", "menu:categories"), _btn("Saved", "menu:saved")],
        [_btn("History", "menu:history"), _btn("Settings", "menu:settings")],
        [_btn("Friends", "menu:friends"), _btn("Help", "menu:help")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def friend_request_kb(request_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_btn("Approve", f"friend:accept:{request_id}"), _btn("Decline", f"friend:decline:{request_id}")],
        ]
    )


def friend_management_kb(rows):
    buttons = []
    for friendship, user in rows:
        label = f"{user.username and '@' + user.username or user.display_name[:24]}"
        permission = "Send on" if friendship.send_allowed else "Send off"
        buttons.append([
            _btn(f"{label} {S.DOT} {permission}", f"friends:send:{user.id}"),
            _btn("Remove", f"friends:remove:{user.id}"),
        ])
    buttons.append([_btn(f"{S.PREV} Main menu", "menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def saved_empty_kb(sid, tab, posts, images):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                _btn(f"{S.TABS_ON if tab == 'posts' else S.TABS_OFF} Posts {S.DOT} {posts}", f"f:{sid}:tab:posts"),
                _btn(f"{S.TABS_ON if tab == 'images' else S.TABS_OFF} Images {S.DOT} {images}", f"f:{sid}:tab:images"),
            ],
            [_btn(f"{S.PREV} Main menu", "menu:main")],
        ]
    )


def card_kb(ns, sid, index, total, mode, has_next=False, tabs=None):


    rows = []
    if tabs:
        rows.append([_btn(label, data) for label, data in tabs])
    label = f"{index} / {total}{'+' if has_next else ''}"
    if total > 1:
        nav = []
        if index > 1:
            nav.append(_btn(f"{S.PREV} Previous", f"{ns}:{sid}:prev"))
        if settings.nav_page_jump:
            nav.append(_btn(f"{label} {S.DOT} Jump", f"{ns}:{sid}:jump"))
        else:
            nav.append(_btn(label, f"{ns}:{sid}:at:{index}"))
        if index < total or has_next:
            nav.append(_btn(f"Next {S.NEXT}", f"{ns}:{sid}:next"))
        rows.append(nav)
        numbers = window(index, total)
        if len(numbers) > 1:
            for chunk in _chunks(numbers, settings.nav_numbers_per_row):
                rows.append([_btn(str(n), f"{ns}:{sid}:at:{n}") for n in chunk])
    actions = []
    if mode in ('search', 'listing'):
        actions.append(_btn("Open gallery", f"{ns}:{sid}:open"))
    elif mode == 'saved_images':
        actions.append(_btn("Open in gallery", f"{ns}:{sid}:open"))
        actions.append(_btn("Remove", f"{ns}:{sid}:remove"))
    elif mode in ('saved_posts', 'history'):
        actions.append(_btn("Open gallery", f"{ns}:{sid}:open"))
        actions.append(_btn("Remove", f"{ns}:{sid}:remove"))
    if actions:
        rows.append(actions)
    rows.append([_btn(f"{S.PREV} {BACK_LABELS.get(mode, 'Back')}", f"{ns}:{sid}:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def gallery_kb(sid, index, total, saved_image=False, saved_post=False):
    rows = []
    if total > 1:
        nav = []
        if index > 1:
            nav.append(_btn(f"{S.PREV} Previous", f"g:{sid}:prev"))
        if settings.nav_page_jump:
            nav.append(_btn(f"{index} / {total} {S.DOT} Jump", f"g:{sid}:jump"))
        else:
            nav.append(_btn(f"{index} / {total}", f"g:{sid}:at:{index}"))
        if index < total:
            nav.append(_btn(f"Next {S.NEXT}", f"g:{sid}:next"))
        rows.append(nav)
        rows.append(
            [
                _btn("First", f"g:{sid}:first"),
                _btn("-5", f"g:{sid}:minus5"),
                _btn("+5", f"g:{sid}:plus5"),
                _btn("Last", f"g:{sid}:last"),
            ]
        )
        numbers = window(index, total)
        if len(numbers) > 1:
            for chunk in _chunks(numbers, settings.nav_numbers_per_row):
                rows.append([_btn(str(n), f"g:{sid}:at:{n}") for n in chunk])
    rows.append(
        [
            _btn(f"{S.STAR_ON} Saved image" if saved_image else f"{S.STAR} Save image", f"g:{sid}:saveimg"),
            _btn(f"{S.STAR_ON} Saved post" if saved_post else f"{S.STAR} Save post", f"g:{sid}:savepost"),
        ]
    )
    rows.append(
        [
            _btn("Information", f"g:{sid}:info"),
            _btn(f"{S.DOWNLOAD} Download", f"g:{sid}:download"),
            _btn("Share", f"g:{sid}:share"),
        ]
    )
    rows.append([_btn("Send to friends", f"g:{sid}:sendfriends")])
    rows.append([_btn(f"{S.PREV} Back to list", f"g:{sid}:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def friend_send_kb(sid, rows, selected, message_preview=''):
    buttons = []
    for friendship, user in rows:
        mark = "[x]" if user.id in selected else "[ ]"
        label = user.username and f"@{user.username}" or user.display_name
        buttons.append([_btn(f"{mark} {label[:28]}", f"fs:{sid}:toggle:{user.id}")])
    if message_preview:
        buttons.append([_btn("Edit message", f"fs:{sid}:message")])
    else:
        buttons.append([_btn("Add message", f"fs:{sid}:message")])
    buttons.append([_btn("Send", f"fs:{sid}:send"), _btn("Cancel", f"fs:{sid}:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def delivered_friend_message_kb(post_url, sender_id):
    username = settings.bot_username.lstrip('@')
    slug = post_url.rstrip('/').split('/')[-1]
    link = f"https://t.me/{username}?start=post-{slug}" if username else post_url
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="View post", url=link)],
            [_btn("Delete", "fmsg:delete"), _btn("Revoke send permission", f"fmsg:revoke:{sender_id}")],
        ]
    )


def album_kb(sid, batch, batches):
    rows = []
    if batches > 1:
        nav = []
        if batch > 1:
            nav.append(_btn(f"{S.PREV} Previous album", f"g:{sid}:albumprev"))
        nav.append(_btn(f"{batch} / {batches}", f"g:{sid}:albumat:{batch}"))
        if batch < batches:
            nav.append(_btn(f"Next album {S.NEXT}", f"g:{sid}:albumnext"))
        rows.append(nav)
    rows.append([_btn(f"{S.PREV} Back to list", f"g:{sid}:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def categories_kb(sid, entries, page, pages):
    """entries: iterable of (global_index, name)."""
    rows = []
    for pair in _chunks(list(entries), 2):
        rows.append([_btn(name[:28], f"c:{sid}:at:{index}") for index, name in pair])
    if pages > 1:
        nav = []
        if page > 1:
            nav.append(_btn(f"{S.PREV} Prev", f"c:{sid}:page:{page - 1}"))
        nav.append(_btn(f"{page} / {pages}", f"c:{sid}:page:{page}"))
        if page < pages:
            nav.append(_btn(f"Next {S.NEXT}", f"c:{sid}:page:{page + 1}"))
        rows.append(nav)
    rows.append([_btn(f"{S.PREV} Main menu", "menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def settings_kb(setting):
    rows = [
        [_btn(f"Delivery {S.DOT} {'album' if setting.delivery_mode == 'album' else 'single'}", "set:delivery")],
        [_btn(f"Images per page {S.DOT} {setting.images_per_page}", "set:perpage")],
        [_btn(f"Thumbnails {S.DOT} {'on' if setting.show_thumbnails else 'off'}", "set:thumbs")],
        [_btn(f"Numbered rows {S.DOT} {'on' if setting.numbered_nav else 'off'}", "set:numbers")],
        [_btn(f"{S.PREV} Main menu", "menu:main")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_kb(maintenance=False):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_btn("Users", "a:users:1"), _btn("Find user", "a:find")],
            [_btn("Broadcast", "a:broadcast"), _btn("Stats", "a:stats")],
            [_btn("Export CSV", "a:export"), _btn("Audit log", "a:audit")],
            [_btn(f"Maintenance {'off' if maintenance else 'on'}", "a:maintenance")],
        ]
    )


def users_list_kb(page, pages, entries):
    """entries: iterable of (user_id, label)."""
    rows = [[_btn(label[:60], f"a:user:{user_id}")] for user_id, label in entries]
    if pages > 1:
        nav = []
        if page > 1:
            nav.append(_btn(f"{S.PREV} Prev", f"a:users:{page - 1}"))
        nav.append(_btn(f"{page} / {pages}", f"a:users:{page}"))
        if page < pages:
            nav.append(_btn(f"Next {S.NEXT}", f"a:users:{page + 1}"))
        rows.append(nav)
    rows.append([_btn(f"{S.PREV} Admin", "a:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def user_card_kb(user_id, is_active):
    action = ("Block", "a:block") if is_active else ("Unblock", "a:unblock")
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_btn(action[0], f"{action[1]}:{user_id}")],
            [_btn("Saved posts", f"a:saved:{user_id}"), _btn("History", f"a:history:{user_id}")],
            [_btn(f"{S.PREV} Back to users", "a:users:1")],
        ]
    )


def admin_back_kb(target='a:home', label='Admin'):
    return InlineKeyboardMarkup(inline_keyboard=[[_btn(f"{S.PREV} {label}", target)]])


def broadcast_kb(segments, current, can_send):
    rows = [
        [_btn(f"{S.ACTIVE if key == current else S.PENDING} {label}", f"b:seg:{key}")]
        for key, label in segments
    ]
    if can_send:
        rows.append([_btn("Send now", "b:send")])
    rows.append([_btn("Cancel", "b:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def broadcast_control_kb(run_id, paused=False):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_btn("Resume" if paused else "Pause", f"b:{'resume' if paused else 'pause'}:{run_id}")],
            [_btn("Cancel run", f"b:cancel_run:{run_id}")],
        ]
    )
