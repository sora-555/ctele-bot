# CosplayTele Telegram Bot

A production-grade Telegram bot wrapping the local `ctele` SDK (cosplaytele.com), built on
**aiogram v3** with **FastAPI**, **SQLite** and **SQLAlchemy 2.0 (async ORM)**.

- **Images are sent by URL.** Telegram fetches them itself, the bot uploads nothing.
- **`/search` shows thumbnails first**, then a paginated result card whose numbered buttons
  open the matching gallery directly.
- **Every media message is auto-deleted after 30 minutes** (configurable) and the user is
  told so on every screen that shows an image.
- **Command menus register themselves** on boot, including a per-admin-chat menu. No
  BotFather `/setcommands` step.

The complete design document, including a UI mockup for every screen, is `plan.md`.

---

## 1. Requirements

- Python **3.11+** (tested on 3.12)
- A bot token from [@BotFather](https://t.me/BotFather)
- Your own Telegram user id for `ADMIN_IDS` (grab it from [@userinfobot](https://t.me/userinfobot))
- The `ctele` folder (supplied by you; it is not part of this zip)

---

## 2. Quick start

```text
bot.zip root/
├── start.py            # entry point
├── requirements.txt
├── .env                # your live config (placeholders shipped)
├── .env.example        # documented template
├── README.md
├── plan.md
├── bot/                # the whole bot
└── ctele/              # <- copy your own ctele folder in here
```

1. **Drop `ctele/` in.** The bot imports it from the project root, so it must sit next to
   `start.py` and keep its folder name.

2. **Create a virtual environment and install dependencies.**

   Windows:
   ```bat
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

   Linux / macOS:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Edit `.env`.** At minimum:

   ```dotenv
   BOT_TOKEN=123456:PUT-YOUR-BOTFATHER-TOKEN-HERE
   ADMIN_IDS=123456789
   ```

   `ADMIN_IDS` is comma separated. Those ids are bootstrapped as **owners** on the first
   run; after that, roles live in the database and are managed with `/addadmin`.

4. **Run it.**

   ```bash
   python start.py
   ```

   The bot starts polling and FastAPI binds `API_HOST:API_PORT` (default `0.0.0.0:8080`).
   Open your bot in Telegram and send `/start`.

`Database.db` is created automatically on first boot. Nothing else needs a manual step.

---

## 3. Run modes

FastAPI + uvicorn is **always** the HTTP layer. `RUN_MODE` only decides how Telegram
updates reach the dispatcher.

### Polling (default)

```bash
python start.py
# or explicitly
python start.py --polling
```

The polling loop runs as an `asyncio.Task` inside the FastAPI lifespan, so one process
serves both. No public URL or TLS certificate is needed — this is the right choice for a
VPS.

### Webhook

Telegram posts updates to FastAPI instead:

```dotenv
RUN_MODE=webhook
WEBHOOK_BASE_URL=https://bot.example.com
WEBHOOK_PATH=/webhook
WEBHOOK_SECRET=some-long-random-string
```

```bash
python start.py --webhook
```

- `WEBHOOK_BASE_URL` must be a public HTTPS origin; no trailing path.
- `WEBHOOK_SECRET` is validated against the `X-Telegram-Bot-Api-Secret-Token` header on
  every request.
- `set_webhook` runs at startup; set `WEBHOOK_DELETE_ON_SHUTDOWN=true` to remove it when
  the process stops.

> The 30-minute media sweeper runs in **both** modes — it is an independent task, not part
> of the polling loop.

### Command-line overrides

| Flag | Effect |
| --- | --- |
| `--polling` / `--webhook` | Force a run mode for this execution |
| `--host <addr>` | Override `API_HOST` |
| `--port <n>` | Override `API_PORT` |
| `--log-level <lvl>` | Override `LOG_LEVEL` |

---

## 4. HTTP endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/` | Uptime / version JSON |
| `GET` | `/healthz` | Liveness probe for the host |
| `GET` | `/readyz` | Readiness: database + source reachability |
| `POST` | `/webhook` | Telegram updates (webhook mode only) |

Point your host health check at `/healthz`. `/readyz` is the deeper check for load
balancers.

---

## 5. Commands

### User commands

| Command | Usage | What it does |
| --- | --- | --- |
| `/start` | — | Onboarding, 18+ gate, welcome card |
| `/menu` | — | Main menu |
| `/help` | — | Command list (admins see the admin set too) |
| `/latest` | `[page]` | Newest posts |
| `/popular` | `[day\|week\|month\|all] [page]` | Trending posts |
| `/search` | `<text or url>` | One result per card, with its thumbnail |
| `/categories` | — | Browse the source taxonomy |
| `/category` | `<name or path> [page]` | Open one category |
| `/random` | — | Random post |
| `/post` | `<url>` | Open a post link |
| `/last` | — | Reopen the last post |
| `/gallery` | `[page]` | Gallery of the last post |
| `/favorites` | `[page]` | Saved posts |
| `/history` | `[page]` | Recently viewed |
| `/profile` | — | Your profile and counters |
| `/settings` | — | Images per page, album/single, spoiler, thumbnails |
| `/stats` | — | Your usage stats |
| `/about` | — | Bot info and the auto-delete explanation |
| `/ping` | — | Latency check |
| `/cancel` | — | Cancel the current input |

### Admin commands

Available to `owner`, `admin` and (read-only) `moderator` roles.

| Command | Usage | What it does |
| --- | --- | --- |
| `/admin` | — | Control panel with live counters |
| `/astats` | — | Global statistics |
| `/users` | `[page]` | Paginated user list |
| `/find` | `<query>` | Search users by id, username or name |
| `/user` | `<id>` | Full user card with actions |
| `/note` | `<id> <text>` | Attach an internal note |
| `/notes` | `<id>` | List notes for a user |
| `/block` | `<id> [reason]` | Block (with a confirm step) |
| `/unblock` | `<id>` | Lift a block |
| `/blocked` | `[page]` | Active blocks |
| `/broadcast` | — | Message every non-blocked user (preview, progress, cancel) |
| `/export` | `[users\|favorites\|history]` | Download a CSV |
| `/logs` | `[action] [page]` | Audit log |
| `/health` | — | Runtime, source, cache and pending-deletion report |
| `/reload` | — | Clear listing and taxonomy caches |
| `/maintenance` | `[on\|off]` | Lock the bot to admins |
| `/admins` | — | Current role grants |
| `/addadmin` | `<id> <role>` | Grant a role (owner only) |
| `/deladmin` | `<id>` | Revoke a role (owner only) |

---

## 6. Configuration

Everything lives in `.env`; `.env.example` documents every key in place. The ones you are
most likely to touch:

| Key | Default | Purpose |
| --- | --- | --- |
| `BOT_TOKEN` | — | BotFather token (required) |
| `ADMIN_IDS` | — | Bootstrap owners, comma separated |
| `LOG_CHANNEL_ID` | — | Channel that mirrors admin actions and errors |
| `DATABASE_URL` | `sqlite+aiosqlite:///Database.db` | Async SQLAlchemy DSN |
| `RUN_MODE` | `polling` | `polling` or `webhook` |
| `API_HOST` / `API_PORT` | `0.0.0.0` / `8080` | Where FastAPI binds |
| `ITEMS_PER_PAGE` | `6` | Posts per listing page |
| `IMAGES_PER_PAGE` | `5` | Images per gallery page (clamped 2-10) |
| `DEFAULT_DELIVERY_MODE` | `album` | `album` (media group) or `single` (in-place paging) |
| `SEARCH_SELECT_TARGET` | `gallery` | What a `/search` result button opens |
| `SEARCH_THUMBNAILS` | `true` | Attach the result's thumbnail to the search card |
| `AUTO_DELETE_ENABLED` | `true` | Delete media messages on a timer |
| `AUTO_DELETE_TTL_MINUTES` | `30` | How long a media message lives |
| `AUTO_DELETE_SCOPE` | `media` | `media` only, or `all` |
| `AUTO_DELETE_SWEEP_INTERVAL` | `60` | Seconds between sweeper passes |
| `IMAGE_FALLBACK_UPLOAD` | `true` | Re-send as bytes only if Telegram refuses a URL |
| `AGE_GATE` | `true` | 18+ confirmation on first `/start` |
| `THROTTLE_RATE` / `THROTTLE_PERIOD` | `6` / `10` | Anti-flood per user |
| `LOG_LEVEL` / `LOG_DIR` | `INFO` / `logs` | Logging |

Changing `AUTO_DELETE_TTL_MINUTES` changes both the behaviour **and** the wording shown to
users, so the two can never drift apart.

---

## 7. Auto-deletion (why it exists)

The bot never re-hosts an image: it sends the source URL and Telegram does the fetching.
Even so, an image sitting in a chat is a copy, so every image-bearing message the bot sends
is queued for deletion.

- **Covered:** gallery pages (album and single), the `/search` result card, post-card
  thumbnails.
- **Not covered:** text cards, menus, admin output, the audit log.
- **Disclosure:** the TTL is printed on the welcome card, the post card, every gallery
  caption, `/settings` and `/about` — for example
  `Auto-delete · this is removed in 30 min`.
- **Restart safe:** the queue is a table (`scheduled_deletions`) in SQLite, so pending
  deletions survive a restart and the sweeper resumes.
- **Resilient:** a failed delete retries up to 5 times, then the row is retired. A message
  the user already deleted by hand is not an error.
- **Visibility:** `/health` reports `Pending deletions`.

Turn it off with `AUTO_DELETE_ENABLED=false` (the disclosure lines then stop being shown
as well).

---

## 8. How `/search` works

`/search` deliberately shows **one result at a time**. A screen showing six numbered
results makes it easy to press the wrong one, and there is nothing to tell two thumbnails
apart; a screen showing one result cannot be misread.

1. The query goes to the source and the page of results is fetched once, then kept in the
   session. Stepping through a page costs no extra source requests.
2. The card shows `❖ Result 2 / 6`, the title, the query and the window
   (`1-6, more available`). With `SEARCH_THUMBNAILS=true` (default) that result's own
   thumbnail is attached to the card, so you can judge it without opening anything.
3. The top row is `‹` / `▸ Open` / `Next ›`. Stepping rewrites the card with
   `edit_message_media`, so a whole search leaves **one** message in the chat.
4. The number row underneath is a shortcut into the in-chat flow: tapping a number asks
   `Send the number of the result you want to see` in the chat. Your reply and the prompt
   are deleted and the card switches to that result.
5. `▸ Open` goes straight to that post's **gallery** (change with
   `SEARCH_SELECT_TARGET=detail`). The gallery carries a `Details` button for the full card.
6. Four buttons or fewer are refused with a toast: `This is the first result`,
   `No further results`, `The source did not answer, try again`.

The same edit-in-place rule applies everywhere else, so browsing never floods the chat:
text screens are rewritten with `edit_message_text`, photos with `edit_message_media`,
and a photo showing a text card keeps the photo and rewrites its caption. Only two
transitions are impossible for the Telegram API — a text message becoming a photo, and a
photo becoming an album — and only those replace the message, once the new one has landed.

---

## 9. Project layout

```text
bot/
├── config.py          # pydantic-settings Settings
├── loader.py          # Bot / Dispatcher singletons
├── main.py            # routers, middleware chain, error handling
├── commands.py        # automatic command-menu registration
├── api/               # FastAPI app, webhook route, health routes
├── database/          # engine, models, repositories (users, content, moderation, ...)
├── services/          # ctele wrapper, delivery, deletion, pagination, sessions, broadcast
├── keyboards/         # inline + reply keyboards
├── handlers/          # user flows, plus handlers/admin/* for the admin surface
├── middlewares/       # db, admin, user, maintenance, throttle, logging
├── states/ filters/   # FSM states, IsAdmin / IsOwner / private-chat guards
├── texts/             # every user-visible string
└── utils/             # logging, text, time helpers
```

---

## 10. Hosting

### Linux VPS (systemd)

```ini
[Unit]
Description=CosplayTele Telegram Bot
After=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/ctelebot
ExecStart=/opt/ctelebot/.venv/bin/python start.py
Restart=always
RestartSec=5
User=botuser

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ctelebots
```

Point the host health check at `GET /healthz`. For webhook mode, put the process behind
Caddy/nginx with TLS and set `WEBHOOK_BASE_URL` to that public origin.

### PaaS (Railway, Render, Koyeb, Fly)

- Start command: `python start.py`
- Port: set `API_PORT` to the port the platform injects (many set `$PORT`).
- Health check path: `/healthz`
- Add a persistent volume for `Database.db` and `logs/`, otherwise state is lost on
  redeploy.

### Notes

- Keep `Database.db` on a persistent disk; it holds users, roles, caches and the deletion
  queue.
- `LOG_CHANNEL_ID` gives you an operational feed of admin actions and errors in Telegram.
- Rotate `WEBHOOK_SECRET` if it ever leaks; it is the only thing protecting the endpoint.

---

## 11. Troubleshooting

| Symptom | Fix |
| --- | --- |
| `BOT_TOKEN is missing or malformed` | Check `.env` is in the folder you run `python start.py` from |
| `ADMIN_IDS is empty` | Set at least one id, otherwise nobody can reach the admin commands |
| No images in a message | The source may reject hotlinking; check `IMAGE_FALLBACK_UPLOAD=true` and `/health` |
| Images disappear after a while | Expected: the 30-minute auto-delete. Change `AUTO_DELETE_TTL_MINUTES` |
| Admin menu missing in Telegram | Reopen the chat; per-chat scopes are set on boot and may need the chat to exist first |
| `webhook requires WEBHOOK_BASE_URL` | Set a public HTTPS origin, or run in polling mode |
| Empty `LOG_CHANNEL_ID=` | Fine: it is parsed leniently and simply disables mirroring |

---

## 12. License and content

This project ships no media of its own. It links to content hosted by a third party; the
operator of this bot is responsible for how that content is used. The 30-minute
auto-deletion of media messages exists specifically to limit how long a copy stays in a
chat.
