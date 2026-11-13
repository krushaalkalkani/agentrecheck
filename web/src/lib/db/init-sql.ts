/**
 * Idempotent schema DDL. Mirrors `schema.ts`.
 *
 * - Local/demo mode (PGlite): applied automatically on first use.
 * - Supabase/Postgres: apply once with `npm run db:init` (or paste into the
 *   Supabase SQL editor).
 */
export const INIT_SQL = `
create table if not exists projects (
  id uuid primary key,
  owner_id text not null,
  name text not null,
  api_key_hash text not null unique,
  api_key_prefix text not null,
  created_at timestamptz not null default now()
);
create index if not exists projects_owner_idx on projects (owner_id);

create table if not exists traces (
  id uuid primary key,
  project_id uuid not null references projects(id) on delete cascade,
  external_id text not null,
  name text not null,
  input jsonb,
  output jsonb,
  error text,
  started_at timestamptz not null,
  latency_ms double precision not null default 0,
  cost_usd double precision not null default 0,
  total_tokens integer not null default 0,
  llm_calls integer not null default 0,
  tool_calls integer not null default 0,
  tool_sequence jsonb not null default '[]'::jsonb,
  steps jsonb not null default '[]'::jsonb,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create unique index if not exists traces_project_external_idx on traces (project_id, external_id);
create index if not exists traces_project_started_idx on traces (project_id, started_at desc);

create table if not exists test_runs (
  id uuid primary key,
  project_id uuid not null references projects(id) on delete cascade,
  external_id text not null,
  started_at timestamptz not null,
  duration_ms double precision not null default 0,
  total integer not null default 0,
  passed integer not null default 0,
  failed integer not null default 0,
  cost_usd double precision not null default 0,
  avg_latency_ms double precision not null default 0,
  git_sha text,
  git_branch text,
  results jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now()
);
create unique index if not exists test_runs_project_external_idx on test_runs (project_id, external_id);
create index if not exists test_runs_project_started_idx on test_runs (project_id, started_at desc);

create table if not exists waitlist (
  id uuid primary key,
  email text not null unique,
  plan text not null default 'pro',
  created_at timestamptz not null default now()
);

-- The app talks to Postgres with a server-side connection only. Enable RLS so
-- the tables are not exposed through Supabase's public REST API.
alter table projects enable row level security;
alter table traces enable row level security;
alter table test_runs enable row level security;
alter table waitlist enable row level security;
`;
