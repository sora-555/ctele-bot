# PLAN.md — CosplayTele Telegram Bot

❖ 𝗖𝗼𝘀𝗽𝗹𝗮𝘆𝗧𝗲𝗹𝗲 𝗕𝗼𝘁
━━━━━━━━━━━━━━━━━━━━

✦ 𝗢𝘃𝗲𝗿𝘃𝗶𝗲𝘄

A production-grade Telegram bot built on **aiogram v3** that wraps the local `ctele` SDK
(cosplaytele.com) and adds **full user management via SQLite + SQLAlchemy 2.0 async ORM**,
image-URL delivery (Telegram fetches), paginated galleries, and a complete admin/moderation
surface.

▸ Stack · aiogram 3.x · FastAPI + uvicorn · SQLAlchemy 2.0 (async) · aiosqlite · pydantic-settings · ctele SDK
▸ Entry point · `start.py` (root)
▸ Database · `Database.db` (root, auto-created)
▸ Source SDK · `ctele/` (supplied by you, imported from project root)
▸ Run mode · FastAPI/uvicorn host; polling by default (as an asyncio task), webhook optional

✦ 𝗚𝗼𝗮𝗹𝘀

✓ Browse cosplaytele.com from Telegram: latest, popular, categories, search, post detail
✓ View galleries with pagination, few images per page, sent as URL-only photos
✓ Search shows one result per screen with its own thumbnail, and steps through them in one message
✓ Every media message is auto-deleted after 30 minutes, and the user is told so on screen
✓ Persistent users: profile, settings, favorites, history, usage counters
✓ Admin surface: list/search/inspect users, block/unblock, broadcast, audit log, CSV export
✓ Clean, premium Telegram UI using the approved Unicode symbol system (no emoji)
✓ Resilient: caching, retries, throttling, graceful errors, safe restart
✓ Self-registering command menus — BotFather `/setcommands` is never needed
✓ One process serves both: FastAPI/uvicorn always, polling-as-task or webhook behind it
✓ Zip-and-run on a host: copy `ctele/`, edit `.env`, `python start.py`

✦ 𝗡𝗼𝗻-𝗚𝗼𝗮𝗹𝘀 (out of scope for v1)

○ Payments / subscriptions / premium tiers
○ Multi-language i18n (English only; `language` column reserved for later)
○ Re-uploading or re-hosting media on our own storage
○ Downloading images to disk (only used as an optional delivery fallback)
○ Scraping beyond what the `ctele` SDK already exposes

✦ 𝗗𝗲𝗹𝗶𝘃𝗲𝗿𝗮𝗯𝗹𝗲 𝗹𝗮𝘆𝗼𝘂𝘁 (bot.zip root)

```
├── start.py                  # entry point: config, logging, DB, commands, FastAPI + uvicorn, polling-as-task or webhook
├── requirements.txt          # pinned dependencies
├── .env                      # your live config (placeholders shipped)
├── .env.example              # documented template
├── Database.db               # created automatically on first run
├── README.md                 # setup + hosting guide
├── plan.md                   # this document
├── .gitignore
├── logs/                     # rotating log files (created at runtime)
└── bot/
    ├── __init__.py
    ├── config.py             # pydantic-settings Settings + .env loading
    ├── loader.py             # Bot + Dispatcher singletons
    ├── main.py               # dispatcher factory: routers, middlewares, error handler
    ├── commands.py           # auto command registration (set_my_commands + scopes)
    ├── api/
    │   ├── app.py            # FastAPI app factory + lifespan (owns the polling task)
    │   ├── webhook.py        # POST route: validates the secret, feeds the dispatcher
    │   └── health.py         # GET /, /healthz, /readyz for host uptime probes
    ├── database/
    │   ├── base.py           # engine, async_sessionmaker, DeclarativeBase, init_db()
    │   ├── models.py         # all ORM models
    │   └── repository/
    │       ├── users.py      # user CRUD, search, pagination, counters
    │       ├── admins.py     # roles, grant/revoke
    │       ├── content.py    # favorites + view history
    │       ├── moderation.py # blocks, notes, audit log, deletion queue
    │       ├── cache.py      # post + category cache
    │       └── stats.py      # daily counters, global aggregates
    ├── services/
    │   ├── ctele_service.py  # async wrapper over CTeleClient + retries + cache
    │   ├── delivery.py       # URL photo/album sending + optional byte fallback
    │   ├── deletion.py       # scheduled auto-delete of media + background sweeper
    │   ├── pagination.py     # generic Paginator (labels, page math, bounds)
    │   ├── sessions.py       # short-lived browse/gallery session store (sid -> payload)
    │   └── broadcast.py      # rate-limited fan-out with progress + abort
    ├── keyboards/
    │   ├── inline.py         # browse, post, gallery, settings, confirm menus
    │   ├── reply.py          # main reply keyboard
    │   └── admin.py          # admin panel keyboards
    ├── handlers/
    │   ├── common.py         # shared listing + gallery renderers, log-channel mirroring
    │   ├── start.py          # /start, age gate, /menu, /help, /about, /ping
    │   ├── browse.py         # /latest /popular /categories /category /search /random
    │   ├── posts.py          # post detail card, /post, /gallery, gallery pagination
    │   ├── account.py        # /profile /settings /stats /history /favorites
    │   ├── admin/
    │   │   ├── panel.py      # /admin hub
    │   │   ├── users.py      # /users /find /user /notes
    │   │   ├── moderation.py # /block /unblock /blocked
    │   │   ├── broadcast.py  # /broadcast FSM + progress + cancel
    │   │   ├── logs.py       # /logs audit viewer + /maintenance /reload /health
    │   │   ├── export.py     # /export users CSV
    │   │   └── roles.py      # /admins /addadmin /deladmin (owner only)
    │   ├── fallback.py       # unknown text/commands, callback fallback
    │   └── errors.py         # global error handler: log, reply, mirror
    ├── middlewares/
    │   ├── db.py             # per-update AsyncSession injection + commit/rollback
    │   ├── user.py           # upsert user, last_seen, counters, block gate
    │   ├── admin.py          # resolve admin role, owner flag
    │   ├── throttle.py       # anti-flood per user
    │   ├── maintenance.py    # lock bot to admins while enabled
    │   └── logging.py        # structured update logging
    ├── states/
    │   ├── admin.py          # broadcast / find / note / role FSM states
    │   └── user.py           # search-query FSM state
    ├── filters/
    │   ├── admin.py          # IsAdmin / IsOwner / RoleAtLeast
    │   └── chat.py           # private-only guards
    ├── texts/
    │   ├── ui.py             # all message templates (Unicode design system)
    │   └── symbols.py        # approved symbol constants + helpers
    └── utils/
        ├── logger.py         # console + rotating file logging, secret redaction
        ├── text.py           # HTML escaping, truncation, number formatting
        └── time.py           # naive-UTC helpers, relative time labels
```
━━━━━━━━━━━━━━━━━━━━

✦ 𝗖𝗼𝗻𝗳𝗶𝗴𝘂𝗿𝗮𝘁𝗶𝗼𝗻 (`.env`)

| Key | Default | Purpose |
| --- | --- | --- |
| `BOT_TOKEN` | — | Telegram bot token from BotFather (required) |
| `ADMIN_IDS` | — | Comma-separated Telegram IDs bootstrapped as `owner` |
| `LOG_CHANNEL_ID` | — | Optional channel ID for admin action / error mirror |
| `DATABASE_URL` | `sqlite+aiosqlite:///Database.db` | Async SQLAlchemy DSN |
| `SOURCE_BASE_URL` | `https://cosplaytele.com` | Passed to `CTeleClient(base_url=...)` |
| `SOURCE_REFERER` | `<base>/` | Referer header the source's hotlink guard expects |
| `SOURCE_USER_AGENT` | desktop Chrome UA | Overridable UA |
| `REQUEST_TIMEOUT` | `20` | Seconds, per outbound request |
| `MAX_RETRIES` | `2` | Transient-failure retries inside the service |
| `SOURCE_CONCURRENCY` | `8` | Global semaphore on outbound SDK calls |
| `THROTTLE_RATE` / `THROTTLE_PERIOD` | `6` / `10` | Max updates per user per window |
| `IMAGES_PER_PAGE` | `5` | Default images per gallery page (album mode) |
| `ITEMS_PER_PAGE` | `6` | Posts per listing page |
| `SEARCH_SELECT_TARGET` | `gallery` | What selecting a `/search` result opens: `gallery` or `detail` |
| `SEARCH_THUMBNAILS` | `true` | Attach the result's own thumbnail to the single-result `/search` card |
| `LISTING_CACHE_TTL` | `300` | Seconds, in-memory listing cache |
| `POST_CACHE_TTL` | `86400` | Seconds, DB `post_cache` freshness |
| `CATEGORY_CACHE_TTL` | `21600` | Seconds, taxonomy refresh |
| `SESSION_TTL` | `1800` | Seconds a browse/gallery `sid` stays valid |
| `DEFAULT_DELIVERY_MODE` | `album` | `album` (media group) or `single` (edit-in-place) |
| `IMAGE_FALLBACK_UPLOAD` | `true` | Re-send as bytes if Telegram refuses the URL |
| `AGE_GATE` | `true` | Require 18+ confirmation on first `/start` |
| `AUTO_DELETE_ENABLED` | `true` | Delete every media message the bot sends, on a timer |
| `AUTO_DELETE_TTL_MINUTES` | `30` | Minutes a media message lives before the sweeper removes it |
| `AUTO_DELETE_SCOPE` | `media` | `media` = photos/albums/cards only; `all` also covers text messages |
| `AUTO_DELETE_SWEEP_INTERVAL` | `60` | Seconds between sweeper passes (minimum 15) |
| `BROADCAST_RATE` | `20` | Messages/second during broadcast fan-out |
| `MAINTENANCE` | `false` | Initial maintenance mode state |
| `RUN_MODE` | `polling` | `polling` (default) or `webhook` |
| `API_HOST` / `API_PORT` | `0.0.0.0` / `8080` | FastAPI/uvicorn bind address (both modes) |
| `WEBHOOK_BASE_URL` | — | Public HTTPS base for webhook mode, e.g. `https://bot.example.com` |
| `WEBHOOK_PATH` | `/webhook` | Route FastAPI serves for Telegram updates |
| `WEBHOOK_SECRET` | — | Telegram `secret_token`; validated against the `X-Telegram-Bot-Api-Secret-Token` header |
| `WEBHOOK_DROP_PENDING` | `true` | Passed to `set_webhook` on startup |
| `WEBHOOK_DELETE_ON_SHUTDOWN` | `false` | Call `delete_webhook` when the app stops |
| `SET_COMMANDS_ON_STARTUP` | `true` | Auto-register the command menus on every boot |
| `COMMAND_SCOPE_ADMINS` | `true` | Also register the admin command set per-admin-chat |
| `LOG_LEVEL` | `INFO` | Root logger level |
| `LOG_DIR` | `logs` | Rotating file directory |

`.env` shipped in the zip carries safe placeholders; `.env.example` documents every key.
`ADMIN_IDS` is only used to **bootstrap**: on first run those IDs are inserted into `admins`
with role `owner`. Roles are then managed in-DB via `/addadmin`.

━━━━━━━━━━━━━━━━━━━━

✦ 𝗔𝘂𝘁𝗼 𝗖𝗼𝗺𝗺𝗮𝗻𝗱 𝗥𝗲𝗴𝗶𝘀𝘁𝗿𝗮𝘁𝗶𝗼𝗻

The menus BotFather normally sets by hand via `/setcommands` are registered
**programmatically on every boot** — no manual BotFather step, and the menu can never drift
away from the code.

Mechanism (`bot/commands.py`):
▸ `BotCommandScopeDefault()` · the user menu shown to everyone
▸ `BotCommandScopeChat(chat_id=<admin id>)` · per-admin-chat menu that adds the admin set,
  applied to every row in `admins`
▸ `set_my_commands(...)` on startup + `set_chat_menu_button(menu_button=MenuButtonCommands())`
▸ `delete_my_commands(scope=...)` for each managed scope, so renamed or removed commands
  never linger in clients
▸ Idempotent and non-fatal: a failure is logged as a warning and never blocks startup
▸ Definitions are validated at import time against Telegram's rules (1–32 chars, `[a-z0-9_]`,
  no leading slash, description ≤ 256 chars), so a typo fails loudly in tests, not silently
  in production
▸ `/help` is rendered from the **same table** that feeds `set_my_commands` — one source of truth

Registered user commands (exactly as the client menu renders them):

| Command | Description |
| --- | --- |
| `start` | Start the bot |
| `menu` | Main menu |
| `help` | Command list |
| `latest` | Newest posts |
| `popular` | Trending posts |
| `search` | Search posts |
| `categories` | Browse categories |
| `category` | Open a category |
| `random` | Random post |
| `favorites` | Saved posts |
| `history` | Recently viewed |
| `profile` | Your profile |
| `settings` | Preferences |
| `stats` | Your usage stats |
| `about` | Bot information |
| `ping` | Check latency |
| `cancel` | Cancel current input |

Registered admin commands (added on top, per admin chat): `admin`, `astats`, `users`,
`find`, `user`, `note`, `notes`, `block`, `unblock`, `blocked`, `broadcast`, `export`,
`logs`, `health`, `reload`, `maintenance`, `admins`, `addadmin`, `deladmin`.

Notes:
▸ `/addadmin` and `/deladmin` re-run registration for the affected chat immediately, so a
  freshly promoted admin sees the admin menu without a restart.
▸ Group scopes are left empty on purpose — this is a private-chat bot.

✦ 𝗗𝗮𝘁𝗮 𝗠𝗼𝗱𝗲𝗹 (SQLite, SQLAlchemy 2.0 typed ORM)

All tables use `Mapped[...]` / `mapped_column`, `DateTime(timezone=True)`, and explicit indexes.

**`users`** — one row per Telegram user that ever touched the bot

| Column | Type | Notes |
| --- | --- | --- |
| `id` | BigInteger PK | Telegram user ID (no autoincrement) |
| `username`, `first_name`, `last_name` | String | refreshed on every update |
| `language_code`, `is_premium`, `is_bot` | String/Bool | Telegram profile snapshot |
| `is_active` | Bool, idx | `false` = blocked |
| `block_reason`, `blocked_at`, `blocked_by` | String/DateTime/BigInt | denormalised current block state |
| `banned_until` | DateTime NULL | temp ban; auto-lifted by scheduled sweep |
| `age_verified`, `age_verified_at` | Bool/DateTime | 18+ gate acknowledgement |
| `request_count` | Int | total commands handled, incremented in middleware |
| `created_at`, `updated_at`, `last_seen_at` | DateTime, idx | lifecycle timestamps |

Indexes: `username`, `is_active`, `created_at`, `last_seen_at`, `banned_until`.

**`admins`** — role grants, kept separate from users

`user_id` PK FK→`users.id` · `role` `owner|admin|moderator` · `granted_by` · `granted_at`

Role model:
▸ `owner` · everything, including adding/removing admins and maintenance mode
▸ `admin` · users, blocking, broadcast, export, audit
▸ `moderator` · read-only inspection, temporary blocks, notes

**`blocks`** — full moderation history (current state also mirrored on `users`)

`id` PK · `user_id` FK idx · `admin_id` · `reason` · `created_at` · `expires_at` NULL ·
`lifted_at` NULL · `lifted_by` NULL · `is_active` Bool idx

**`favorites`** — saved posts

`id` PK · `user_id` FK idx · `post_url` · `post_title` · `thumbnail` · `created_at`
Constraint: `UNIQUE(user_id, post_url)`; index on `(user_id, created_at DESC)`.

**`user_notes`** — free-text admin notes attached to a user

`id` PK · `user_id` FK idx · `admin_id` · `text` · `created_at`
Notes are append-only; `/notes <id>` lists them and `/note <id> <text>` adds one.

**`history`** — recently viewed posts (bounded, upsert-on-conflict)

`id` PK · `user_id` FK idx · `post_url` · `post_title` · `thumbnail` · `viewed_at`
Constraint: `UNIQUE(user_id, post_url)`; view → upsert, keep last 100 per user.

**`user_settings`** — per-user preferences

`user_id` PK FK · `images_per_page` (3–10, default 5) · `delivery_mode` `album|single` ·
`spoiler_media` Bool · `blur_thumbnails` Bool · `show_thumbnails` Bool ·
`items_per_page` (default 6) · `notifications` Bool · `language` · `updated_at`

**`post_cache`** — avoids re-fetching a post for every gallery page

`url` String(512) PK · `title` · `description` · `genres` JSON · `upload_date` ·
`images` JSON · `image_count` Int · `fetched_at` idx · `hits` Int

**`category_cache`** — warm taxonomy on cold start

`path` String(255) PK · `name` · `position` Int · `fetched_at`

**`audit_logs`** — every privileged action

`id` PK · `admin_id` idx · `action` String(48) · `target_type` · `target_id` ·
`details` JSON · `created_at` idx

**`broadcasts`** — fan-out bookkeeping

`id` PK · `admin_id` · `kind` `text|photo` · `content` · `parse_mode` ·
`status` `draft|running|done|cancelled|failed` · `total` · `sent_ok` · `sent_fail` ·
`created_at` · `started_at` · `finished_at`

**`daily_stats`** — cheap counters for growth stats

`day` Date PK · `new_users` · `active_users` · `requests` · `blocks` · `broadcasts`

**`scheduled_deletions`** — the auto-delete queue (30-minute media TTL)

`id` PK · `chat_id` idx · `message_id` idx · `user_id` NULL · `kind` `media|card|preview` ·
`delete_at` DateTime idx · `created_at` · `attempts` Int

A row is written the moment a media message is sent and removed when the sweeper deletes
the message. Because it lives in SQLite, pending deletions survive a restart. Failures
retry up to 5 times before the row is retired.

**`meta`** — key/value store

`key` PK · `value` · holds `schema_version`, `categories_synced_at`, `maintenance` flag.

Schema is created automatically on boot (`Base.metadata.create_all` via `init_db()`);
`meta.schema_version` lets a future release run additive migrations without Alembic.

✦ 𝗦𝗤𝗟𝗶𝘁𝗲 𝗖𝗼𝗻𝗰𝘂𝗿𝗿𝗲𝗻𝗰𝘆

SQLite allows a single writer, so the engine is tuned to keep write transactions short and
to wait rather than fail:

▸ `journal_mode=WAL` · readers never block the writer, and the writer never blocks readers
▸ `busy_timeout=15000` plus the driver-level `timeout=15` · a blocked writer waits for the
  lock instead of failing on the first attempt
▸ `synchronous=NORMAL` · the WAL-appropriate durability setting, and a shorter write lock
▸ `foreign_keys=ON` · PRAGMAs are per connection, so they are re-applied on every checkout
▸ One session per update, but the user tracking writes **commit before the handler runs**,
  so no write lock is held across a Telegram call. A slow album send used to keep the lock
  for seconds, which made the auto-delete scheduler and every other writer fail with
  `database is locked`
▸ `bot/database/base.is_lock_error()` classifies lock errors, and `DeletionService` retries
  its scheduling write up to 4 times with backoff. That write is idempotent — queuing a
  message that is already queued is a no-op — so replaying it after contention is safe

Rule for future work: never `await` a Telegram call inside an open write transaction, and
only retry a write whose body is idempotent.
━━━━━━━━━━━━━━━━━━━━

✦ 𝗖𝗼𝗺𝗺𝗮𝗻𝗱 𝗥𝗲𝗳𝗲𝗿𝗲𝗻𝗰𝗲 — 𝗨𝘀𝗲𝗿

| Command | Args | What it does |
| --- | --- | --- |
| `/start` | — | Register user, age gate (first run), welcome card + main menu |
| `/menu` | — | Re-open the main inline menu |
| `/help` | — | Command reference (user set; admin set appended for admins) |
| `/latest` | `[page]` | Newest posts — `ctele.get_latest(page)` |
| `/popular` | `[day\|week\|month\|all] [page]` | Popular posts — `ctele.get_popular(page, time_range=...)` |
| `/categories` | `[page]` | Browse live taxonomy — `ctele.get_categories()` |
| `/category` | `<name or path> [page]` | Category/tag archive — `ctele.browse_category(...)` |
| `/search` | `<text or url>` | One result per card (`❖ Result 2 / 6`) with `‹` / `▸ Open` / `Next ›` on top and a number row below; the result's thumbnail rides on the card, and a number jumps through the in-chat prompt |
| `/post` | `<url>` | Open a post by URL (detail card) |
| `/last` | — | Re-open the most recent post you viewed |
| `/gallery` | `[page]` | Paginated image gallery for the current post |
| `/random` | — | Random post picked from the latest listing |
| `/favorites` | `[page]` | Saved posts, openable and removable |
| `/history` | `[page]` | Recently viewed; `/history clear` wipes it |
| `/profile` | — | Your profile card: ID, join date, requests, saves, status |
| `/settings` | — | Preferences: images per page, album/single mode, spoiler, thumbnails |
| `/stats` | — | Your personal usage stats |
| `/about` | — | Bot version, source, build info |
| `/ping` | — | Round-trip latency + source reachability |
| `/cancel` | — | Leave any input flow (e.g. search prompt) |

Notes:
▸ `[brackets]` = optional, `|` = alternatives, `<>` = required.
▸ `/latest /popular /category /categories` render the same paginated listing UI: numbered
  post buttons, `‹ Prev`, `Page N`, `Next ›`, and a footer row. `/search` uses the
  single-result card instead (see the flow below).
▸ Any listing page caches its results under a short session id, so pressing a post
  button costs zero extra source requests for the listing itself.

✦ 𝗖𝗼𝗺𝗺𝗮𝗻𝗱 𝗥𝗲𝗳𝗲𝗿𝗲𝗻𝗰𝗲 — 𝗔𝗱𝗺𝗶𝗻

| Command | Role | What it does |
| --- | --- | --- |
| `/admin` | mod+ | Admin hub: live counters + jump-off buttons |
| `/astats` | mod+ | Global stats: users, active 24h/7d, blocked, requests, top categories |
| `/users` | mod+ | Paginated user list (newest first), 10/page, jump + search buttons |
| `/find` | mod+ | Search users by ID, `@username`, or name fragment |
| `/user` | mod+ | Full user card: profile, activity, settings, blocks, notes |
| `/note` | mod+ | Attach an internal note to a user |
| `/notes` | mod+ | List notes for a user |
| `/block` | admin+ | Block a user: `/block <id> [reason]` (optional `--days N` for temp) |
| `/unblock` | admin+ | Lift a block |
| `/blocked` | mod+ | Active block list, paginated, with unblock buttons |
| `/broadcast` | admin+ | FSM: send text/photo → preview → confirm → progress → cancel |
| `/export` | admin+ | Export `users` (or `favorites`/`history`) as CSV, delivered as a file |
| `/logs` | admin+ | Audit log, paginated, filtered by action/admin |
| `/health` | admin+ | SDK connectivity, latency, cache hit rates, DB size, uptime |
| `/reload` | owner | Clear listing/post/category caches and re-sync taxonomy |
| `/maintenance` | owner | `on`/`off` — when on, only admins can use the bot |
| `/admins` | owner | List admins and roles |
| `/addadmin` | owner | Grant `admin`/`moderator` to a user id |
| `/deladmin` | owner | Revoke a role (guards against removing the last owner) |

Admins also get every user command, plus `/help` renders both tables.

✦ 𝗦𝘂𝗴𝗴𝗲𝘀𝘁𝗲𝗱 𝗔𝗱𝗱𝗶𝘁𝗶𝗼𝗻𝘀 (recommended, cheap to build)

▸ `/surprise` · alias of `/random` with a category filter (`/random <category>`)
▸ `/top` · `/popular` pinned to `range=month` with a cleaner card
▸ `/open` · `/post` accepting a bare numeric index from the last listing
▸ `/share` · returns a copy-paste link + `t.me/share/url` deep link for a post
▸ `/sync` · admin: force-refresh `category_cache` and report added/removed categories
▸ `/whois` · admin: reverse lookup — given a post, who saved/viewed it
▸ `/flag` · user reporting: hand a bad link to admins via `LOG_CHANNEL_ID`

These are in scope as “nice-to-have” and can ship in the same build if you approve them.
━━━━━━━━━━━━━━━━━━━━

✦ 𝗨𝗫 𝗙𝗹𝗼𝘄𝘀

**First contact — `/start`**
1. Upsert user row (id, username, names, language, `is_premium`).
2. If `age_verified = false` and `AGE_GATE` is on → show the 18+ notice with `I am 18+` /
   `Exit`. No source content is sent before confirmation.
3. On confirm → welcome card + main menu (reply keyboard + inline menu).
4. If `is_active = false` → show the blocked notice with reason and stop.

**Browse — `/latest`, `/popular`, `/categories`, `/category`, `/search`**
1. Handler asks `ctele_service` for a page (cache-first, then SDK, with retries).
2. A `sid` is minted and the page's `PostSummary[]` is stored in the session store.
3. Message renders: header, section line, numbered post buttons (title truncated to fit),
   nav row, footer row.
4. `Prev`/`Next` ask the service for the neighbouring page and re-render **in place**
   (`edit_text`), reusing or replacing only the session entry — never spamming the chat.
5. Source errors map to friendly cards: `RequestError` → “source unreachable, retry”,
   `ParseError` → “source layout changed” + silent alert to `LOG_CHANNEL_ID`.

**Chained navigation — edit in place, never delete-and-resend**
A button that leads to another screen rewrites the message the user just tapped. It is only
replaced when Telegram makes the edit impossible:
1. text → text · `edit_message_text` — listings, categories, menus, admin screens
2. photo → photo · `edit_message_media` — search results, `single`-mode galleries
3. photo → text · `edit_message_caption`, so the image the user is looking at stays put and
   only the words change (gallery → `▸ Details`)
4. text → photo, or anything → album · the one thing the API forbids; the old message is
   deleted *after* the new one lands, so the chat never blinks empty
5. `present_card()` and `show_screen()` in `bot/handlers/common.py` are the only two places
   that decide this, so every screen behaves the same way. `callback_data` that only
   carried “what to delete” now carries “what to edit”

**Search — `/search <query>`**
1. Called with no query, the bot asks for one and waits (FSM, cancellable with `/cancel`);
   a pasted post or category URL is accepted and resolved by the source SDK.
2. The page is fetched once and its `PostSummary[]` is kept in the session, so stepping
   through results costs no extra source request until a page boundary is crossed.
3. **One result is shown at a time** — a `❖ Result 2 / 6` card with the title, the query,
   the window (`1-6, more available`) and, when `SEARCH_THUMBNAILS=true`, that result's own
   thumbnail as `photo=<url>`. Two results can never be confused with each other.
4. `Next ›` / `‹` step one result at a time and rewrite the card with `edit_message_media`;
   crossing a page boundary loads the next page and continues from its first (or last) item.
5. The number row (`1`…`6`) is a **shortcut into the in-chat flow**: tapping it asks
   `⟡ Jump to Result · Send the number of the result you want to see` in the chat. The reply
   and the prompt are then deleted and the card is switched to that result, so the tap never
   has to guess which result was meant.
6. Stepping past the first or last result is refused with a toast, not an error card.
7. `▸ Open` opens that post's gallery (`SEARCH_SELECT_TARGET=gallery`, default; set it to
   `detail` for the post card instead). The gallery carries a `▸ Details` button back.
8. An empty result set answers with a `◇ No results` card that echoes the query and offers
   `▸ /latest` and `⟡ New search`.
9. Listing pages (`/latest`, `/popular`, `/category`) always open the detail card first.

**Post detail — press a listing button or `/post <url>`**
1. `ctele_service.get_post(url)` (DB `post_cache` first; fresh within `POST_CACHE_TTL`).
2. Card: title, genres, upload date, image count, short description/excerpt.
3. Thumbnail sent as `photo=<thumbnail_url>` when `show_thumbnails` is on.
4. Buttons: `▸ Open Gallery`, `◇ Save`, `⟡ Source link`, `‹ Back to list`.

**Gallery — `▸ Open Gallery` or `/gallery [page]`**
1. Resolve the post's `images[]` (cached), slice into pages of `images_per_page`.
2. Send **only URLs** — Telegram fetches the media itself; nothing is downloaded.
3. Inline nav: `‹ Prev`, `◇ 2 / 9`, `Next ›`; plus `♡ Save`, `⟡ Open original`, `▸ Details`.
4. `Prev`/`Next` delete the previous page's messages and send the new page, keeping the
   chat clean and the album order predictable.
5. Requests for pages beyond the range are rejected with a toast alert, not a crash.

**Admin — users & moderation**
1. `/admin` → counters (total, active 24h, blocked, new today) + buttons.
2. `/users` → paginated table of cards (`#id · @username · status · joined`), each card a
   button that opens `/user <id>`.
3. `/user <id>` → profile, activity, settings, block history, notes, and action buttons:
   `◆ Block`, `◇ Unblock`, `▸ Note`, `⟡ Export row`.
4. `/block <id> reason` → confirm step → writes `blocks` row, flips `users.is_blocked`,
   appends an `audit_logs` row, and mirrors to `LOG_CHANNEL_ID`.
5. A blocked user's updates are dropped at middleware level with a single polite notice
   (rate-limited so it can't be used to spam).

**Broadcast — `/broadcast`**
`Send the message to broadcast` → admin sends text or photo+caption → preview rendered
back → `Confirm` / `Edit` / `Cancel` → rate-limited fan-out (`BROADCAST_RATE`) with a live
progress edit (`✔ 120 · ✘ 3 · 412/2000`) → final summary written to `broadcasts` and the
audit log. `/cancel` or the `Cancel` button aborts mid-flight and records the partial run.

✦ 𝗠𝗲𝘀𝘀𝗮𝗴𝗲 𝗗𝗲𝘀𝗶𝗴𝗻 𝗦𝘆𝘀𝘁𝗲𝗺 (per `agents.md`)

Every string lives in `bot/texts/ui.py` with the approved symbols and **no emoji**.
`parse_mode = HTML` so we can use `<a href>` and `<code>`; all dynamic values are escaped.

Default vocabulary:
▸ Header `❖` · Section `✦` · List `▸` · Success `✓` · Important `◆` · Pending `◇` ·
  Inactive `○` · Separator `━━━━━━━━━━━━━━━━━━━━` · Key/value `·`
▸ Mathematical bold sans (`𝗛𝗲𝗮𝗱𝗲𝗿`) for headers and section names only — nowhere else.

`/start` welcome

```
❖ 𝗪𝗲𝗹𝗰𝗼𝗺𝗲

━━━━━━━━━━━━━━━━━━━━

▸ User · John
▸ ID · <code>123456789</code>
▸ Status · ◆ Active

✦ 𝗚𝗲𝘁 𝗦𝘁𝗮𝗿𝘁𝗲𝗱

▸ /latest · newest posts
▸ /popular · trending now
▸ /search · find anything
▸ /help · all commands

━━━━━━━━━━━━━━━━━━━━
```

Listing page

```
✦ 𝗟𝗮𝘁𝗲𝘀𝘁 𝗣𝗼𝘀𝘁𝘀

━━━━━━━━━━━━━━━━━━━━

▸ Page · 2 / 40
▸ Results · 6 posts

▼ Select a post below
```

Post detail

```
❖ 𝗣𝗼𝘀𝘁

━━━━━━━━━━━━━━━━━━━━

✦ 𝗜𝗻𝗳𝗼

▸ Title · <title>
▸ Date · 2026-08-30
▸ Images · 42

✦ 𝗚𝗲𝗻𝗿𝗲𝘀

▸ Cosplay · Nude · Ero
```

Gallery page

```
❖ 𝗚𝗮𝗹𝗹𝗲𝗿𝘆

━━━━━━━━━━━━━━━━━━━━

▸ Post · <title>
▸ Images · 6–10 of 42
▸ Page · 2 / 9
```

Admin user card

```
❖ 𝗨𝘀𝗲𝗿 · <code>123456789</code>

━━━━━━━━━━━━━━━━━━━━

✦ 𝗣𝗿𝗼𝗳𝗶𝗹𝗲

▸ Name · John Doe
▸ Username · @johndoe
▸ Language · en

✦ 𝗔𝗰𝘁𝗶𝘃𝗶𝘁𝘆

▸ Joined · 2026-07-02
▸ Last seen · 3 min ago
▸ Requests · 812
▸ Favorites · 24

✦ 𝗦𝘁𝗮𝘁𝘂𝘀

✓ Active
◇ No active block

━━━━━━━━━━━━━━━━━━━━
```

Error / alert

```
【 𝗜𝗠𝗣𝗢𝗥𝗧𝗔𝗡𝗧 】

◆ Source Unavailable
━━━━━━━━━━━━━━━━━━━━

The requested operation could not be completed.

▸ Reason · Request timed out
▸ Retry · /latest
```

Rules enforced in review: one header symbol, one list symbol, one separator, one
key/value separator per message; no decoration on every line; correct information never
altered by formatting.
━━━━━━━━━━━━━━━━━━━━

✦ 𝗨𝗜 𝗠𝗼𝗰𝗸𝘂𝗽𝘀

Rough rendering of every screen the bot can send. Structure, symbol usage and button order
match the shipped strings in `bot/texts/ui.py`.

How to read these:
▸ One fenced block per screen · the message text first, then its keyboard
▸ `media →` · an attached photo or album (always a public URL; Telegram fetches it)
▸ `buttons →` · one inline keyboard row; consecutive lines are consecutive rows
▸ `reply →` · the persistent reply keyboard, noted only where it changes
▸ `<…>` · a dynamic value · `…` · truncation
▸ `(toast)` · a transient popup alert that leaves the message unchanged

✦ 𝗢𝗻𝗯𝗼𝗮𝗿𝗱𝗶𝗻𝗴

**Age gate** — shown once, before any source content

```
【 𝗔𝗚𝗘 𝗩𝗘𝗥𝗜𝗙𝗜𝗖𝗔𝗧𝗜𝗢𝗡 】

This bot shares content intended for adults only.

▸ Requirement · you must be 18 or older
▸ Reminder · you can stop using the bot at any time

━━━━━━━━━━━━━━━━━━━━
```
```
buttons → [ I am 18+ ] [ Exit ]
```

**Welcome** — `/start`

```
❖ 𝗪𝗲𝗹𝗰𝗼𝗺𝗲

━━━━━━━━━━━━━━━━━━━━

▸ User · John
▸ ID · 123456789
▸ Status · ◆ Active

✦ 𝗚𝗲𝘁 𝗦𝘁𝗮𝗿𝘁𝗲𝗱

▸ Latest · newest posts
▸ Popular · trending now
▸ Search · find anything
▸ Help · all commands

━━━━━━━━━━━━━━━━━━━━
```
```
buttons → [ ❖ Latest ] [ ✦ Popular ]
buttons → [ ⟡ Search ] [ ◇ Favorites ]
reply   → [ Latest ] [ Popular ] [ Search ] [ Help ]
```

**Exit / declined** — `Exit` on the age gate

```
◇ 𝗘𝘅𝗶𝘁𝗲𝗱

You can return any time with /start.
```
```
buttons → [ ⟡ Restart ]
```

**Main menu** — `/menu`

```
❖ 𝗠𝗮𝗶𝗻 𝗠𝗲𝗻𝘂

━━━━━━━━━━━━━━━━━━━━

▸ User · John
▸ Saves · 24
▸ Status · ◆ Active
```
```
buttons → [ ❖ Latest ] [ ✦ Popular ]
buttons → [ ⟡ Search ] [ ◇ Categories ]
buttons → [ ◇ Favorites ] [ ◇ History ]
buttons → [ ◎ Profile ] [ ⟡ Settings ]
```

**Help · user** — `/help`

```
❖ 𝗛𝗲𝗹𝗽

━━━━━━━━━━━━━━━━━━━━

✦ 𝗕𝗿𝗼𝘄𝘀𝗲

▸ /latest · newest posts
▸ /popular · trending posts
▸ /categories · browse categories
▸ /category · open a category
▸ /search · search posts
▸ /random · random post

✦ 𝗬𝗼𝘂𝗿 𝗔𝗰𝗰𝗼𝘂𝗻𝘁

▸ /favorites · saved posts
▸ /history · recently viewed
▸ /profile · your profile
▸ /settings · preferences
▸ /stats · usage stats

✦ 𝗢𝘁𝗵𝗲𝗿

▸ /about · bot information
▸ /ping · check latency
▸ /cancel · cancel input

━━━━━━━━━━━━━━━━━━━━
```
```
buttons → [ ❖ Latest ] [ ⟡ Search ] [ ◇ Favorites ]
```

**Help · admin** — `/help` for an admin (user table above, plus this block)

```
✦ 𝗔𝗱𝗺𝗶𝗻

▸ /admin · control panel
▸ /astats · global statistics
▸ /users · user list
▸ /find · search users
▸ /user · user detail
▸ /block · block a user
▸ /unblock · unblock a user
▸ /blocked · active blocks
▸ /broadcast · message everyone
▸ /logs · audit log
▸ /health · system health
```
```
buttons → [ ◆ Admin Panel ] [ ◇ Audit Log ]
```

━━━━━━━━━━━━━━━━━━━━

✦ 𝗕𝗿𝗼𝘄𝘀𝗶𝗻𝗴

**Latest** — `/latest`

```
✦ 𝗟𝗮𝘁𝗲𝘀𝘁 𝗣𝗼𝘀𝘁𝘀

━━━━━━━━━━━━━━━━━━━━

▸ Page · 2 / 40
▸ Results · 6 posts

Press a number to open a post.
```
```
buttons → [ 1 · Nova ] [ 2 · Aurora ]
buttons → [ 3 · Eclipse ] [ 4 · Mirage ]
buttons → [ 5 · Ember ] [ 6 · Zenith ]
buttons → [ « Prev ] [ Page 2 / 40 ] [ Next » ]
buttons → [ ⟡ Refresh ] [ ❖ Menu ]
```

**Popular** — `/popular week`

```
✦ 𝗣𝗼𝗽𝘂𝗹𝗮𝗿 𝗣𝗼𝘀𝘁𝘀

━━━━━━━━━━━━━━━━━━━━

▸ Range · last 7 days
▸ Page · 1 / 12
▸ Results · 6 posts
```
```
buttons → [ 1 · … ] [ 2 · … ]
buttons → [ 3 · … ] [ 4 · … ]
buttons → [ 5 · … ] [ 6 · … ]
buttons → [ ◇ Day ] [ ◆ Week ] [ ◇ Month ]
buttons → [ « Prev ] [ Page 1 / 12 ] [ Next » ]
```
`◆` marks the active range; the three range buttons re-render the list in place.

**Search prompt** — `/search` with no arguments

```
⟡ 𝗦𝗲𝗮𝗿𝗰𝗵

━━━━━━━━━━━━━━━━━━━━

Send a keyword to search for.

▸ Tip · a post or category link works too
▸ Cancel · /cancel
```

**Search result card** — one result per screen

Each screen carries exactly one result, so two results are never confused. The top row is
navigation plus the open action; the number row underneath is a shortcut into the in-chat
flow. The result's own thumbnail rides on the card when `SEARCH_THUMBNAILS=true`, so a
result can be judged without opening its gallery.

**With a thumbnail** (`SEARCH_THUMBNAILS=true`)

```
media  → photo=<result thumbnail url> (URL-only, Telegram fetches it)
```
```
❖ 𝗥𝗲𝘀𝘂𝗹𝘁 1 / 6

━━━━━━━━━━━━━━━━━━━━

Nova Nights

▸ Query · nova
▸ Window · 1-6, more available

▸ Tap a number below, or just send the number in chat

◆ Auto-delete · this is removed in 30 min
```
```
buttons → [ ‹ ] [ ▸ Open ] [ Next › ]
buttons → [ 1 ] [ 2 ] [ 3 ] [ 4 ] [ 5 ]
buttons → [ 6 ]
buttons → [ ⟡ New Search ] [ ❖ Menu ]
```
`‹` is inert on the first result and `Next ›` on the last; both are refused with a toast
rather than an error card. `▸ Open` sends page 1 of that post's gallery.

**The number row is a shortcut into the in-chat flow** — tapping any number opens a prompt
instead of guessing which result was meant:

```
⟡ 𝗝𝘂𝗺𝗽 𝘁𝗼 𝗥𝗲𝘀𝘂𝗹𝘁

━━━━━━━━━━━━━━━━━━━━

Send the number of the result you want to see.

▸ Range · 1 to 6
▸ Cancel · /cancel

━━━━━━━━━━━━━━━━━━━━
```
```
buttons → [ Cancel ]
```
Sending `5` deletes the reply and the prompt, then edits the card to result 5. A number
outside the range answers with `◇ Unknown Result · ▸ You sent · 99 · ▸ Range · 1 to 6`.

**Without a thumbnail** (`SEARCH_THUMBNAILS=false`, or a CDN that refuses the URL)

The same card is sent as plain text and the `◆ Auto-delete` line is dropped, because
nothing image-bearing went out.

Every step — `‹`, `Next ›`, the jump and `▸ Open` — rewrites the same message, so walking a
whole search leaves one card in the chat, not a column of them.

**Search · no results**

```
◇ 𝗡𝗼 𝗥𝗲𝘀𝘂𝗹𝘁𝘀

━━━━━━━━━━━━━━━━━━━━

▸ Query · <query>
▸ Tried · text search

▸ Suggestion · shorten the keyword or check the spelling
```
```
buttons → [ ⟡ New Search ] [ ❖ Latest ]
```

**Categories** — `/categories`

```
✦ 𝗖𝗮𝘁𝗲𝗴𝗼𝗿𝗶𝗲𝘀

━━━━━━━━━━━━━━━━━━━━

▸ Source · live taxonomy
▸ Page · 1 / 3

Select a category to browse.
```
```
buttons → [ · Cosplay ] [ · Cosplay Nude ]
buttons → [ · Cosplay Ero ] [ · Gravure ]
buttons → [ « Prev ] [ Page 1 / 3 ] [ Next » ]
buttons → [ ⟡ Refresh ] [ ❖ Menu ]
```

**Category archive** — `/category cosplay`

```
✦ 𝗖𝗮𝘁𝗲𝗴𝗼𝗿𝘆

━━━━━━━━━━━━━━━━━━━━

▸ Name · Cosplay
▸ Path · category/cosplay
▸ Page · 1 / 24
```
```
buttons → [ 1 · … ] [ 2 · … ]
buttons → [ 3 · … ] [ 4 · … ]
buttons → [ 5 · … ] [ 6 · … ]
buttons → [ « Prev ] [ Page 1 / 24 ] [ Next » ]
buttons → [ « Categories ] [ ❖ Menu ]
```

**Random pick** — `/random`

Sends the post card below, prefixed with a one-line banner:

```
✦ 𝗥𝗮𝗻𝗱𝗼𝗺 𝗣𝗶𝗰𝗸
```

**Transient alerts** (toasts, message unchanged)

```
⟡ Loading…
```
```
◇ That page does not exist
```

━━━━━━━━━━━━━━━━━━━━

✦ 𝗣𝗼𝘀𝘁 𝗮𝗻𝗱 𝗚𝗮𝗹𝗹𝗲𝗿𝘆

**Post card** — from a listing button or `/post <url>`

```
media  → thumbnail photo (only when thumbnails are enabled)
```
```
❖ 𝗣𝗼𝘀𝘁

━━━━━━━━━━━━━━━━━━━━

✦ 𝗜𝗻𝗳𝗼

▸ Title · <title>
▸ Date · 2026-08-30
▸ Images · 42

✦ 𝗚𝗲𝗻𝗿𝗲𝘀

▸ Cosplay · Nude · Ero

✦ 𝗣𝗿𝗲𝘃𝗶𝗲𝘄

▸ <first ~200 characters of the description>

━━━━━━━━━━━━━━━━━━━━
```
```
buttons → [ ▸ Open Gallery ]
buttons → [ ◇ Save ] [ ⟡ Open Original ]
buttons → [ « Back ]
```

**Auto-delete notice** — carried by every screen that shows media

```
◆ Auto-delete · this is removed in 30 min
```
The label is rendered from `AUTO_DELETE_TTL_MINUTES`, so the wording and the behaviour can
never drift apart. It appears on the post card, in both gallery modes, under the `/search`
previews and in `/about`.

**Gallery · first page (album mode, default)**

```
media  → album of 5 photos, sent as URLs only
         caption attached to the first image ↓
❖ 𝗚𝗮𝗹𝗹𝗲𝗿𝘆

━━━━━━━━━━━━━━━━━━━━

▸ Post · <title>
▸ Images · 1–5 of 42
▸ Page · 1 / 9

◆ Auto-delete · this is removed in 30 min
```
```
buttons → [ ♡ Save ] [ ▸ Details ] [ ⟡ Original ]
buttons → [ ‹ Prev ] [ 1 / 9 ] [ Next › ]
```
`‹ Prev` is inert on page 1. `Next ›` deletes this album and sends the next page, so only
one gallery is ever on screen.

**Gallery · middle page (album mode)**

```
media  → album of 5 photos
caption →
❖ 𝗚𝗮𝗹𝗹𝗲𝗿𝘆

━━━━━━━━━━━━━━━━━━━━

▸ Post · <title>
▸ Images · 6–10 of 42
▸ Page · 2 / 9

◆ Auto-delete · this is removed in 30 min
```
```
buttons → [ ♡ Save ] [ ▸ Details ] [ ⟡ Original ]
buttons → [ ‹ Prev ] [ 2 / 9 ] [ Next › ]
```

**Gallery · single mode** (`delivery_mode = single` in `/settings`)

```
media  → one photo per screen
caption →
❖ 𝗚𝗮𝗹𝗹𝗲𝗿𝘆

━━━━━━━━━━━━━━━━━━━━

▸ Post · <title>
▸ Image · 7 of 42

◆ Auto-delete · this is removed in 30 min
```
```
buttons → [ ‹ Prev ] [ 7 / 42 ] [ Next › ]
buttons → [ ♡ Save ] [ ▸ Details ] [ ⟡ Original ]
```
Paged with `edit_message_media`, so the entire gallery lives in a single message.

**Gallery · partial failure**

```
❖ 𝗚𝗮𝗹𝗹𝗲𝗿𝘆

━━━━━━━━━━━━━━━━━━━━

▸ Post · <title>
▸ Images · 11–15 of 42
▸ Page · 3 / 9

◆ Note · 1 image could not be loaded

◆ Auto-delete · this is removed in 30 min
```
```
buttons → [ ⟡ Retry Page ] [ ▸ Details ]
buttons → [ ‹ Prev ] [ 3 / 9 ] [ Next › ]
```

**Gallery · expired session**

```
◇ 𝗦𝗲𝘀𝘀𝗶𝗼𝗻 𝗘𝘅𝗽𝗶𝗿𝗲𝗱

━━━━━━━━━━━━━━━━━━━━

This gallery is no longer open.

▸ Fix · run /gallery again, or reopen the post
```
```
buttons → [ ⟡ Latest ] [ ❖ Menu ]
```

✦ 𝗔𝗰𝗰𝗼𝘂𝗻𝘁

**Profile** — `/profile`

```
❖ 𝗣𝗿𝗼𝗳𝗶𝗹𝗲

━━━━━━━━━━━━━━━━━━━━

✦ 𝗜𝗱𝗲𝗻𝘁𝗶𝘁𝘆

▸ Name · John Doe
▸ Username · @johndoe
▸ ID · 123456789

✦ 𝗔𝗰𝘁𝗶𝘃𝗶𝘁𝘆

▸ Joined · 2026-07-02
▸ Last seen · just now
▸ Requests · 812

✦ 𝗟𝗶𝗯𝗿𝗮𝗿𝘆

▸ Favorites · 24
▸ History · 100

✦ 𝗦𝘁𝗮𝘁𝘂𝘀

✓ Active
✓ 18+ verified

━━━━━━━━━━━━━━━━━━━━
```
```
buttons → [ ◇ Favorites ] [ ◇ History ]
buttons → [ ⟡ Settings ] [ ❖ Menu ]
```

**Settings** — `/settings`

```
❖ 𝗦𝗲𝘁𝘁𝗶𝗻𝗴𝘀

━━━━━━━━━━━━━━━━━━━━

✦ 𝗗𝗶𝘀𝗽𝗹𝗮𝘆

▸ Images per page · 5
▸ Posts per page · 6
▸ Thumbnails · ◆ On

✦ 𝗚𝗮𝗹𝗹𝗲𝗿𝘆

▸ Mode · ◆ Album
▸ Spoiler media · ◇ Off

━━━━━━━━━━━━━━━━━━━━
```
```
buttons → [ Images per page · 5 ]
buttons → [ – ] [ 5 ] [ + ]
buttons → [ ◆ Album ] [ ◇ Single ]
buttons → [ ◆ Thumbnails ] [ ◇ Spoiler ]
buttons → [ ⟡ Reset Defaults ] [ ❖ Menu ]
```
Every tap edits this message in place and persists to `user_settings`.

**Stats · user** — `/stats`

```
❖ 𝗬𝗼𝘂𝗿 𝗦𝘁𝗮𝘁𝘀

━━━━━━━━━━━━━━━━━━━━

▸ Requests · 812
▸ Posts viewed · 231
▸ Favorites · 24
▸ Member since · 2026-07-02
▸ Last active · just now
```
```
buttons → [ ❖ Menu ]
```

**Favorites** — `/favorites`

```
❖ 𝗙𝗮𝘃𝗼𝗿𝗶𝘁𝗲𝘀

━━━━━━━━━━━━━━━━━━━━

▸ Saved · 24
▸ Page · 1 / 4

Press a number to open its gallery.
```
```
buttons → [ 1 · Nova Prime ] [ 2 · Ember ]
buttons → [ 3 · Zenith ] [ 4 · Mirage ]
buttons → [ « Prev ] [ Page 1 / 4 ] [ Next » ]
buttons → [ ⟡ Manage ] [ ❖ Menu ]
```
`⟡ Manage` flips the list into removal mode, where each row is prefixed with `◇` and a tap
deletes that entry.

**History** — `/history`

```
❖ 𝗛𝗶𝘀𝘁𝗼𝗿𝘆

━━━━━━━━━━━━━━━━━━━━

▸ Viewed · 100
▸ Page · 1 / 17
```
```
buttons → [ 1 · … ] [ 2 · … ]
buttons → [ 3 · … ] [ 4 · … ]
buttons → [ « Prev ] [ Page 1 / 17 ] [ Next » ]
buttons → [ ◆ Clear History ] [ ❖ Menu ]
```
`◆ Clear History` asks for confirmation before wiping rows.

**Transient alerts** (toasts)

```
✓ Saved
```
```
◇ Removed
```

━━━━━━━━━━━━━━━━━━━━

✦ 𝗔𝗱𝗺𝗶𝗻

**Panel** — `/admin`

```
❖ 𝗔𝗱𝗺𝗶𝗻 𝗣𝗮𝗻𝗲𝗹

━━━━━━━━━━━━━━━━━━━━

✦ 𝗟𝗶𝘃𝗲 𝗡𝘂𝗺𝗯𝗲𝗿𝘀

▸ Users · 1,204
▸ Active 24h · 318
▸ Blocked · 12
▸ New today · 27

✦ 𝗦𝘆𝘀𝘁𝗲𝗺

▸ Mode · ◆ Polling
▸ Source · ✓ Reachable
▸ Cache · 84% hit rate

━━━━━━━━━━━━━━━━━━━━
```
```
buttons → [ ◆ Users ] [ ⟡ Find User ]
buttons → [ ◇ Blocked ] [ ⟡ Broadcast ]
buttons → [ ◇ Audit Log ] [ ⟡ Health ]
buttons → [ ⟡ Export CSV ] [ ❖ Menu ]
```

**Users list** — `/users`

```
❖ 𝗨𝘀𝗲𝗿𝘀

━━━━━━━━━━━━━━━━━━━━

▸ Total · 1,204
▸ Page · 1 / 121
▸ Sort · newest first

◆ active · ◇ blocked · ✓ admin
```
```
buttons → [ 123456789 · ◆ ] [ 987654321 · ✓ ]
buttons → [ 555555555 · ◆ ] [ 444444444 · ◇ ]
buttons → [ « Prev ] [ Page 1 / 121 ] [ Next » ]
buttons → [ ⟡ Find ] [ ◇ Blocked ] [ ❖ Menu ]
```
Tapping an entry opens that user's card.

**Find user** — `/find` (prompt)

```
⟡ 𝗙𝗶𝗻𝗱 𝗨𝘀𝗲𝗿

━━━━━━━━━━━━━━━━━━━━

Send an ID, username, or name fragment.

▸ Example · 123456789
▸ Example · @johndoe
▸ Example · john

▸ Cancel · /cancel
```

**Find results** — `/find john`

```
❖ 𝗙𝗶𝗻𝗱 𝗥𝗲𝘀𝘂𝗹𝘁𝘀

━━━━━━━━━━━━━━━━━━━━

▸ Query · john
▸ Matches · 3

Select a user to open their card.
```
```
buttons → [ 123456789 · @johndoe ]
buttons → [ 222222222 · @johnny ]
buttons → [ 333333333 · John ]
buttons → [ ❖ Menu ]
```

**User card** — `/user 123456789`

```
❖ 𝗨𝘀𝗲𝗿 · 123456789

━━━━━━━━━━━━━━━━━━━━

✦ 𝗣𝗿𝗼𝗳𝗶𝗹𝗲

▸ Name · John Doe
▸ Username · @johndoe
▸ Language · en
▸ Premium · ◇ No

✦ 𝗔𝗰𝘁𝗶𝘃𝗶𝘁𝘆

▸ Joined · 2026-07-02
▸ Last seen · 3 min ago
▸ Requests · 812
▸ Favorites · 24

✦ 𝗦𝘁𝗮𝘁𝘂𝘀

✓ Active
◇ No active block

✦ 𝗡𝗼𝘁𝗲𝘀

▸ 1 note on file
```
```
buttons → [ ◆ Block ] [ ⟡ Add Note ]
buttons → [ ◇ View Notes ] [ ⟡ Export Row ]
buttons → [ « Back ] [ ❖ Menu ]
```

**Block confirmation**

```
◆ 𝗕𝗹𝗼𝗰𝗸 𝗨𝘀𝗲𝗿

━━━━━━━━━━━━━━━━━━━━

▸ User · 123456789
▸ Username · @johndoe
▸ Reason · spam
▸ Duration · permanent

Confirm this action.
```
```
buttons → [ ◆ Confirm Block ] [ ◇ Cancel ]
```

**Block result**

```
✓ 𝗕𝗹𝗼𝗰𝗸𝗲𝗱

━━━━━━━━━━━━━━━━━━━━

▸ User · 123456789
▸ By · 999999999
▸ Reason · spam
▸ Logged · audit entry written
```

**Blocked list** — `/blocked`

```
◆ 𝗕𝗹𝗼𝗰𝗸𝗲𝗱 𝗨𝘀𝗲𝗿𝘀

━━━━━━━━━━━━━━━━━━━━

▸ Active blocks · 12
▸ Page · 1 / 2
```
```
buttons → [ 123456789 · spam ]
buttons → [ 222222222 · abuse ]
buttons → [ « Prev ] [ Page 1 / 2 ] [ Next » ]
buttons → [ ❖ Menu ]
```
Tapping an entry opens the user card, where `◇ Unblock` lives behind a confirm step.

**Broadcast · prompt**

```
⟡ 𝗕𝗿𝗼𝗮𝗱𝗰𝗮𝘀𝘁

━━━━━━━━━━━━━━━━━━━━

Send the message to broadcast.

▸ Supports · text or photo with caption
▸ Audience · all non-blocked users
▸ Cancel · /cancel
```

**Broadcast · preview**

```
❖ 𝗕𝗿𝗼𝗮𝗱𝗰𝗮𝘀𝘁 𝗣𝗿𝗲𝘃𝗶𝗲𝘄

━━━━━━━━━━━━━━━━━━━━

▸ Audience · 1,192 users
▸ Rate · 20 per second
▸ ETA · about 1 minute

✦ 𝗠𝗲𝘀𝘀𝗮𝗴𝗲

▸ <the exact body that will be sent>
```
```
buttons → [ ◆ Send Now ] [ ⟡ Edit ] [ ◇ Cancel ]
```

**Broadcast · progress** (edited in place while running)

```
⟡ 𝗕𝗿𝗼𝗮𝗱𝗰𝗮𝘀𝘁 𝗥𝘂𝗻𝗻𝗶𝗻𝗴

━━━━━━━━━━━━━━━━━━━━

▸ Sent · 412 / 1,192
▸ Failed · 3
▸ Elapsed · 22s
```
```
buttons → [ ◇ Cancel ]
```

**Broadcast · summary**

```
✓ 𝗕𝗿𝗼𝗮𝗱𝗰𝗮𝘀𝘁 𝗖𝗼𝗺𝗽𝗹𝗲𝘁𝗲

━━━━━━━━━━━━━━━━━━━━

▸ Delivered · 1,187
▸ Failed · 5
▸ Duration · 1m 04s
▸ Sent by · 999999999
```

**Export** — `/export users`

```
✓ 𝗘𝘅𝗽𝗼𝗿𝘁 𝗥𝗲𝗮𝗱𝘆

━━━━━━━━━━━━━━━━━━━━

▸ Dataset · users
▸ Rows · 1,204
▸ Columns · id, username, first_name, joined, last_seen, requests, blocked
```
```
media → users_2026-09-14.csv (document)
```

**Audit log** — `/logs`

```
❖ 𝗔𝘂𝗱𝗶𝘁 𝗟𝗼𝗴

━━━━━━━━━━━━━━━━━━━━

▸ Entries · 3,410
▸ Page · 1 / 341

▸ 2026-09-14 11:02 · 999999999 · block · 123456789
▸ 2026-09-14 10:41 · 999999999 · note · 222222222
▸ 2026-09-14 09:15 · 999999999 · broadcast · 1,187 sent
```
```
buttons → [ ⟡ Filter by Action ]
buttons → [ « Prev ] [ Page 1 / 341 ] [ Next » ]
buttons → [ ❖ Menu ]
```

**Health** — `/health`

```
❖ 𝗛𝗲𝗮𝗹𝘁𝗵

━━━━━━━━━━━━━━━━━━━━

✦ 𝗥𝘂𝗻𝘁𝗶𝗺𝗲

▸ Mode · ◆ Polling
▸ Uptime · 3d 04h 12m
▸ Version · 1.0.0

✦ 𝗦𝗼𝘂𝗿𝗰𝗲

✓ Reachable
▸ Latency · 412 ms
▸ Last error · none

✦ 𝗗𝗮𝘁𝗮

▸ Database · 1.8 MB
▸ Post cache · 604 entries
▸ Cache hits · 84%
▸ Sessions · 12 active

▸ Pending deletions · 2 queued

━━━━━━━━━━━━━━━━━━━━
```
```
buttons → [ ⟡ Reload Caches ] [ ❖ Menu ]
```
`▸ Pending deletions` is the live count of media messages still waiting for the 30-minute
sweeper.

**Roles** — `/admins`

```
❖ 𝗔𝗱𝗺𝗶𝗻𝘀

━━━━━━━━━━━━━━━━━━━━

▸ Owners · 1
▸ Admins · 2
▸ Moderators · 3

✦ 𝗘𝗻𝘁𝗿𝗶𝗲𝘀

▸ 999999999 · ◆ owner
▸ 888888888 · ◆ admin
▸ 777777777 · ◇ moderator
```
```
buttons → [ ⟡ Add Admin ] [ ◇ Remove Admin ]
buttons → [ ❖ Menu ]
```

**Global stats** — `/astats`

```
❖ 𝗚𝗹𝗼𝗯𝗮𝗹 𝗦𝘁𝗮𝘁𝘀

━━━━━━━━━━━━━━━━━━━━

✦ 𝗨𝘀𝗲𝗿𝘀

▸ Total · 1,204
▸ New today · 27
▸ Active 24h · 318
▸ Active 7d · 741
▸ Blocked · 12

✦ 𝗨𝘀𝗮𝗴𝗲

▸ Requests today · 9,318
▸ Posts viewed · 41,002
▸ Favorites · 6,884
▸ Broadcasts · 7

━━━━━━━━━━━━━━━━━━━━
```
```
buttons → [ ⟡ Export CSV ] [ ❖ Menu ]
```

━━━━━━━━━━━━━━━━━━━━

✦ 𝗦𝘆𝘀𝘁𝗲𝗺 𝗦𝘁𝗮𝘁𝗲𝘀

**Source unavailable** — `RequestError`

```
【 𝗜𝗠𝗣𝗢𝗥𝗧𝗔𝗡𝗧 】

◆ 𝗦𝗼𝘂𝗿𝗰𝗲 𝗨𝗻𝗮𝘃𝗮𝗶𝗹𝗮𝗯𝗹𝗲
━━━━━━━━━━━━━━━━━━━━

The requested operation could not be completed.

▸ Reason · request timed out
▸ Retry · try again in a moment
```
```
buttons → [ ⟡ Retry ] [ ❖ Menu ]
```

**Source layout changed** — `ParseError`

```
【 𝗜𝗠𝗣𝗢𝗥𝗧𝗔𝗡𝗧 】

◆ 𝗦𝗼𝘂𝗿𝗰𝗲 𝗨𝗽𝗱𝗮𝘁𝗲𝗱
━━━━━━━━━━━━━━━━━━━━

This page could not be read.

▸ Reason · the source changed its layout
▸ Action · the maintainer has been notified
```
```
buttons → [ ❖ Menu ]
```

**Rate limited** — throttling middleware

```
◇ 𝗦𝗹𝗼𝘄 𝗗𝗼𝘄𝗻

━━━━━━━━━━━━━━━━━━━━

Too many requests.

▸ Limit · 6 per 10 seconds
▸ Retry · in a few seconds
```

**Blocked user** — refused at middleware level

```
◆ 𝗔𝗰𝗰𝗲𝘀𝘀 𝗥𝗲𝘀𝘁𝗿𝗶𝗰𝘁𝗲𝗱

━━━━━━━━━━━━━━━━━━━━

You cannot use this bot.

▸ Reason · <reason>
▸ Since · 2026-09-14
▸ Question · contact <support handle>
```

**Maintenance mode** — shown to non-admins while enabled

```
◆ 𝗠𝗮𝗶𝗻𝘁𝗲𝗻𝗮𝗻𝗰𝗲

━━━━━━━━━━━━━━━━━━━━

The bot is being updated.

▸ Status · ◇ Temporary
▸ Please try again shortly
```

**Session expired** — generic, for any stale menu

```
◇ 𝗦𝗲𝘀𝘀𝗶𝗼𝗻 𝗘𝘅𝗽𝗶𝗿𝗲𝗱

━━━━━━━━━━━━━━━━━━━━

This menu is no longer active.

▸ Fix · reopen it from the menu
```
```
buttons → [ ❖ Menu ]
```

**Unknown input** — fallback handler

```
◇ 𝗨𝗻𝗸𝗻𝗼𝘄𝗻 𝗜𝗻𝗽𝘂𝘁

━━━━━━━━━━━━━━━━━━━━

That input was not recognised.

▸ Try · /help
▸ Or pick a section below
```
```
buttons → [ ❖ Menu ] [ ⟡ Search ]
```

**Empty state · favorites**

```
◇ 𝗡𝗼𝘁𝗵𝗶𝗻𝗴 𝗦𝗮𝘃𝗲𝗱

━━━━━━━━━━━━━━━━━━━━

You have no favorites yet.

▸ Tip · press ♡ Save on any gallery
```
```
buttons → [ ❖ Latest ] [ ⟡ Search ]
```

**Empty state · history**

```
◇ 𝗡𝗼 𝗛𝗶𝘀𝘁𝗼𝗿𝘆

━━━━━━━━━━━━━━━━━━━━

You have not opened a post yet.

▸ Tip · browse /latest to get started
```
```
buttons → [ ❖ Latest ]
```

**Mirror · admin action** — posted to `LOG_CHANNEL_ID`

```
◆ 𝗔𝗱𝗺𝗶𝗻 𝗔𝗰𝘁𝗶𝗼𝗻

━━━━━━━━━━━━━━━━━━━━

▸ Action · block
▸ Target · 123456789
▸ By · 999999999
▸ Reason · spam
▸ Time · 2026-09-14 11:02
```

**Mirror · unexpected error** — posted to `LOG_CHANNEL_ID`

```
◆ 𝗕𝗼𝘁 𝗘𝗿𝗿𝗼𝗿

━━━━━━━━━━━━━━━━━━━━

▸ Where · handlers/browse.py · latest
▸ Type · RequestError
▸ User · 123456789
▸ Time · 2026-09-14 11:02
```

━━━━━━━━━━━━━━━━━━━━

✦ 𝗜𝗺𝗮𝗴𝗲 𝗗𝗲𝗹𝗶𝘃𝗲𝗿𝘆 (URL-only, Telegram fetches)

Primary path — **never download, never re-host**:

▸ Single image · `message.answer_photo(photo=<image_url>, caption=...)`
▸ Album page · `message.answer_media_group(media=[InputMediaPhoto(media=<url>, ...), ...])`
▸ aiogram passes the URL string straight through; Telegram's servers fetch and cache it,
  which keeps the bot's bandwidth and CPU near zero.

`bot/services/delivery.py` owns this and provides:
▸ `send_media_page(bot, chat_id, urls, ...)` — one gallery page as a media group, or a single
  photo in `single` mode; this is the only place that talks to Telegram about images
▸ `send_preview_photo(...)` — one URL photo with a caption; used for the post card and the
  `/search` result card, and returns `None` when Telegram refuses the URL so the caller can
  fall back to a text card instead of failing the screen
▸ `edit_to_photo(...)` — in-place paging used by `single` mode
▸ the byte fallback below lives *inside* `send_media_page`, so the happy path stays URL-only

Constraints that shape the code (Telegram Bot API):
▸ Album · 2–10 items per media group; gallery page size is clamped to that range
▸ Caption · 1024 chars max, so gallery captions carry metadata, never descriptions
▸ By-URL photos · Telegram must be able to fetch them; each is capped at 10 MB
▸ `callback_data` · 64 bytes max, hence short session ids instead of long URLs

Fallback (opt-in via `IMAGE_FALLBACK_UPLOAD=true`, and only on failure):
if Telegram rejects a URL (`Bad Request: failed to get HTTP URL content`,
`wrong file identifier`, or 4xx from the CDN), the delivery service re-sends that image
using `BufferedInputFile(await ctele.download_image(url))`. Failures are counted and, if
they exceed a threshold for a post, the remaining pages switch to byte mode for the rest
of that gallery. This keeps the happy path URL-only exactly as requested while making the
bot robust against hotlink-protection or CDN rejection.

✦ 𝗔𝘂𝘁𝗼-𝗗𝗲𝗹𝗲𝘁𝗶𝗼𝗻 (30-minute media TTL)

**Why this exists.** The bot only ever *links* to images that live on the source — it never
re-hosts them. A copied image sitting in a Telegram chat is still a copy, so every
image-bearing message the bot sends is removed on a timer. Default TTL is **30 minutes**
(`AUTO_DELETE_TTL_MINUTES=30`); the user is told this on every screen that shows media.

**What is covered** (`AUTO_DELETE_SCOPE=media`)
▸ Gallery pages — albums, and single-mode photos
▸ The thumbnail attached to the `/search` result card (the card is edited, never re-sent,
  so it is queued once and removed once)
▸ Post-card thumbnails
▸ Nothing else: text cards, menus, admin output and the audit log are never touched

**How it works**
1. Every send goes through `bot/services/delivery.py`, which returns the `Message` objects.
2. The handler passes them to `DeletionService.schedule_messages(...)`, which writes one
   `scheduled_deletions` row per message (`chat_id`, `message_id`, `delete_at`, `kind`,
   `attempts`, `user_id`).
3. A background sweeper (`DeletionService.start()`, every `AUTO_DELETE_SWEEP_INTERVAL`
   seconds, minimum 15) loads due rows, calls `delete_message`, and drops the row on
   success. Failures retry up to 5 attempts and are then retired — a message the user
   deleted by hand is not an error.
4. The queue lives in SQLite, so a restart does not lose pending deletions; the sweeper
   resumes where it left off. `/health` reports `▸ Pending deletions · <n>`.

**Disclosure to the user** — shown, not buried in a privacy note:

```
◆ Auto-delete · this is removed in 30 min
```

▸ `/start` welcome card · `▸ Media · auto-deleted after 30 min`
▸ Post card · `◆ Auto-delete · this is removed in 30 min`
▸ Gallery caption (album and single) · the same line, with the live TTL label
▸ `/settings`, `/profile` · repeated in the `Good to Know` section
▸ `/about` · the full explanation: 30 minutes, why it is done, and how to keep a copy
  outside Telegram

The TTL is rendered from configuration, so changing `AUTO_DELETE_TTL_MINUTES` changes both
the behaviour and the wording — they can never drift apart.

✦ 𝗚𝗮𝗹𝗹𝗲𝗿𝘆 𝗣𝗮𝗴𝗶𝗻𝗮𝘁𝗶𝗼𝗻

▸ Page size · user setting `images_per_page`, default 5, clamped to 2–10
▸ Page math · `total_pages = ceil(len(images) / per_page)`; 1-indexed labels
▸ Album mode (default) · each page is one media group; navigating deletes the previous
  page's message(s) and sends the new album, so the chat shows exactly one gallery at a time
▸ Single mode (optional setting) · one image per screen, navigated with `edit_message_media`
  for zero-chat-clutter in-place paging; fastest feel on slow connections
▸ Session payload · `sid → {post_url, images}` held in the in-memory session store with a
  30-minute TTL; expired sids answer with `◇ Session expired · run /gallery again`
▸ Safety · before sending an album the URLs for that page are de-duplicated; if Telegram
  still drops individual items, the service reports `▸ Sent · 5 / 6` with a retry button

✦ 𝗖𝗮𝗰𝗵𝗶𝗻𝗴 𝗮𝗻𝗱 𝗥𝗮𝘁𝗲 𝗟𝗶𝗺𝗶𝘁𝗶𝗻𝗴

▸ In-memory TTL cache · listing pages (`LISTING_CACHE_TTL`) and taxonomy
▸ DB `post_cache` · post metadata + image lists (`POST_CACHE_TTL`), surviving restarts;
  gallery pages 2..N therefore cost zero source requests
▸ Global semaphore · `SOURCE_CONCURRENCY` caps concurrent SDK calls across all users
▸ Per-user throttle · `THROTTLE_RATE`/`THROTTLE_PERIOD` with a silent drop + toast
▸ Retry policy · 2 retries with small backoff on `RequestError`; `ParseError` is never retried
▸ Cache stats · hits/misses exposed in `/health`

✦ 𝗠𝗶𝗱𝗱𝗹𝗲𝘄𝗮𝗿𝗲 𝗢𝗿𝗱𝗲𝗿

`logging` → `db` → `admin` → `user` → `maintenance` → `throttle`
(registered as *outer* middleware on `message` and `callback_query`, in that order)

▸ `db` · opens one `AsyncSession` per update, commits on success, rolls back on exception
▸ `user` · upserts the user, updates `last_seen_at`/`username`, bumps `request_count`,
  bumps `daily_stats`, and drops blocked users before any handler runs
▸ `admin` · loads the admin role into `data["role"]` so filters and handlers stay cheap
▸ `maintenance` · while the lock is on only admins get past; everyone else receives the
  maintenance card
▸ `throttle` · in-memory token bucket keyed by user id, applied last so a flood can never
  reach a handler or the source

✦ 𝗦𝗲𝗰𝘂𝗿𝗶𝘁𝘆 𝗮𝗻𝗱 𝗦𝗮𝗳𝗲𝘁𝘆

▸ Age gate · 18+ confirmation stored in `users.age_verified` before any source content
▸ Admin auth · DB-backed roles only; `ADMIN_IDS` is bootstrap-only, never a live bypass
▸ Owner guard · the last remaining owner cannot be demoted (`/deladmin` refuses)
▸ Audit everything · block/unblock/note/broadcast/role/export all write `audit_logs`
▸ Input hygiene · URLs validated against the configured source host before use
▸ Output hygiene · all interpolated content HTML-escaped; titles truncated to safe widths
▸ No secrets in logs · token and DSN are redacted in exception traces
▸ Graceful failure · every handler wrapped by a global error handler; unexpected
  exceptions are logged, reported to `LOG_CHANNEL_ID`, and answered with a calm card

✦ 𝗟𝗼𝗴𝗴𝗶𝗻𝗴, 𝗦𝘁𝗮𝘁𝘀, 𝗢𝗯𝘀𝗲𝗿𝘃𝗮𝗯𝗶𝗹𝗶𝘁𝘆

▸ Console + rotating file (`logs/bot.log`, 5 MB × 5)
▸ Structured update logs: user id, command, duration, cache hit
▸ `/health` · SDK latency, last error, cache hit ratio, DB size, uptime, session count,
  pending auto-deletions
▸ `daily_stats` powers `/astats` growth numbers without expensive aggregate queries

✦ 𝗥𝘂𝗻𝘁𝗶𝗺𝗲: 𝗙𝗮𝘀𝘁𝗔𝗣𝗜 + 𝗮𝗶𝗼𝗴𝗿𝗮𝗺 (𝗯𝗼𝘁𝗵 𝗺𝗼𝗱𝗲𝘀)

One process serves both concerns. **FastAPI + uvicorn is always the HTTP layer**, and
`RUN_MODE` decides how updates reach the dispatcher:

▸ **`polling` (default)** · uvicorn serves the FastAPI app and long-polling runs as an
  `asyncio.Task` inside the same event loop, started in the FastAPI lifespan and cancelled
  cleanly on shutdown. No public URL or HTTPS certificate required — ideal for a VPS.
▸ **`webhook`** · FastAPI exposes `POST {WEBHOOK_PATH}`; each request validates
  `X-Telegram-Bot-Api-Secret-Token` against `WEBHOOK_SECRET`, then hands the update to the
  dispatcher via `dp.feed_update(bot, update)`. `set_webhook(...)` runs on startup, and
  `delete_webhook(...)` on shutdown when `WEBHOOK_DELETE_ON_SHUTDOWN=true`.

Startup sequence (`start.py` → `bot/api/app.py` lifespan):

```
init_logging() → load Settings → init_db() → build Bot + Dispatcher
  → register_commands(bot)            # user scope + per-admin-chat scopes
  → app = create_app(bot, dp)         # FastAPI + /healthz + /readyz
  → deletions.start()                 # 30-minute media auto-delete sweeper
  → RUN_MODE == "webhook" ? set_webhook(...)
                          : asyncio.create_task(dp.start_polling(bot, handle_signals=False))
  → uvicorn.Server(config).serve()
```

Shutdown (SIGINT/SIGTERM) unwinds in reverse: stop the deletion sweeper, cancel and await
the polling task, close the aiogram session, close the shared `httpx` client inside
`CTeleClient`, dispose the SQLAlchemy engine, flush logs.

Implementation notes:
▸ `dp.start_polling(..., handle_signals=False)` — uvicorn owns signal handling, so aiogram
  must not install competing handlers.
▸ `allowed_updates=dp.resolve_used_update_types()` is passed to both `start_polling` and
  `set_webhook`, so Telegram never sends updates we cannot route.
▸ The polling task is supervised: an unexpected exit is logged and mirrored to
  `LOG_CHANNEL_ID` instead of dying silently.
▸ The auto-delete sweeper is an independent `asyncio.Task` alongside the polling task, so
  media cleanup keeps running in webhook mode too (where there is no polling task at all).
  It swallows its own exceptions and can never take the bot down.
▸ FastAPI also gives free operational surface: `GET /` (uptime JSON), `GET /healthz`
  (liveness), `GET /readyz` (DB + source reachability) — everything Railway, Render, Koyeb,
  or Fly needs for health checks.
▸ uvicorn runs with `access_log=False` by default, so our structured logger stays the single
  source of truth; enable it with `LOG_LEVEL=DEBUG`.

✦ 𝗜𝗺𝗽𝗹𝗲𝗺𝗲𝗻𝘁𝗮𝘁𝗶𝗼𝗻 𝗡𝗼𝘁𝗲𝘀 (as built)

Where the delivered code adds to, or differs from, the sketch above:

▸ `bot/utils/` was added · `logger.py` (rotating logs + secret redaction), `text.py`
  (escaping, truncation, number formatting) and `time.py` (naive-UTC helpers) were pulled out
  of the handlers so the same rules apply everywhere
▸ `bot/handlers/common.py` was added · one set of listing, search-card and gallery renderers
  is shared by `/latest`, `/popular`, `/category`, `/search`, `/favorites` and `/history`, so
  pagination and the auto-delete scheduling live in exactly one place. `present_card()` and
  `show_screen()` also own the edit-in-place rule, so no handler decides it on its own
▸ `bot/handlers/errors.py` was added · a single global error handler replaces scattered
  try/except blocks for unexpected failures
▸ `bot/database/repository/content.py` carries favorites **and** history;
  `moderation.py` carries blocks, notes, the audit log **and** the deletion queue — six
  repository modules instead of the eight originally sketched
▸ `bot/services/deletion.py` implements the 30-minute media TTL (see the auto-deletion
  section); `scheduled_deletions` and `user_notes` are the two tables added for it
▸ Models stay relationship-free (plain foreign-key columns) so lazy loading can never raise
  a greenlet error; joins are written explicitly in the repository layer
▸ `.env` values are parsed leniently — an empty `LOG_CHANNEL_ID=` must not crash startup
▸ Unpaired surrogates are stripped in `esc()` and `truncate()` (`strip_surrogates()` in
  `bot/utils/text.py`), so a title decoded from broken HTML can never make a send fail to
  encode as UTF-8; the log handlers replace unencodable characters instead of raising, and
  `_title_for()` uses real characters rather than surrogate escape pairs
▸ `SEARCH_THUMBNAILS` was implemented as “attach the result's own thumbnail to the
  single-result card”, so one result is judged at a glance without opening its gallery;
  the numbered album it used to send is gone

✦ 𝗗𝗲𝗽𝗹𝗼𝘆𝗺𝗲𝗻𝘁

```
python -m venv .venv
.venv\Scripts\activate            # (bash: source .venv/bin/activate)
pip install -r requirements.txt
# edit .env  ->  BOT_TOKEN, ADMIN_IDS
python start.py                   # polls Telegram; FastAPI on API_PORT
# or set RUN_MODE=webhook (+ WEBHOOK_BASE_URL) and expose API_PORT publicly
```

▸ `start.py` runs from the project root so `import bot` **and** `import ctele` both resolve;
  it also inserts the root on `sys.path` defensively before importing either.
▸ Pre-flight checks: token format, `ADMIN_IDS` parsed, DB writable, source reachable
  (warn-only), then `register_commands()` runs. Only a missing/invalid token is fatal.
▸ Requirements: `aiogram`, `fastapi`, `uvicorn[standard]`, `SQLAlchemy`, `aiosqlite`,
  `pydantic-settings`, `httpx` and `selectolax` (the last two are required by `ctele`
  itself), pinned to known-good versions.
━━━━━━━━━━━━━━━━━━━━

✦ 𝗕𝘂𝗶𝗹𝗱 𝗣𝗵𝗮𝘀𝗲𝘀

▸ **Phase 1 · Foundation** — `config.py`, `loader.py`, `database/*` (models, base, repositories),
  all middlewares, logging, `commands.py` auto-registration, the FastAPI app (lifespan-owned
  polling task + webhook route), and a runnable `start.py` that answers `/start` and `/ping`
▸ **Phase 2 · Core browsing** — `ctele_service`, session store, paginator, keyboards, and
  `/latest`, `/popular`, `/categories`, `/category`, `/search` (one result per card, its own
  thumbnail attached, numbers jumping through an in-chat prompt), `/random`
▸ **Phase 3 · Post + gallery** — post detail card, `delivery.py` URL sending,
  album/single modes, gallery pagination, fallback path
▸ **Phase 4 · Account** — age gate, `/profile`, `/settings`, `/stats`, `/favorites`,
  `/history`
▸ **Phase 5 · Admin** — `/admin`, `/users`, `/find`, `/user`, `/block`, `/unblock`,
  `/blocked`, `/note`, `/logs`, `/export`, roles
▸ **Phase 6 · Ops** — `/broadcast` with progress + cancel, `/astats`, `/health`,
  `/maintenance`, `/reload`, `LOG_CHANNEL_ID` mirroring
▸ **Phase 7 · Package** — README, `.env.example`, `.gitignore`, `requirements.txt` pins, a
  smoke test of both run modes, and `bot.zip` (excluding `ctele/`)

✦ 𝗔𝗰𝗰𝗲𝗽𝘁𝗮𝗻𝗰𝗲 𝗖𝗿𝗶𝘁𝗲𝗿𝗶𝗮

✓ `python start.py` on a clean machine with only `ctele/` copied in → bot comes online,
  creates `Database.db`, sets commands, and answers `/start`
✓ Every user command in the table above works end-to-end against the live source
✓ Command menus register themselves on boot, in default and per-admin-chat scopes
✓ Polling (default) and webhook both run behind FastAPI; `GET /healthz` answers on `API_PORT`
✓ `/search` shows one result per card with `‹` / `▸ Open` / `Next ›` on top and a number row
  below; every step edits the same message, and `▸ Open` reaches that post's gallery
✓ The result's own thumbnail rides on that card (`SEARCH_THUMBNAILS=true`), so it can be
  judged without opening anything, and a number jumps via the in-chat prompt
✓ Galleries paginate with the configured page size, using URL photos only
✓ Every media message is queued at send time and removed within the configured TTL
  (`AUTO_DELETE_TTL_MINUTES`, default 30), with the TTL disclosed on the screens that show it
✓ Pending deletions survive a restart, and the sweeper runs in both polling and webhook mode
✓ A blocked user is refused at middleware level and appears in `/blocked`
✓ `/broadcast` reaches all non-blocked users with progress, abort, and a recorded summary
✓ No emoji anywhere in bot output; every message follows the symbol system
✓ Restart-safe: post cache and user data survive; stale sessions fail gracefully

✦ 𝗗𝗲𝗰𝗶𝘀𝗶𝗼𝗻𝘀 𝗜 𝗡𝗲𝗲𝗱 𝗙𝗿𝗼𝗺 𝗬𝗼𝘂

◆ Defaults I will use unless you say otherwise:

▸ Run mode · `polling` by default, `webhook` opt-in through `RUN_MODE` — FastAPI serves both
▸ Command menus · auto-registered on every boot, plus per-admin-chat scopes
▸ Search select · opens the gallery first (`SEARCH_SELECT_TARGET=gallery`)
▸ Search card · one result per screen with its own thumbnail attached
  (`SEARCH_THUMBNAILS=true`)
▸ Search jump · the number row asks for the number in chat instead of guessing, and both the
  reply and the prompt are consumed silently
▸ Images per gallery page · `5` (clamped 2–10)
▸ Media auto-delete · on, 30 minutes (`AUTO_DELETE_TTL_MINUTES=30`), media only, with the TTL
  stated on every screen that shows an image
▸ Default gallery mode · `album` (media group per page), `single` available in `/settings`
▸ Age gate · `on` — the source is adult content; users confirm 18+ once
▸ Image fallback upload · `on` (URL-only is still the primary path)
▸ `/help` scope · users see user commands, admins see both tables
▸ Listed commands · `/surprise`, `/top`, `/open`, `/share`, `/sync`, `/whois`, `/flag`
  are included only if you approve the “Suggested Additions” section
▸ Reply keyboard · a small persistent menu (`Latest`, `Popular`, `Search`, `Help`) is shown;
  say the word and I will keep it inline-only
▸ Admin bootstrap · `ADMIN_IDS` from `.env` becomes `owner` on first run

✦ 𝗪𝗵𝗮𝘁 𝗬𝗼𝘂 𝗚𝗲𝘁 𝗔𝗳𝘁𝗲𝗿 𝗔𝗽𝗽𝗿𝗼𝘃𝗮𝗹

A single `bot.zip` containing everything in the deliverable layout **except** `ctele/`,
plus `README.md` (hosting steps) and this `plan.md`. Drop your `ctele/` folder in, set
`BOT_TOKEN` and `ADMIN_IDS`, run `python start.py`. Command menus register themselves, and
FastAPI starts on `API_PORT` in either run mode.

Out of the box, before you change a single setting:
▸ `/search` shows one result per card — thumbnail included — and steps through the whole
  query without ever leaving more than one card behind
▸ Every image the bot sends is auto-deleted 30 minutes later, and each caption says so
▸ `Database.db` is created on first boot; no other manual step is required

━━━━━━━━━━━━━━━━━━━━

· End of plan ·
