# ZIMA

**The Builders Network** — a community platform that connects builders
working on regenerative, solarpunk, and tools-for-sovereignty projects,
matched by skills and by *neurotype*: ten builder archetypes describing how
someone works and what they naturally bring to a project, not a personality
quiz gimmick but the backbone of how matching actually scores compatibility.

Built under the HOPAMINE brand. Onboarding happens on Discord; the web
platform is where matching, projects, and the builder directory live.

## The ten archetypes

| | Archetype | |
|---|---|---|
| 🌱 | **Seedcaster** | *"They plant what others haven't imagined yet."* — regenerative agriculture, food forests, seed saving |
| ⚙️ | **Fabricant** | *"If it doesn't exist, they build it."* — mechanical engineering, fabrication, open-source hardware |
| 🍄 | **Mycelian** | *"They think in networks and grow in the dark."* — biology, biomaterials, fermentation, bioremediation |
| 🏗️ | **Terraformer** | *"They redesign the spaces we inhabit."* — sustainable architecture, passive design, land trusts |
| 💻 | **Developer** | *"They write the tools of sovereignty."* — software, AI/ML, data pipelines, automation |
| 🎨 | **Artisan** | *"They make the future beautiful enough to want."* — visual design, UI/UX, solarpunk aesthetics |
| 📡 | **Chronicler** | *"They make sure the work gets seen."* — storytelling, video, writing, community media |
| 🌿 | **Cultivar** | *"They bridge the lab and the land."* — food science, plant medicine, crop research |
| 🔗 | **Loomkeeper** | *"They hold the network together."* — community building, event production, partnerships |
| 📜 | **Verdant** | *"They change the rules of the game."* — policy, advocacy, circular economics, governance |

## Architecture

```
ZIMA/
├── src/
│   ├── index.js, config.js, features/, handlers/, roles/   # Discord bot (discord.js)
│   ├── api/, core/, database/, db/, services/               # FastAPI backend (Python)
│   └── frontend/                                            # Web app (React) — in active rebuild
├── demo/                # Live prototype pages (deployed via Vercel)
├── migrations/           # Alembic schema migrations
├── supabase/schema.sql   # Same schema, for a Supabase-hosted Postgres
├── scripts/seed_data.py  # Generates a realistic dev/test dataset — not for production use
└── tests/
```

**Backend**: FastAPI + PostgreSQL + SQLAlchemy, Discord OAuth2 for auth,
Alembic for migrations. Matching is deterministic, pure-code scoring — no
LLM calls in the hot path. **Discord bot**: discord.js, handles onboarding
and role management, writes into the same database the API reads from.
**Frontend**: React — currently mid-rebuild against the backend above; the
`demo/` folder is the current live public preview in the meantime.

## Quick start

Prerequisites: Python 3.11+, Node.js 18+, PostgreSQL 16+ (with the
`pgvector` and `pgcrypto` extensions available), Docker (optional).

```bash
git clone https://github.com/oldpengwin/ZIMA.git
cd ZIMA
cp .env.example .env
# edit .env — at minimum set DATABASE_URL and SECRET_KEY
```

**Backend:**

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
python src/main.py
```

API docs are then at `http://localhost:8000/api/docs`.

Want realistic dev data to work against instead of an empty database?

```bash
python -m scripts.seed_data --reset --profiles 300
```

**Discord bot** (shares the same `.env` as the backend):

```bash
npm install
npm start
```

**Frontend** (currently in active rebuild — see the note above):

```bash
cd src/frontend
npm install
npm start
```

**Or everything at once with Docker:**

```bash
docker compose up --build
```

## Testing

```bash
alembic upgrade head          # tests run against a real schema, not mocks
python -m pytest tests/backend/
```

## API surface

| | |
|---|---|
| `GET /api/v1/auth/discord/login` / `/callback` | Discord OAuth2 |
| `POST /api/v1/profiles` · `GET/PUT /profiles/{id}` · `GET /profiles?q=` | Profile CRUD + search |
| `GET /api/v1/profiles/{id}/stats` | Precomputed connection/project/match summary |
| `GET /api/v1/profiles/{id}/roles` | Discord role-grant history |
| `GET /api/v1/match/{user_id}` · `POST /match/request` · `PUT /match/requests/{id}` | Matching + connection requests |
| `POST /api/v1/projects` · `GET /projects` · `POST /projects/{id}/join` | Projects |
| `GET /api/v1/users/me/export` · `DELETE /users/me` | Data export / right-to-erasure |
| `GET /api/v1/neurotypes` | The ten archetypes, machine-readable |

Full interactive docs at `/api/docs` once the server is running.

## Discord bot

- `/setup-onboarding` — posts the onboarding flow in a channel
- Completing onboarding grants the **Vetted** role automatically

## Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests for behavior, not just syntax — this project runs its test
   suite against a real database, not mocks
4. Submit a pull request

## License

MIT

## Status

Backend and data layer are in active use and under test. The web frontend
is mid-rebuild; `demo/` is the current live preview.
