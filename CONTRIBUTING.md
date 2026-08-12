# Contributing to ZIMA

Thanks for wanting to build with us. This repo is the private source of truth;
a curated public mirror (`zima-showcase`) is generated from an allowlist, so
not everything here is public.

## Ground rules

- **Security first.** Never commit secrets. `.env` is gitignored — copy
  `.env.example` and fill it locally. If you find a vulnerability, follow
  [`SECURITY.md`](SECURITY.md), don't open a public issue.
- **Truth over polish.** State gaps as gaps. A partial fix with a clear
  `TODO` beats a silent one.
- **Deterministic over magic.** Matching and scoring are pure math, no LLM —
  keep it that way unless generation genuinely adds value.

## Project layout

| Path | What |
|---|---|
| `src/api`, `src/core`, `src/services` | FastAPI backend + business logic |
| `src/quiz`, `src/core/neurotypes.py` | Neurotype typology engine + registry |
| `src/features`, `src/handlers`, `src/roles` | Discord bot (Node / discord.js) |
| `src/database`, `migrations` | SQLAlchemy models + Alembic migrations |
| `demo/` | Public static demos (mirrored) |
| `tests/backend` | Pytest suite (runs against a real Postgres) |

## Development

**Backend**
```bash
cp .env.example .env          # fill in real values; set ENVIRONMENT=development
pip install -r requirements.txt
alembic upgrade head
pytest tests/backend/         # requires a test Postgres
uvicorn src.main:app --reload
```

**Bot**
```bash
npm install
npm run register-commands
npm run dev
```

## Pull request checklist

- [ ] Branches from `main`; PR targets `main`.
- [ ] `pytest tests/backend/` passes (and `python -m pytest tests/backend/test_quiz_engine.py` for pure-logic changes).
- [ ] New/changed API input is validated and cleaned; public responses never leak `discord_id` or other PII.
- [ ] No new dependency unless it's used; no secrets in the diff.
- [ ] DB schema changes ship with an Alembic migration (`upgrade` **and** `downgrade`).
- [ ] New files are classified for the public mirror (`python scripts/classify_public.py --check` is green).
- [ ] Commented the *why*, not just the *what*, where it isn't obvious.

## Style

- Python: standard library first; type hints on public functions; match the
  surrounding module's conventions.
- JS: ES modules, `discord.js` v14 patterns as in `src/features/onboarding`.
- Keep functions small and single-purpose; prefer pushing filters into SQL
  over loading rows and filtering in Python.

## Conduct

Be decent. This is a community for builders — assume good faith, disagree with
mechanism, and keep it constructive.
