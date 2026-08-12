# ZIMA Platform - Production Implementation Plan

> **This is a forward-looking roadmap doc, internal-only.** For the actual
> current state of the codebase (what's real, what's tested, what's still
> broken/missing), read `README.internal.md` — that file is kept honest
> turn by turn; this one is the longer-range plan and gets updated less
> often. The checkmarks below were rewritten to reflect where things
> actually stand as of the storage/caching/Discord-hooking pass, not the
> original aspirational draft.

## Current State Analysis

### Existing Components
- ✅ FastAPI backend with **real** Discord OAuth2 + dev-token auth (was mock)
- ✅ Neurotype matching algorithm (10 neurotypes, compatibility matrix) — plus a
  content-fingerprinted cache layer (`MatchScoreCache`) as of this pass
- ✅ PostgreSQL models (profiles, connections, projects, orgs, resources,
  messages, events, language entries, role grants, quest completions,
  consent/deletion audit trail, match-score cache, profile stats cache) —
  one canonical schema, real Alembic migrations
- ⚠️ React frontend (`src/frontend/`) — still targets the pre-rebuild mocked
  API shape; not yet rebuilt against the real backend (next planned phase)
- ✅ Discord bot (discord.js, repo root) — onboarding is real and working;
  a second, unwired Python bot also exists (`src/bot/`) and its fate is an
  open decision, see README.internal.md
- ✅ Demo HTML files (zima-globe.html, zima2.html) — live, deployed via Vercel
- ✅ Docker compose setup — rewritten this pass (previous version's bot
  Dockerfile pointed at a directory with no actual bot in it)
- ✅ Real test suite (49 tests, pytest against a live Postgres instance, not
  mocks) — the original test structure existed but had import-chain bugs
  that meant it silently never actually ran

### Missing Features

#### Phase 1: Authentication & Security (Priority)
- [x] Discord OAuth2 integration (replace mock auth)
- [x] Environment variable validation (`src/core/config.py`)
- [ ] Rate limiting with Redis — `slowapi`/`redis` are in requirements.txt,
      not wired into any route yet
- [ ] Input validation with Pydantic — routes currently accept `Dict[str, Any]`
      bodies validated by hand in the service layer, not typed Pydantic models
- [x] Security headers and CORS hardening (CORS is settings-driven; see
      nginx.conf for the security headers on the frontend's reverse proxy)

#### Phase 2: Database & Models
- [x] Add pgvector extension for embeddings (column exists — `profiles.embedding`)
- [x] Create Organization model
- [x] Create Resource model
- [x] Create Message model
- [x] Create LanguageEntry model
- [x] Add embedding column to Profile — **column exists but is never
      populated or queried**; `search_profiles` is plain ILIKE, not vector
      search. This is real, tracked debt, not "done."
- [x] Alembic migrations for new schema

#### Phase 3: AI Integration
- [ ] Sentence-transformers for embeddings (all-MiniLM-L6-v2)
- [ ] Gemini Flash integration for search clarification
- [ ] Profile summarization with LLM
- [ ] Vector search endpoint
- [ ] Hybrid search (keyword + vector)
- [ ] Prompt caching

#### Phase 4: Backend Endpoints
- [ ] `/api/v1/auth/discord` - OAuth2 flow
- [ ] `/api/v1/organizations` - CRUD
- [ ] `/api/v1/projects` - CRUD with join functionality
- [ ] `/api/v1/connections` - Full CRUD
- [ ] `/api/v1/messages` - Messaging system
- [ ] `/api/v1/resources` - Directory with voting
- [ ] `/api/v1/language-map` - Word frequency analysis
- [ ] `/api/v1/events` - Event management
- [ ] `/api/v1/match/explore` - Enhanced search

#### Phase 5: Frontend Conversion
- [ ] Convert zima-globe.html to React components
- [ ] Convert zima2.html to React components
- [ ] Replace mock data with real API calls
- [ ] Implement authentication flow
- [ ] Create pages: Home, Search, Profiles, Projects, Directory, Events, Dashboard
- [ ] Integrate 3D globe with globe.gl
- [ ] Implement message UI

#### Phase 6: Background Jobs
- [ ] Language map analysis (daily cron)
- [ ] Embedding updates on profile changes
- [ ] Cache warming

#### Phase 7: Production Readiness
- [ ] Redis caching layer
- [ ] Rate limiting
- [ ] Gunicorn + Uvicorn production setup
- [ ] Nginx configuration
- [ ] Monitoring endpoints
- [ ] Logging configuration
- [ ] Error tracking

## Implementation Timeline

### Week 1: Foundation & Authentication
- Day 1-2: Discord OAuth2 implementation
- Day 3: Database migrations with pgvector
- Day 4: New models and Alembic migrations
- Day 5: Testing and validation

### Week 2: AI & Search
- Day 6-7: Embedding integration
- Day 8: Gemini Flash LLM integration
- Day 9: Vector search endpoints
- Day 10: Hybrid search implementation

### Week 3: Backend Endpoints
- Day 11-12: Organizations, Projects, Connections endpoints
- Day 13: Messages and Resources endpoints
- Day 14: Language map and Events endpoints
- Day 15: Testing all endpoints

### Week 4: Frontend
- Day 16-17: Convert HTML demos to React
- Day 18-19: API integration
- Day 20: Authentication flow

### Week 5: Production & Polish
- Day 21: Redis integration
- Day 22: Rate limiting and caching
- Day 23: Docker production setup
- Day 24: Monitoring and logging
- Day 25: Final testing and deployment

## Technical Decisions

### Authentication
- Use `discord-oauth2` package for OAuth2 flow
- Store Discord tokens securely
- JWT for API authentication
- Session management with Redis

### AI Integration
- Local embeddings with `sentence-transformers/all-MiniLM-L6-v2`
- Gemini Flash for LLM tasks (cheap and fast)
- Prompt caching to reduce costs
- Limit to 1-2 LLM calls per search

### Database
- PostgreSQL with pgvector extension
- SQLAlchemy ORM
- Alembic for migrations
- Indexes on frequently queried columns

### Frontend
- Next.js for SSR and routing
- React Query for data fetching
- Zustand for state management
- Tailwind CSS for styling
- globe.gl for 3D visualizations

### Deployment
- Docker Compose with separate services
- Gunicorn + Uvicorn for FastAPI
- Nginx reverse proxy
- Redis for caching and rate limiting

## Testing Strategy

### Unit Tests
- Neurotype matcher (existing + new embedding logic)
- Profile manager (all CRUD operations)
- New endpoint handlers
- Authentication flow

### Integration Tests
- Search flow (keyword + vector)
- Connection workflow
- LLM integration (mocked)
- OAuth2 flow

### End-to-End Tests
- User onboarding journey
- Search and connect flow
- Project creation and joining
- Messaging between users

## Risk Assessment

### High Risk
- Discord OAuth2 implementation complexity
- LLM cost management
- Performance of vector search at scale

### Medium Risk
- Frontend conversion from HTML demos
- Real-time messaging implementation
- Background job reliability

### Low Risk
- Additional CRUD endpoints
- Database migrations
- UI component creation

## Success Metrics

1. All authentication flows working with Discord OAuth2
2. Vector search returning relevant results
3. LLM calls limited to budget
4. Frontend matching demo designs
5. All tests passing
6. Production deployment successful
7. Response times under 500ms for all endpoints
