-- ============================================================================
-- MemBase — complete database schema for the Supabase SQL Editor
--
-- Run this file once (Dashboard -> SQL Editor -> paste -> Run).
-- All statements are idempotent — re-running is safe.
--
-- Zero-knowledge design: only the AES-GCM ciphertext (base64) and the
-- client-side embedding vector are ever stored. Plaintext never arrives here.
-- ============================================================================

-- 1. Enable the pgvector extension (no-op if already active).
create schema if not exists extensions;
create extension if not exists vector with schema extensions;

-- 2. Table expected by app/services/supabase_db.py::insert_memory().
create table if not exists public.memories (
    id                uuid        primary key default gen_random_uuid(),
    user_id           text        not null,
    encrypted_content text        not null,       -- base64(nonce || AES-GCM ciphertext)
    embedding         extensions.vector(384) not null,       -- matches the local embedding model
    created_at        timestamptz not null default now()
);

-- Backend-only access: RLS with no policies means the public anon key
-- sees nothing, while the service_role key (used by the API) bypasses RLS.
alter table public.memories enable row level security;

-- Tenant isolation lookups.
create index if not exists idx_memories_user_id
    on public.memories (user_id);

-- HNSW index for ultra-fast approximate nearest-neighbour search (cosine).
create index if not exists idx_memories_embedding_hnsw
    on public.memories
    using hnsw (embedding vector_cosine_ops);

-- 3. RPC function called by app/services/supabase_db.py::match_memories().
--    similarity = 1 - cosine_distance (<=>); rows below match_threshold drop out.
--    Drop first so the return type can evolve across re-runs.
drop function if exists public.match_memories(extensions.vector, float, int, text);

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
