-- Run this in the Supabase SQL editor for your project.
--
-- This schema is now the same canonical schema the Python backend's Alembic
-- migrations generate (see migrations/versions/ and src/database/models.py)
-- — previously this file and the SQLAlchemy models disagreed with each
-- other (different columns, and `links` was `text` here vs `text[]` in
-- Python). The Discord bot only ever writes a subset of these columns
-- (discord_id, discord_username, display_name, location, skills, bio,
-- links, onboarding_completed_at) — every other column is nullable/
-- defaulted so that keeps working unchanged; see
-- src/features/onboarding/flow.js and components.js for the one behavior
-- change this required (links is now parsed into a text[] before writing,
-- via the new parseLinks() helper, instead of being passed through as a
-- raw scalar string).

create extension if not exists vector;
create extension if not exists pgcrypto;

create table if not exists public.profiles (
  id uuid primary key default gen_random_uuid(),
  discord_id text not null unique,
  discord_username text not null,
  display_name text not null,
  location text,
  skills text[] default '{}',
  bio text,
  links text[] default '{}',
  onboarding_completed_at timestamptz,

  -- Richer product/matching fields, filled in later via the web app.
  neurotype text,
  offering text[] default '{}',
  looking_for text[] default '{}',
  projects text[] default '{}',
  is_open boolean not null default true,
  tagline text,
  embedding vector(384),
  vision_2036 text,
  mission text,
  badges text[] default '{}',
  wall_posts text[] default '{}',

  consented_at timestamptz,

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists profiles_discord_id_idx on public.profiles (discord_id);
create index if not exists profiles_neurotype_idx on public.profiles (neurotype);
create index if not exists profiles_is_open_idx on public.profiles (is_open);

-- Quest / contribution role history
create table if not exists public.role_grants (
  id uuid primary key default gen_random_uuid(),
  discord_id text not null,
  role_key text not null,
  granted_at timestamptz not null default now(),
  source text not null default 'onboarding',
  metadata jsonb default '{}'::jsonb
);

create index if not exists role_grants_discord_id_idx on public.role_grants (discord_id);
create unique index if not exists role_grants_discord_role_unique
  on public.role_grants (discord_id, role_key);

create table if not exists public.quest_completions (
  id uuid primary key default gen_random_uuid(),
  discord_id text not null,
  quest_key text not null,
  completed_at timestamptz not null default now(),
  metadata jsonb default '{}'::jsonb
);

create unique index if not exists quest_completions_unique
  on public.quest_completions (discord_id, quest_key);

-- Everything below this line exists in the Python backend's canonical
-- schema (see src/database/models.py) and is created here too so a
-- Supabase-hosted Postgres instance can serve as the single database for
-- both the bot and the FastAPI backend, rather than needing two databases.
-- If you're running the Python backend against its own Alembic-migrated
-- Postgres instance instead, you don't need to run this section — `alembic
-- upgrade head` already creates it.

create table if not exists public.connections (
  id uuid primary key default gen_random_uuid(),
  from_user_id uuid not null references public.profiles(id) on delete cascade,
  to_user_id uuid not null references public.profiles(id) on delete cascade,
  status text not null default 'pending',
  message text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (from_user_id, to_user_id)
);

create table if not exists public.projects (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid references public.profiles(id) on delete set null,
  owner_deleted boolean not null default false,
  title text not null,
  description text,
  neurotypes_needed text[] default '{}',
  skills_needed text[] default '{}',
  status text not null default 'active',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.project_participants (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  profile_id uuid not null references public.profiles(id) on delete cascade,
  role text,
  joined_at timestamptz not null default now(),
  unique (project_id, profile_id)
);

create table if not exists public.organizations (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  mission text,
  location text,
  org_type text,
  roles_open text[] default '{}',
  project_links text[] default '{}',
  email text,
  beta_info text,
  resume_request boolean not null default false,
  trust_score double precision not null default 0.5,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.resources (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  type text,
  category text,
  subcategory text,
  url text not null,
  description text,
  status text not null default 'pending',
  votes integer not null default 0,
  cool integer not null default 0,
  created_at timestamptz not null default now(),
  submitted_by uuid references public.profiles(id) on delete set null
);

create table if not exists public.messages (
  id uuid primary key default gen_random_uuid(),
  from_user_id uuid references public.profiles(id) on delete set null,
  to_user_id uuid references public.profiles(id) on delete set null,
  from_user_deleted boolean not null default false,
  to_user_deleted boolean not null default false,
  content text not null,
  read boolean not null default false,
  created_at timestamptz not null default now()
);

create table if not exists public.events (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  date timestamptz not null,
  location text,
  official boolean not null default false,
  description text,
  contact_email text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- AcousticBrainz-style derived/cached data — see the docstring block above
-- MatchScoreCache in src/database/models.py for the full design rationale.
-- Append-only submission history (never UPDATE a row's score in place;
-- flip the old row's is_current to false and INSERT a new one) plus one
-- promoted, indexed `score` column so hot-path queries (top-N, score >
-- threshold) never have to touch the JSONB breakdown.

create table if not exists public.match_score_cache (
  id uuid primary key default gen_random_uuid(),
  profile_lo_id uuid not null references public.profiles(id) on delete cascade,
  profile_hi_id uuid not null references public.profiles(id) on delete cascade,
  score double precision not null,
  algorithm_version text not null,
  input_fingerprint text not null,
  breakdown jsonb not null default '{}'::jsonb,
  is_current boolean not null default true,
  computed_at timestamptz not null default now()
);

create unique index if not exists ix_match_score_cache_current_pair
  on public.match_score_cache (profile_lo_id, profile_hi_id)
  where is_current;

create index if not exists ix_match_score_cache_lo_current on public.match_score_cache (profile_lo_id, is_current);
create index if not exists ix_match_score_cache_hi_current on public.match_score_cache (profile_hi_id, is_current);
create index if not exists ix_match_score_cache_score on public.match_score_cache (score);
create index if not exists ix_match_score_cache_computed_at on public.match_score_cache (computed_at);

-- Cheap, single-row-read aggregate summary per profile — recomputed
-- on-demand/on a schedule (services/stats_service.py), never inline on a
-- page request. See ProfileMatchStats in src/database/models.py.
create table if not exists public.profile_match_stats (
  profile_id uuid primary key references public.profiles(id) on delete cascade,
  total_connections integer not null default 0,
  total_projects_owned integer not null default 0,
  total_projects_joined integer not null default 0,
  cached_match_count integer not null default 0,
  avg_match_score double precision,
  top_match_profile_id uuid,
  computed_at timestamptz not null default now()
);

create table if not exists public.language_entries (
  id uuid primary key default gen_random_uuid(),
  word text not null,
  definitions jsonb default '{}'::jsonb,
  drift_score double precision not null default 0.0,
  frequency_by_neurotype jsonb default '{}'::jsonb,
  frequency_by_location jsonb default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

-- Privacy / consent / deletion audit trail — see src/services/privacy_service.py
-- for the full deletion policy this schema supports.

create table if not exists public.consent_records (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid references public.profiles(id) on delete set null,
  subject_deleted boolean not null default false,
  consent_type text not null,
  granted_at timestamptz,
  revoked_at timestamptz,
  source text
);

create table if not exists public.deletion_requests (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid not null,
  discord_id text not null,
  requested_at timestamptz not null default now(),
  completed_at timestamptz,
  requested_by text not null default 'self',
  status text not null default 'pending'
);

create table if not exists public.deletion_audit_log (
  id uuid primary key default gen_random_uuid(),
  deletion_request_id uuid not null references public.deletion_requests(id) on delete cascade,
  table_name text not null,
  action text not null,
  rows_affected integer not null default 0,
  executed_at timestamptz not null default now()
);
