-- ============================================================================
-- MemBase — security hardening (from Supabase security advisors)
--
-- Applies on top of schema.sql + api_keys.sql deployments that were created
-- before the hardened base files. Fresh setups using the current base files
-- do not need this migration.
-- ============================================================================

-- 1. The signup trigger function must not be callable via the REST RPC
--    surface (it is SECURITY DEFINER).
revoke execute on function public.handle_new_user() from public;
revoke execute on function public.handle_new_user() from anon;
revoke execute on function public.handle_new_user() from authenticated;

-- 2. Move pgvector out of the exposed public schema.
create schema if not exists extensions;
alter extension vector set schema extensions;

-- 3. Recreate match_memories with a pinned search_path.
drop function if exists public.match_memories(extensions.vector, double precision, integer, text);

create function public.match_memories(
    query_embedding extensions.vector(384),
    match_threshold float,
    match_count     int,
    owner_id        text
)
returns table (
    id                uuid,
    encrypted_content text,
    similarity        float,
    created_at        timestamptz
)
language sql
stable
set search_path = public, extensions
as $$
    select
        m.id,
        m.encrypted_content,
        1 - (m.embedding <=> query_embedding) as similarity,
        m.created_at
    from public.memories m
    where m.user_id = owner_id
      and 1 - (m.embedding <=> query_embedding) >= match_threshold
    order by m.embedding <=> query_embedding
    limit match_count;
$$;
