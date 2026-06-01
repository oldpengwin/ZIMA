-- Run this in the Supabase SQL editor for your project.

create table if not exists public.profiles (
  id uuid primary key default gen_random_uuid(),
  discord_id text not null unique,
  discord_username text not null,
  display_name text not null,
  location text,
  skills text[] default '{}',
  bio text,
  links text,
  onboarding_completed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists profiles_discord_id_idx on public.profiles (discord_id);

-- Quest / contribution role history (for future gamification)
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

-- Optional: track quest progress later
create table if not exists public.quest_completions (
  id uuid primary key default gen_random_uuid(),
  discord_id text not null,
  quest_key text not null,
  completed_at timestamptz not null default now(),
  metadata jsonb default '{}'::jsonb
);

create unique index if not exists quest_completions_unique
  on public.quest_completions (discord_id, quest_key);
