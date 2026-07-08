-- ============================================================================
-- MemBase — API key provisioning for registered users
--
-- Run this in the Supabase SQL Editor (after schema.sql).
-- Every new auth.users signup automatically receives a personal API key.
-- ============================================================================

-- 1. One API key per authenticated user.
create table if not exists public.user_api_keys (
    id         uuid        primary key default gen_random_uuid(),
    user_id    uuid        unique not null references auth.users (id) on delete cascade,
    api_key    text        unique not null,
    created_at timestamptz not null default now()
);

-- 2. Row Level Security: the browser talks to this table with the public
--    anon key, so users must only ever see THEIR OWN key.
alter table public.user_api_keys enable row level security;

drop policy if exists "Users can read own api key" on public.user_api_keys;
create policy "Users can read own api key"
    on public.user_api_keys
    for select
    to authenticated
    using (auth.uid() = user_id);

-- No insert/update/delete policies: clients cannot mint or alter keys.
-- Rows are created exclusively by the trigger below.

-- 3. Trigger: mint a key like 'mb_live_<32 hex chars>' on every signup.
--    SECURITY DEFINER is required because the auth service inserting into
--    auth.users has no direct grants on public.user_api_keys.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
    insert into public.user_api_keys (user_id, api_key)
    values (
        new.id,
        'mb_live_' || md5(random()::text || clock_timestamp()::text || new.id::text)
    );
    return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
    after insert on auth.users
    for each row
    execute function public.handle_new_user();
