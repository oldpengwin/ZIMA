# ZIMA — Internal / Private README

**Do not include this file (or `REPOSITORY_SUMMARY.md`, or `IMPLEMENTATION_PLAN.md`)
in anything public-facing.** `README.md` is the public one — this is the
honest internal status doc: what's real, what's still broken, what needs a
decision from Frost before anyone builds on it, and the production
checklist. Written the way the project's conduct doctrine asks for: no
inflated claims, gaps stated as gaps, not silently dropped.

---

## Honest current state

Two engineering passes have been done so far, both on the `backend-rebuild`
branch, both delivered as uncommitted working-tree changes (not pushed —
review and commit when ready).

**Pass 1 — backend rebuild.** The two previously-disconnected/broken
backends (a fully-mocked FastAPI app and a raw-psycopg2 `ProfileManager`)
were unified into one canonical Postgres schema, real Discord OAuth2 auth,
and a real, tested account-deletion/data-export system (the actual reason
for building a real seeded userbase instead of frontend mock data — so
"delete this user without corrupting anyone else's data" is something that
can be tested against, not asserted).

**Pass 2 — storage/caching/Discord-hooking.** An AcousticBrainz-style
derived-data cache (`MatchScoreCache`, `ProfileMatchStats` — see the
docstring above `MatchScoreCache` in `src/database/models.py`) cut match
scoring from "recompute every candidate on every request" to "compute once
per pair, reuse until either profile or the algorithm changes" (~4x on the
seeded dataset). The Node bot and Python backend, which previously only
agreed on a DB schema and could never cause an effect in each other's
world, now have two narrow, real integration points (`src/core/
discord_client.py`, `src/services/role_service.py`) — see that pass's
delivery message for the full writeup.

**Pass 3 — this one — production-readiness audit + Docker/CI fixes + the
public/private README split** you're reading right now. See the file-by-
file table below and the "Fixed this pass" section after it.

49 backend tests pass against a real Postgres instance (not mocks) as of
this pass — `python -m pytest tests/backend/` from the repo root, after
`alembic upgrade head`.

## File-by-file: what's needed for production, what isn't

Legend: **KEEP** = production code, in good shape. **KEEP (gap)** =
production code, needed, but has a known real gap noted. **NOT YET** =
exists, not production-ready, has a stated next step. **DECISION NEEDED** =
don't touch without Frost's input — see the note. **REMOVE** = recommend
deleting; flagged rather than deleted here (the delivery tool that writes
these files to your machine can't delete files — see "Manual cleanup
needed" below).

### Backend (Python) — production path

| Path | Status | Notes |
|---|---|---|
| `src/main.py` | KEEP | Entry point. Fixed this pass: the frontend static-file mount path was wrong (`frontend/build` instead of `src/frontend/build`) and silently no-op'd. |
| `src/api/routes.py` | KEEP | All real endpoints, backed by the service layer. `DELETE /admin/users/{id}` has no real role-based auth yet — logged loudly on every call, not silently shipped; needs real authz before this endpoint is exposed to anyone but you. |
| `src/core/config.py` | KEEP | Fails loudly in production if `SECRET_KEY`/`DATABASE_URL` are missing/placeholder. |
| `src/core/auth.py` | KEEP | Real Discord OAuth2. `/auth/dev-token` is hard-disabled outside `ENVIRONMENT=production`-is-false — confirm this is actually set correctly wherever you deploy, since a dev backdoor reachable in prod is a real vulnerability, not a theoretical one. |
| `src/core/discord_client.py` | KEEP | Best-effort Python→Discord push (role revoke, DMs). No-ops safely (logged) if `DISCORD_BOT_TOKEN`/`DISCORD_TOKEN` isn't set. |
| `src/core/neurotype_matcher.py` | KEEP | The scoring algorithm. Two real bugs fixed in pass 1 (missing self-affinity entries, constructor rejecting empty lists). |
| `src/core/profile_manager.py` | **DECISION NEEDED** | Deprecated raw-SQL profile CRUD, superseded by `src/services/profile_service.py`. Kept only because `src/bot/cogs/matching.py` still imports it — see that row. |
| `src/database/models.py` | KEEP | Canonical schema. See its module docstring for the full reconciliation history. |
| `src/db/session.py` | KEEP | Connection pooling (`pool_size=5, max_overflow=10`) — fine for a single-instance deploy; revisit if you run multiple API replicas. |
| `src/services/*.py` (all 7) | KEEP | profile/connection/project/matching/privacy/stats/role — the real business logic. All exercised by `tests/backend/`. |
| `migrations/versions/*.py` | KEEP | Two real migrations, both applied and tested (`alembic upgrade head` / `downgrade -1` / `upgrade head` round-tripped clean in this pass). |
| `scripts/seed_data.py` | KEEP (gap) | **Do not run this against a production database** — it's a synthetic-userbase generator for dev/testing, not a seed script meant to coexist with real signups. There's no guard in the script itself preventing that; add one (an `ENVIRONMENT` check that refuses to run when `production`) before this is a real risk instead of a theoretical one. |
| `requirements.txt`, `alembic.ini`, `conftest.py` | KEEP | — |
| `tests/backend/*.py` | KEEP, except one | 49 tests, all real (query a live Postgres, no mocking of the DB layer). `test_profile_manager.py` tests the deprecated module and should be deleted — see "Manual cleanup needed." |

### Discord bot(s) — production path

| Path | Status | Notes |
|---|---|---|
| `package.json`, `src/index.js`, `src/config.js`, `src/register-commands.js` | KEEP | The real, working bot (discord.js, gateway client). |
| `src/handlers/*.js`, `src/roles/roleManager.js`, `src/db/supabase.js` | KEEP | — |
| `src/features/onboarding/{components,flow,constants}.js` | KEEP | Onboarding flow — real, tested by hand against a live server in earlier work. |
| `src/features/onboarding/constants.jsx` | **REMOVED** | Was a misplaced, unrelated script with a hardcoded API key — see the security section at the top. Deleted from the working tree this pass. |
| `src/bot/cogs/matching.py`, `src/bot/` | **DECISION NEEDED** | A second, entirely separate Discord bot implementation (discord.py) that nothing in this repo actually runs — no entrypoint loads this cog. Duplicates onboarding, adds matching commands the real bot doesn't have. Marked with a loud deprecation docstring this pass, not deleted. **Needs your call**: port its command ideas onto the real (discord.js) bot, stand it up as a genuine second running process, or delete it outright. Whichever you pick, `src/core/profile_manager.py` (above) rides along with it. |

### Frontend — explicitly not production-ready yet, by design

| Path | Status | Notes |
|---|---|---|
| `src/frontend/**` | NOT YET | Create React App scaffold built against the pre-rebuild, mocked API shape. Per your own stated priority order (backend → data pipeline → frontend), this is the next phase, not started. Building against it today means building against endpoints/response shapes that no longer match `src/api/routes.py`. |
| `tests/frontend/test_api_client.js` | NOT YET | References `vitest`, which isn't a `src/frontend` dependency (that project uses CRA/Jest), and lives outside CRA's default test discovery path. Non-functional as configured; will need fixing as part of the frontend rebuild, not before. |
| `demo/*.html` (4 files) | KEEP | Actively deployed — `vercel.json`'s `outputDirectory` points here. This is your current live public-facing preview, not a throwaway prototype. Keep serving it until the real frontend replaces it. |
| `vercel.json` | KEEP | Matches the above. |

### Docker / deployment — fixed this pass

| Path | Status | Notes |
|---|---|---|
| `Dockerfile.backend` | FIXED | Was Python 3.9, ran as root, no migration step, plain `uvicorn` (no multi-worker). Now: 3.11, non-root user, `docker-entrypoint.backend.sh` runs `alembic upgrade head` before serving, `gunicorn` + `uvicorn` workers (both already in `requirements.txt`, neither was actually being used), a `HEALTHCHECK`. |
| `docker-entrypoint.backend.sh` | NEW | See above. |
| `Dockerfile.bot` | FIXED (was broken) | **This previously pointed at `src/bot/`** — the dead Python cog directory with no `package.json` and no entrypoint at all. `COPY src/bot/package*.json ./` would fail the instant this was actually built. Now builds the real bot from the repo root. |
| `Dockerfile.frontend` | KEEP (as-is, flagged) | Structurally fine; builds the not-yet-rebuilt frontend — see the Frontend section above. Nothing here needs to change once the real frontend replaces `src/frontend/` in place. |
| `docker-compose.yml` | FIXED | `bot`'s `env_file` pointed at `src/bot/.env`, which doesn't exist — now reads the same root `.env` as the API. `db`'s port is no longer published to the host by default (unnecessary attack surface). Added a real Postgres healthcheck and made `api` wait on it (`depends_on: condition: service_healthy`) instead of just "container started, maybe not accepting connections yet." `pgadmin` moved behind a `dev` compose profile so `docker compose up` doesn't start an admin UI with default creds by default. `ENVIRONMENT` set explicitly instead of relying on the `NODE_ENV` fallback. Validated with `docker compose config` (this sandbox has no Docker daemon, so an actual `docker compose build`/`up` could not be run here — do that before trusting this fully). |
| `nginx.conf` | KEEP | Fine as-is; paired with the not-yet-rebuilt frontend, will keep working once that's replaced. |
| `.github/workflows/ci-cd.yml` | FIXED | The backend test job ran `cd src` before `pytest` — the real tests live in `tests/backend/` at the repo root, so this job never actually found them. Combined with no `alembic upgrade head` step, every test's schema-check fixture would have **skipped** (not failed) — meaning this pipeline could report a clean "0 failed" while testing nothing at all. Both fixed: correct working directory, migration step added, Python bumped to 3.11. The `build-docker` job's bot image build would also have failed outright once actually run (see `Dockerfile.bot` above) — fixed by the Dockerfile fix, no workflow change needed there. |
| `.gitignore` | FIXED | Was missing `venv/`, `__pycache__/`, `.pytest_cache/`, coverage output, and frontend build output — meaning a `git add .` today would have picked up hundreds of generated files. Expanded. |

### Docs

| Path | Status | Notes |
|---|---|---|
| `README.md` | REWRITTEN, public | Accurate as of this pass — no aspirational claims about features that don't exist. |
| `README.internal.md` | NEW, this file | Private. |
| `REPOSITORY_SUMMARY.md` | SUPERSEDED | Its content is folded into this file; it's now a short pointer here so nothing that already links to it 404s. |
| `IMPLEMENTATION_PLAN.md` | KEPT, internal | Forward-looking roadmap (phases 3–7 are genuinely not started). Its "current state" checklist at the top was updated to match reality this pass; the roadmap below it is unchanged and still a reasonable plan. |
| `Archetypes.md` | KEEP, public-safe | Content reference for the 10 archetypes — already effectively public (drives the `/neurotypes` endpoint's descriptions). **It exists on your machine but was never committed to git** (not in any commit, not gitignored either — just untracked). `git add Archetypes.md` if you want it version-controlled. |

### Legacy / recommend removal

| Path | Status | Notes |
|---|---|---|
| `_legacy_serverless/` | REMOVE | Its own `README.txt` already says "UNUSED... Safe to delete." Agreed — nothing references it. |
| `tests/backend/test_profile_manager.py` | REMOVE | Tests the deprecated `profile_manager.py`. Flagged for manual deletion in pass 1 too — please confirm this one's actually gone; the delivery tool that writes files to your machine cannot delete files, only write them, so this has to be a manual `rm`/delete on your end. |

### Manual cleanup needed (the delivery tool can only write files, not delete them)

- `rm tests/backend/test_profile_manager.py` (flagged twice now — please confirm)
- `rm src/features/onboarding/constants.jsx` if it's still present locally (removed from the delivered set this pass, but your working copy needs the same deletion applied by hand) — **and see the security section above about the key inside it**
- `rm -rf _legacy_serverless/` (or keep it if you have a reason to — its own docs say it's safe to remove)

## Deployment checklist (before this goes anywhere near real users)

1. Rotate the leaked key (see top of this file) — do this first, independent of everything else.
2. `cp .env.example .env` and fill in real values — especially `SECRET_KEY`
   (must not be the placeholder), `DATABASE_URL` (use `db` as the host if
   running via `docker compose`, `localhost` if running the API directly —
   see the comment in `.env.example`), and the Discord OAuth2 credentials.
3. `alembic upgrade head` (or let `docker-entrypoint.backend.sh` do it on
   container start).
4. Do **not** run `scripts/seed_data.py` against this database — see its row
   in the table above.
5. Set `ENVIRONMENT=production` wherever the API and bot actually run. This
   is what disables the `/auth/dev-token` backdoor and enables strict config
   validation — confirm it's actually set, don't assume the default.
6. Resolve the `src/bot/` decision (table above) before anyone tries to run
   both bots, or continues building Discord-side features on the dead one.
7. Give `DELETE /admin/users/{id}` real role-based authorization before it's
   reachable by anyone other than you directly.
8. Run an actual `docker compose build && docker compose up` somewhere with
   a real Docker daemon — this pass's compose/Dockerfile fixes were
   validated with `docker compose config` (schema-valid) but this sandbox
   has no daemon to actually build/run against, so a real build hasn't
   happened yet.
9. Frontend: still the pre-rebuild scaffold — plan to replace `src/frontend/`
   in place per the earlier agreed priority order before pointing real
   traffic at it.

See also project memory: `zima_codebase_audit.md` (kept in sync with each
pass), `zima_hopamine_vision.md` (product/design spec), `atwin_conduct_doctrine.md`
(the working doctrine applied across all of this).
