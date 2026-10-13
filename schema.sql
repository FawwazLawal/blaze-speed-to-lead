-- Supabase table for the speed-to-lead pipeline.
-- Paste this whole file into the Supabase SQL editor and hit Run.
-- Safe to re-run: every statement is idempotent.

create table if not exists leads (
  id               bigserial primary key,
  received_at      timestamptz not null default now(),

  -- Straight from the Facebook lead-ad payload
  name             text    not null,
  email            text    not null,
  phone            text    not null,
  company          text    not null,
  doors            integer not null,
  message          text    not null,

  -- Filled in by the LLM qualification step
  fit_score        integer,
  reason           text,
  reply            text,

  -- Filled in once the Discord card is delivered
  delivered_at     timestamptz,
  elapsed_seconds  numeric(6,2)
);

-- Row Level Security stays ON, with explicit policies for the anon role.
--
-- The pipeline authenticates with the anon key, so without a policy every
-- insert fails with "new row violates row-level security policy" — which is
-- exactly what happened on the first live run. Granting access explicitly is
-- preferred here over turning RLS off: it is scoped to this one table, it is
-- visible in the schema, and it leaves Supabase's own security linter clean.
--
-- These policies are permissive because this is a throwaway demo project whose
-- only client is a localhost script and whose only row is a fabricated lead. A
-- production version would drop them and write through a service role instead.

alter table leads enable row level security;

drop policy if exists "demo anon insert" on leads;
create policy "demo anon insert" on leads
  for insert to anon with check (true);

drop policy if exists "demo anon select" on leads;
create policy "demo anon select" on leads
  for select to anon using (true);

drop policy if exists "demo anon update" on leads;
create policy "demo anon update" on leads
  for update to anon using (true) with check (true);
