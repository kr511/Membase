-- MemBase: initial schema for zero-knowledge vector memory storage.
--
-- The backend only ever stores the AES-GCM ciphertext (base64) and the
-- embedding vector produced client-side. Plaintext never reaches this table.

-- 1. Enable the pgvector extension.
create schema if not exists extensions;
create extension if not exists vector with schema extensions;

-- 2. Memory table: one row per encrypted memory chunk.
create table if not exists public.memories (
    id                uuid        primary key default gen_random_uuid(),
    user_id           text        not null,
    encrypted_content text        not null,       -- base64(nonce || AES-GCM ciphertext)
    embedding         extensions.vector(384) not null,       -- e.g. all-MiniLM-L6-v2, computed client-side
    created_at        timestamptz not null default now()
);

-- Backend-only access: RLS with no policies means the public anon key
-- sees nothing, while the service_role key (used by the API) bypasses RLS.
alter table public.memories enable row level security;

-- Tenant isolation lookups.
create index if not exists idx_memories_user_id
    on public.memories (user_id);

-- Approximate nearest-neighbour search with cosine distance.
create index if not exists idx_memories_embedding_hnsw
    on public.memories
    using hnsw (embedding vector_cosine_ops);

-- 3. Cosine similarity search, callable via PostgREST RPC.
--    similarity = 1 - cosine_distance; rows below match_threshold are dropped.
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
