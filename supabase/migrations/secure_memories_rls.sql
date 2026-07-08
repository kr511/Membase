-- ============================================================================
-- MemBase — lock down the memories table
--
-- The memories table is accessed exclusively by the FastAPI backend using
-- the service_role key (which bypasses RLS). Without RLS, PostgREST would
-- expose the table to anyone holding the public anon key.
--
-- Enabling RLS with NO policies means: anon/authenticated see nothing,
-- the backend (service_role) keeps full access. The match_memories()
-- function runs with invoker rights, so RLS applies there too.
-- ============================================================================

alter table public.memories enable row level security;
