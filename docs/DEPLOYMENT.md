# ZIMA — Deployment & Operator Guide

Everything needed to stand ZIMA up from a clean machine. If you only read one
section, read **Quick deploy (Docker)** and **Environment variables**.

The stack is four processes:

| Service    | What it is                            | Port (host) |
|------------|---------------------------------------|-------------|
| `api`      | FastAPI backend (Python 3.11)         | 8000        |
| `bot`      | Discord bot (Node.js / discord.js)    | —           |
| `frontend` | React (Vite) SPA                      | 3000        |
| `db`       | PostgreSQL 16                         | (internal)  |

The `api` and `bot` are two processes sharing **one** `.env` at the repo root.
The `api` container runs `alembic upgrade head` automatically on startup
(`docker-entrypoint.backend.sh`) — you do not migrate by hand under Docker.

No PostgreSQL extensions are required (matching is pure archetype/skill math).

---

## 1. Discord application setup (do this first)

You need one Discord application; the bot and the API's OAuth login are the
same app.

1. **Create the app**: <https://discord.com/developers/applications> → *New
   Application*.
2. **Bot**: *Bot* tab → *Reset Token* → copy it → this is `DISCORD_TOKEN` /
   `DISCORD_BOT_TOKEN` (same value, both keys accept it).
3. **Application ID**: *General Information* → *Application ID* →
   `DISCORD_APPLICATION_ID`. This is also the `DISCORD_CLIENT_ID`.
4. **Client secret** (for web login): *OAuth2* → *Client Secret* →
   `DISCORD_CLIENT_SECRET`.
5. **OAuth redirect**: *OAuth2* → *Redirects* → add exactly your
   `DISCORD_REDIRECT_URI` (e.g. `https://api.yourdomain.com/api/v1/auth/discord/callback`).
6. **Invite the bot** to your server: *OAuth2* → *URL Generator* → scopes
   `bot` + `applications.commands`; bot permissions *Manage Roles*, *Send
   Messages*, *View Channels*. Open the generated URL and add it to the server.
7. **IDs** (enable Developer Mode in Discord to copy IDs):
   - `DISCORD_SERVER_ID` — right-click the server icon → *Copy Server ID*
   - `ONBOARDING_CHANNEL_ID` — the channel for the onboarding message
   - `VETTED_ROLE_ID` — role granted on completing onboarding
   - `XP_TIER_CONTRIBUTOR_ROLE_ID`, `XP_TIER_BUILDER_ROLE_ID` — optional roles
     applied when a builder crosses an XP level threshold (see §5)

> The bot's own role must be **above** any role it grants in the server's role
> list, or Discord refuses the grant.

---

## 2. Quick deploy (Docker) — recommended

```bash
git clone https://github.com/oldpengwin/ZIMA.git
cd ZIMA
cp .env.example .env
# edit .env — see §3. At minimum for production:
#   ENVIRONMENT, DATABASE_URL, SECRET_KEY, POSTGRES_*, DISCORD_*, BOT_API_KEY,
#   ADMIN_DISCORD_IDS
docker compose up --build -d
```

This builds and starts `api`, `frontend`, `bot`, and `db`. The API waits for
the DB to be healthy, runs migrations, then serves on `:8000`. (`pgadmin` is
dev-only: `docker compose --profile dev up`.)

**Register slash commands once** (and again whenever they change):

```bash
docker compose run --rm bot npm run register-commands
```

**Verify:**

```bash
curl -fsS http://localhost:8000/api/v1/neurotypes >/dev/null && echo "API OK"
docker compose ps        # all services Up; db healthy
docker compose logs -f api bot
```

> **DB credential gotcha:** the `db` service is created with `POSTGRES_USER` /
> `POSTGRES_PASSWORD` / `POSTGRES_DB` from `.env` (defaults `zima` /
> `zima_password` / `zima`). Your `DATABASE_URL` **must use the same user /
> password / db name and host `db`**, e.g.
> `postgresql://zima:zima_password@db:5432/zima`. A mismatch here is the most
> common first-deploy failure (the API can't authenticate to Postgres).

---

## 3. Environment variables

One `.env` at the repo root configures both `api` and `bot`. Full annotated
list is in `.env.example`; the ones that matter for a real deploy:

### Required in production
| Var | Notes |
|-----|-------|
| `ENVIRONMENT` | `production`. Anything unset/unknown **refuses to start** (fail-closed). Compose already forces this for `api`. |
| `DATABASE_URL` | `postgresql://<user>:<pass>@db:5432/<db>` — must match the `POSTGRES_*` below and host `db` under Docker. |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Provision the `db` container. Keep consistent with `DATABASE_URL`. |
| `SECRET_KEY` | Strong random string (`python -c "import secrets;print(secrets.token_urlsafe(48))"`). Production refuses the placeholder. |
| `DISCORD_TOKEN` (= `DISCORD_BOT_TOKEN`) | Bot token; also lets the API push role grants/DMs. |
| `DISCORD_APPLICATION_ID` / `DISCORD_CLIENT_ID` | App ID. |
| `DISCORD_CLIENT_SECRET` | For web OAuth2 login. |
| `DISCORD_REDIRECT_URI` | Must exactly match the redirect registered in the Discord portal. |
| `DISCORD_SERVER_ID` | Your guild ID. |
| `BOT_API_KEY` | Shared secret; the bot sends it as `X-Bot-Key` on `/api/v1/bot/*`. Set the **same** value for api and bot (same `.env`). Empty ⇒ bot endpoints reject everyone. |
| `ADMIN_DISCORD_IDS` | Comma-separated Discord IDs allowed to hit admin endpoints. Empty ⇒ nobody is admin (fail-closed). |

### Recommended
| Var | Notes |
|-----|-------|
| `ALLOWED_ORIGINS` | Comma-separated origins for CORS (your frontend URL). |
| `FRONTEND_URL` | Where the API redirects after login. |
| `ONBOARDING_CHANNEL_ID`, `VETTED_ROLE_ID` | Onboarding flow + vetted role. |
| `XP_TIER_CONTRIBUTOR_ROLE_ID`, `XP_TIER_BUILDER_ROLE_ID` | XP tier roles (§5). Unset ⇒ tier unlock still recorded, Discord role skipped (logged). |
| `RATE_LIMIT_REQUESTS`, `RATE_LIMIT_WINDOW` | Global rate limit (enforced only in production). |

---

## 4. Frontend

The Vite SPA reads `VITE_API_URL` at build time. Point it at your deployed API
and build:

```bash
cd src/frontend
npm install
VITE_API_URL="https://api.yourdomain.com" npm run build   # -> src/frontend/dist
```

Serve `src/frontend/dist` as static files (any static host / CDN / nginx), or
use the `frontend` container in `docker-compose.yml`. In dev, `npm run dev`
proxies `/api` to `localhost:8000` so you don't set `VITE_API_URL` locally.

Publishing the frontend to a public host is the operator's choice; nothing in
this repo publishes it automatically.

---

## 5. XP / gamification config

XP is awarded server-side for onboarding completion, quiz completion, first
project join, and project creation (values/thresholds in
`src/services/xp_service.py`). Crossing a level threshold:

1. records a `RoleGrant` (`source="xp"`), and
2. if the matching `XP_TIER_*_ROLE_ID` is set, applies that Discord role
   directly via the bot token.

If a tier's role ID is unset, the unlock is still recorded but the Discord role
is not applied — that case is logged, never silent. Builders check standing
with `/xp` in Discord or `GET /api/v1/profiles/me/xp` on the web.

---

## 6. Manual (non-Docker) deploy

```bash
# Postgres running and reachable via DATABASE_URL
python -m venv venv && source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
export ENVIRONMENT=production                        # plus the rest of §3
alembic upgrade head
gunicorn src.main:app -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 --workers 4

# Bot (separate process, same .env)
npm install
npm run register-commands       # once
npm start
```

Python **3.11** is the supported runtime (matches the Docker image and the
pinned dependency set). Newer/older minors may not satisfy the pins.

---

## 7. Post-deploy checklist

- [ ] `.env` complete; `ENVIRONMENT=production`; strong `SECRET_KEY`.
- [ ] `DATABASE_URL` matches the `POSTGRES_*` creds and host.
- [ ] `docker compose ps` — all Up, `db` healthy.
- [ ] `curl http://<host>:8000/api/v1/neurotypes` returns the ten archetypes.
- [ ] Slash commands registered (`/quiz`, `/xp`, `/setup-onboarding` appear in Discord).
- [ ] Discord OAuth login round-trips (redirect URI matches the portal exactly).
- [ ] Bot's role sits **above** the roles it grants.
- [ ] `ADMIN_DISCORD_IDS` set; `/api/docs` is disabled in production (it is, by config).
- [ ] Frontend built with the correct `VITE_API_URL` and served.
