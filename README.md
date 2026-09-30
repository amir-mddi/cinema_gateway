# Cinema Gate — 20-bot edition (updated simplified gate)

A Django project with one central Telegram channel, one dedicated channel per film, and independent per-film assigned bots. The original architecture and models are retained, so **existing database records survive** when updating the code.


## Docker deployment (recommended for the server)

This edition includes a production-oriented Docker Compose setup with four application roles:

- `db`: PostgreSQL 16 with a persistent named volume.
- `migrate`: one-shot migrations + `collectstatic`; web/workers start only after it succeeds.
- `web`: Gunicorn/Django admin and signed redirect endpoints.
- `poller`: runs every active Telegram bot with `bot_polling --all`.
- `expiry`: deletes delivered Telegram messages after their TTL.

The Django admin static files are served with WhiteNoise, so the admin UI works behind Gunicorn without a separate static-file server.

### First deployment on `198.12.73.236`

Install Docker Engine and the Docker Compose plugin, then enter the project directory (the folder containing `compose.yaml`). Copy the safe example environment file and edit it:

```bash
cp .env.example .env
nano .env
```

At minimum replace these placeholders:

```dotenv
DJANGO_SECRET_KEY=GENERATE_A_NEW_LONG_RANDOM_SECRET
DB_PASSWORD=GENERATE_A_STRONG_DATABASE_PASSWORD
ADMIN_TELEGRAM_IDS=YOUR_PERSONAL_TELEGRAM_USER_ID
BOT_TOKEN_BOT01=YOUR_REAL_BOT01_TOKEN
```

The included example already uses:

```dotenv
ALLOWED_HOSTS=198.12.73.236,127.0.0.1,localhost
CSRF_TRUSTED_ORIGINS=http://198.12.73.236:8079
PUBLIC_BASE_URL=http://198.12.73.236:8079
HOST_PORT=8079
DATABASE_ENGINE=postgres
DB_HOST=db
```

Generate a Django secret without installing Django on the host:

```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(64))'
```

Generate a database password similarly:

```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
```

Build and start everything:

```bash
docker compose up -d --build
```

Check status and logs:

```bash
docker compose ps
docker compose logs -f web poller expiry
```

Create the Django administrator once the web container is healthy:

```bash
docker compose exec web python manage.py createsuperuser
```

Open:

```text
http://198.12.73.236:8079/admin/
```

If UFW is enabled, allow the port once:

```bash
sudo ufw allow 8079/tcp
sudo ufw status
```

### Register the Telegram bots

In Django Admin create `BotAccount` rows. The environment variable name is derived from each key:

```text
BotAccount.key=bot01 -> BOT_TOKEN_BOT01
BotAccount.key=bot02 -> BOT_TOKEN_BOT02
...
BotAccount.key=bot20 -> BOT_TOKEN_BOT20
```

Use the actual bot username without `@`. After adding or changing a bot account/token, restart only the poller:

```bash
docker compose restart poller
```

Do not run another `getUpdates` process for the same token on the host at the same time.

### Common Docker commands

```bash
# Status
docker compose ps

# All logs
docker compose logs -f

# Poller logs
docker compose logs -f poller

# Django shell
docker compose exec web python manage.py shell

# Run checks
docker compose exec web python manage.py check

# Run tests
docker compose exec web python manage.py test backend.apps.cinema

# Apply future migrations/collectstatic manually if needed
docker compose run --rm migrate

# Restart app roles without deleting PostgreSQL data
docker compose restart web poller expiry

# Stop containers but KEEP database volume
docker compose down

# WARNING: this also deletes the PostgreSQL volume
docker compose down -v
```

### Updating the source later

Keep your server `.env` file. Replace/pull the source and run:

```bash
docker compose up -d --build
```

The one-shot `migrate` service applies migrations before the web, poller, and expiry services are started. Never run `docker compose down -v` during a normal update.

### HTTPS later

The IP-only example uses HTTP, therefore `SECURE_COOKIES=0` and `SECURE_SSL_REDIRECT=0`. For a real public deployment, put the web service behind HTTPS with your domain, then update:

```dotenv
ALLOWED_HOSTS=movies.example.com
CSRF_TRUSTED_ORIGINS=https://movies.example.com
PUBLIC_BASE_URL=https://movies.example.com
SECURE_COOKIES=1
SECURE_SSL_REDIRECT=1
```

Do not turn the secure-cookie flags on while you are still accessing the Django admin over plain HTTP, otherwise browser login cookies will not work correctly.

## Changes in this edition

- Removed all five-post viewing/click prerequisites from the user flow and admin UI. Existing `ChannelPost` records and `Channel.require_post_clicks` database columns are kept for safe backwards compatibility but **ignored**. The bot no longer records new `channel_post` clicks. Old signed post-tracking URLs are invalid.
- Short, context-specific user prompt. Only buttons for **unfinished** channel joins and Instagram page opens appear. A new check edits the existing bot message instead of posting a second checklist.
- The Instagram button reads `📷 فالو کردن <name>` / `Follow <name>`. Tapping it opens a signed redirect which **records only the link visit** and sends the user straight to the Instagram URL (no extra confirmation page). The Bot API **cannot verify** a real follow/like. A URL preview or shared signed URL could also count as a visit; do not advertise this as verification.
- Telegram `getChatMember` statuses `creator`, `administrator`, `member` and `restricted` + `is_member=True` count as joined. Lookup exceptions are now shown separately from missing membership, and do **not** falsely accuse a channel admin of not joining. Membership is rechecked before each delivery; no bypass is provided.
- Added `diagnose_membership` command to check bot admin rights, channel ID, and the **personal user ID** used for verification.

## Run locally on Ubuntu (no Docker required)

Prerequisites: Python 3.12+, access to Telegram Bot API, an existing channel and bot created with BotFather. Open a terminal in the folder containing `manage.py`:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
# For a new install only; if .env exists, keep it and edit in place:
cp -n .env.example .env
nano .env
mkdir -p db
python manage.py migrate
python manage.py check
python manage.py createsuperuser  # Only if you don't have one already
python manage.py test backend.apps.cinema
```

Set `BOT_TOKEN_BOT01` (a newly issued secret token), then register `BotAccount.key=bot01`, `username=<ACTUAL BOT USERNAME, WITHOUT @>` in Django Admin. The bot's username is **not** the channel username. `BOT_USERNAME` and `TELEGRAM_BOT_TOKEN` are legacy single-bot mode settings and can stay empty in multi-bot mode. Register extra bots as `bot02` / `BOT_TOKEN_BOT02` etc. A bot assigned to a film must be an admin of the central channel, film channel, and any other required channel for reliable member checks. It must have access to media source messages too.

Open **three terminal windows**, activate `.venv` in each, and run:

```bash
python manage.py runserver 127.0.0.1:8000   # terminal 1: Django admin and link redirects
python manage.py bot_polling --all            # terminal 2: one stream per active registered bot
python manage.py expire_media                 # terminal 3: delete delivered media ~30 s later
```

Or test just one bot with `python manage.py bot_polling --bot bot01` instead of `--all`. Do NOT run both for the same bot token. Restart the poller after modifying bot registrations or token environment variables. Django Admin: `http://127.0.0.1:8000/admin/`.

**Important for local testing:** `PUBLIC_BASE_URL=http://127.0.0.1:8000` is reachable from a browser running on the *same computer*, not from Telegram on your phone or another user's device. To test Instagram-click tracking across devices, point `PUBLIC_BASE_URL` at a publicly reachable HTTPS endpoint serving this Django project. Do not expose Django's debug development server or your admin publicly in production.

## Create a film

1. Add a **central** Channel (`is_central=True`), with Telegram's actual negative numeric chat ID and a valid join URL. Only **one** channel can be central.
2. Add a different Channel for the film (`is_central=False`). The dedicated channel cannot be the central channel. Add the assigned bot as administrator of **both** channels.
3. In Films add title, slug, assigned bot (or leave bot blank for a once-only random assignment), dedicated channel and any additional *optional* required channels. Do not add the same channel twice; central and dedicated are already required automatically.
4. Upload your licensed film media to a channel where its assigned bot can access it or send the media directly to the assigned bot as an authorized admin. Media sources are recorded automatically. Link sources in the Film Assets inline in Films. `STORAGE_CHAT_ID` may be used for a shared storage channel (all delivering bots need access).
5. Save the film and copy its unique link from the Films listing. Post it to the central channel or use the admin action to publish selected films.
6. User presses Start, joins **only outstanding channels**, opens the Instagram link buttons (if configured), presses `بررسی و دریافت`, receives media, and the separate expiration worker attempts deletion after the configured TTL.

## Why does the channel owner show as not joined?

Telegram's `getChatMember` normally returns `creator` for a channel owner and `administrator` for an admin; **both count as joined**. Check that the **bot whose link you opened** is an admin in that exact channel, and that your personal Telegram ID (not bot ID, channel ID, or different Telegram account ID) is the one used in the bot session. A wrong channel ID or Telegram API failure must not be interpreted as a missing membership. Use:

```bash
python manage.py diagnose_membership --bot bot01 --channel=-1001234567890 --user=YOUR_PERSONAL_USER_ID
```

Use your own actual channel ID and personal user ID, not example values. This prints the bot's own channel status and the user's status but **never prints tokens**. If the user status is `creator` or `administrator` yet the bot screen still shows an issue, check whether the **central channel or another required channel is missing or misconfigured**, and ensure `is_central=True` is set on exactly one channel. A film needs **two distinct channels** (central + dedicated). If a lookup fails, the bot shows an API verification message rather than `not joined`.

## Security and deployment

Do not include `.env`, database files, credentials or virtualenv in source ZIPs or Git. When upgrading **copy the new source over the old project while keeping your existing `.env` and `db/cinema.sqlite3` unchanged**; then run `python manage.py migrate` and restart all three processes. Never start a new empty DB when you intended to retain existing film/admin records. Revoke any BotFather token shared in a screenshot or message, rotate exposed proxy credentials and Django secret key, and update `.env` with replacements. Rotating the Django secret key may invalidate current admin sessions and old signed redirect URLs.

Never rely on deletion of Telegram messages to prevent a user saving a film; distribute only media you are authorized to share. The number of bots does not guarantee immunity from rate limits or restrictions. The Bot API can't verify an Instagram follow, and a click is not proof of following.
