-- ============================================================================
-- ZIMA — Row-Level Security (RLS) hardening.  DEFENSE IN DEPTH.  MANUAL APPLY.
-- ============================================================================
--
-- Context: the Discord bot no longer connects to Supabase with a service-role
-- key (it now writes through the Python API). So the only intended DB client is
-- the backend, which connects with a PRIVILEGED role (table owner / service
-- role) that BYPASSES RLS. Enabling RLS therefore locks out any *other* path —
-- e.g. a leaked Supabase `anon`/`authenticated` key — which is exactly the
-- defense-in-depth the audit asked for.
--
-- ┌──────────────────────────────────────────────────────────────────────────┐
-- │ ⚠️  DO NOT apply this blindly in production.                               │
-- │                                                                           │
-- │ RLS with no permissive policy = DENY-ALL for any role that does not       │
-- │ bypass RLS. If your backend's DATABASE_URL role is NOT the table owner /   │
-- │ a bypass role, this will break the API. VERIFY FIRST:                     │
-- │                                                                           │
-- │   SELECT current_user, rolbypassrls                                        │
-- │     FROM pg_roles WHERE rolname = current_user;                            │
-- │                                                                           │
-- │ On Supabase, the pooled `postgres`/owner connection and `service_role`     │
-- │ bypass RLS; `anon` and `authenticated` do not. Point the backend at a      │
-- │ bypass role (it already is, in a standard Supabase setup), confirm the     │
-- │ test query above, THEN apply this in the Supabase SQL editor.             │
-- └──────────────────────────────────────────────────────────────────────────┘
--
-- Effect: every public table gets RLS enabled with no permissive policy, so
-- non-bypass roles can read/write nothing. If you later want a Supabase client
-- key to read specific PUBLIC data directly (bypassing the API), add narrow
-- SELECT policies per table — but note the API already exposes public-safe
-- reads (GET /neurotypes, /network) without leaking discord_id, so you usually
-- don't need to.

DO $$
DECLARE
    t text;
BEGIN
    FOR t IN
        SELECT tablename FROM pg_tables WHERE schemaname = 'public'
    LOOP
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY;', t);
        -- Belt-and-suspenders: FORCE makes even the table owner subject to RLS.
        -- Left commented on purpose — enabling it means you MUST define explicit
        -- policies for the backend role or you lock yourself out entirely.
        -- EXECUTE format('ALTER TABLE public.%I FORCE ROW LEVEL SECURITY;', t);
    END LOOP;
END $$;

-- To undo:
--   DO $$ DECLARE t text; BEGIN
--     FOR t IN SELECT tablename FROM pg_tables WHERE schemaname='public' LOOP
--       EXECUTE format('ALTER TABLE public.%I DISABLE ROW LEVEL SECURITY;', t);
--     END LOOP;
--   END $$;
