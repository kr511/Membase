-- ============================================================================
-- MemBase database schema
--
-- Paste this file into the Supabase SQL Editor (Dashboard -> SQL Editor)
-- and run it once. All statements are idempotent — re-running is safe.
--
-- The backend is zero-knowledge: this schema only ever stores the AES-GCM
-- ciphertext (base64) and the embedding vector computed client-side.
-- ============================================================================

-- 1. Enable the pgvector extension.
create extension if not exists vector;

-- 2. Memory table: one row per encrypted memory chunk.
create table if not exists public.memories (
    id                uuid        primary key default gen_random_uuid(),
    user_id           text        not null,
    encrypted_content text        not null,       -- base64(nonce || AES-GCM ciphertext)
    embedding         vector(384) not null,       -- e.g. all-MiniLM-L6-v2, computed client-side
    created_at        timestamptz not null default now()
);

-- 3. Indexes.

-- Tenant isolation lookups.
create index if not exists idx_memories_user_id
    on public.memories (user_id);

-- HNSW index for ultra-fast approximate nearest-neighbour search
-- with cosine distance.
create index if not exists idx_memories_embedding_hnsw
    on public.memories
    using hnsw (embedding vector_cosine_ops);

-- 4. Cosine similarity search, callable via PostgREST RPC.
--    similarity = 1 - cosine_distance; rows below match_threshold are dropped.
create or replace function public.match_memories(
    query_embedding vector(384),
    match_threshold float,
    match_count     int,
    owner_id        text
)
returns table (
    id                uuid,
    user_id           text,
    encrypted_content text,
    similarity        float,
    created_at        timestamptz
)
language sql
stable
as $$
    select
        m.id,
        m.user_id,
        m.encrypted_content,
        1 - (m.embedding <=> query_embedding) as similarity,
        m.created_at
    from public.memories m
    where m.user_id = owner_id
      and 1 - (m.embedding <=> query_embedding) >= match_threshold
    order by m.embedding <=> query_embedding
    limit match_count;
$$;
