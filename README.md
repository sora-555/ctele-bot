# CosplayTele Telegram Bot

An aiogram 3 browser bot for the CosplayTele galleries, with a SQLite-backed
user/analytics store and a FastAPI health layer. Search, browse, save and
broadcast all run from this one process.

The `ctele/` SDK package is supplied separately. It is intentionally not part of
this project and is never generated here.

## Requirements

- Python 3.11 or newer
- The `ctele/` package copied into the project root

## Setup

1. Copy `ctele/` from the supplied SDK into the project root.
2. Copy `.env.example` to `.env` and set `BOT_TOKEN` and `ADMIN_IDS`.
3. Install dependencies:

       pip install -r requirements.txt

4. Run:

       python main.py

`main.py` is the only entry point. It creates or upgrades the database, runs the
legacy schema top-ups, applies `alembic upgrade head`, backfills orphan rows, bootstraps admins from `ADMIN_IDS`,
starts the auto-delete sweep and resumes any interrupted broadcast before
polling starts.

Polling is the default. Set `RUN_MODE=webhook` and `WEBHOOK_BASE_URL` to run
behind Telegram's webhook instead; the FastAPI app serves `/`, `/healthz`,
`/readyz` and `/webhook` in both modes on `API_PORT`.

## User commands

| Command | Purpose |
|---------|---------|
| `/start` | Main menu; `post-<slug>` payloads open a shared gallery |
| `/menu` | Main menu |
| `/search <query>` | Search the source |
| `/latest`, `/popular`, `/random` | Discovery without a query |
| `/categories` | Category list, then a paginated listing |
| `/favorites` | Saved posts and saved images, in two tabs |
| `/history` | Galleries you opened |
| `/add_friends` | Create a two-day friend invite link |
| `/friends` | Manage friends and permission to send messages |
| `/suggestions <message>` | Send a suggestion to bot admins; it can also reply to a message |
| `/profile` | Your counters |
| `/settings` | Per-user preferences |
| `/help`, `/about`, `/cancel` | Command list, bot info, leave an input prompt |

## Admin commands

Admins are the ids in `ADMIN_IDS` (bootstrapped as owners) plus anyone added to
the `admins` table.

| Command | Purpose |
|---------|---------|
| `/admin` | Panel: users, find, broadcast, stats, export, audit, maintenance |
| `/users [page]` | Paginated user list |
| `/find <query>` | Match by id, username or name |
| `/user <id>` | User card with real counters and block state |
| `/block`, `/unblock <id>` | Take effect on the user's next update |
| `/stats` | Totals, DAU/WAU, top saved posts, top searches |
| `/export` | CSV of every user |
| `/audit` | Recent admin actions |
| `/broadcast` | Compose, pick a segment, send |
| `/broadcast_status` | The last five runs |

`/broadcast` accepts any message type: the draft is copied back as a preview,
delivered with `copy_message`, and driven by a keyset cursor so a run can be
paused, cancelled and resumed after a restart. Blocked users are flagged
`bot_blocked` instead of failing the run.

## Navigation

Every list in the bot is rendered by `bot/handlers/viewer.py`: search results,
category listings, saved posts, saved images and history all share one card
keyboard and one gallery viewer, and every screen edits a single message in
place. Tabs, numbered rows and prev/next are bounded, so the first and last
item never show a dead button.

In the gallery, `Save image` stores exactly the image on screen (the star flips
to show it), `Save post` stores the whole set, `Download` uploads the bytes, and
`Share` returns a `t.me/<bot>?start=post-<slug>` link that reopens the gallery.
`Send to friends` lets you select friends, add an optional message up to 1000
characters, and deliver the post only to friends who have send permission
enabled. Recipients can delete the delivered bot message or revoke that
friend's future send permission.

## Storage

- SQLite through SQLAlchemy async, WAL mode, `foreign_keys=ON` and a 15 s
  `busy_timeout`.
- **Any update that carries a `from_user` provisions that user**, so the `users`
  table always reflects who has interacted.
- SQLite allows one writer at a time, so a handler must never open a second
  connection while the update's transaction holds the write lock - that
  deadlocks until the busy timeout expires. Background writers retry through
  `bot/database/base.py::retry_locked`.
- `alembic/versions/` contains forward migrations for VPS deployments. Run
  `alembic upgrade head` manually before `python main.py` when deploying, and
  startup runs the same command as a final guard. Existing legacy databases are
  stamped by the baseline and upgraded without dropping data.

## Layout

    main.py                     entry point, startup and shutdown
    bot/config.py               settings, loaded from .env / .env.example
    bot/loader.py               shared Bot instance
    bot/main.py                 middleware and router wiring
    bot/handlers/               start, browse, viewer, account, admin, broadcast, errors, fallback
    bot/keyboards/inline.py     every inline keyboard
    bot/texts/                  message builders and the approved glyph table
    bot/middlewares/            throttle, database, user, access, ctele
    bot/database/               engine, models, migrations, repositories
    bot/services/               ctele wrapper, sessions, pagination, broadcast, deletion
    bot/api/                    FastAPI app and webhook

## Conventions

- All user-facing text follows `telegram_skills.md`: no emoji, only the
  approved Unicode glyphs, which are declared once as `\uXXXX` escapes in
  `bot/texts/symbols.py` so every source file stays pure ASCII.
- `bot/texts/ui.py` is the only place message text is built, and it escapes
  every dynamic value.
- Callback data never exceeds 64 bytes and never contains a URL. The prefixes
  are documented in `plan.md` section 9.

`plan.md` holds the full analysis, the defect log and the phase-by-phase
acceptance evidence.
