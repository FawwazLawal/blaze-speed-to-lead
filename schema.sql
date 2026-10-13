-- Supabase table for the speed-to-lead pipeline.
-- Paste this whole file into the Supabase SQL editor and hit Run.

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

-- Row Level Security is intentionally left OFF for this demo: the project is a
-- throwaway, the only client is a localhost script holding the anon key, and no
-- real person's data is ever stored. In production this table would have RLS on
-- with writes restricted to a service role. Noted in the README as well.
