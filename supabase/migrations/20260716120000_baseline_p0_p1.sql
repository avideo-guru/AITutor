-- 20260716120000_baseline_p0_p1 — SQUASHED BASELINE.
--
-- This is `backend/schema.sql` as of 2026-07-16 (P0 + P1), frozen as the first
-- immutable migration. Everything after this is a new numbered file; this one is
-- never edited again ([[ADR-011]] in docs/Decisions/).
--
-- History note, deliberately honest: P0.1 / P0.2 / P0.3 were real, separate
-- changes and were applied to the live project (`xdszkwjkaamyycirfslz`) on
-- 2026-07-12 via the Supabase MCP, which recorded them in that project's own
-- `supabase_migrations.schema_migrations` ledger. Those version strings are NOT
-- in this repo and are not reconstructable from it. Splitting this baseline into
-- fabricated per-phase files would invent a history that never existed in git, so
-- it is squashed instead. See supabase/README.md § "Reconciling the live project"
-- — the live DB must be told this baseline is already applied rather than having
-- it re-run.
--
-- Idempotency (`if not exists`) is retained ONLY so this baseline can be applied
-- to a project that already has these objects. New migrations should NOT rely on
-- it: see ADR-011 on why `if not exists` silently no-ops on drift.

create extension if not exists vector;

create table if not exists profiles (
  id uuid primary key references auth.users on delete cascade,
  exam_target text default 'JEE_2027',
  plan text not null default 'free',            -- free | pro
  stripe_customer_id text,
  plan_expires_at timestamptz,
  questions_today int not null default 0,
  questions_reset_on date not null default current_date,
  -- P0.1: Pro fair-use monthly cap (the Copilot fix)
  questions_month int not null default 0,
  questions_month_reset_on date not null default current_date
);

create table if not exists sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles on delete cascade,
  question text not null,
  image_url text,
  answer text,
  model text,
  tokens_in int,
  tokens_out int,
  cost_usd numeric(8,5),
  created_at timestamptz default now(),
  -- P0.3: feedback capture + thread grouping.
  -- feedback_rating is 'up' | 'down'; thread_id groups a follow-up conversation
  -- so /v1/ask can load prior turns as context.
  thread_id uuid,
  feedback_rating text,
  feedback_reason text,
  feedback_at timestamptz
);
create index if not exists sessions_user_created_idx
  on sessions (user_id, created_at desc);
create index if not exists sessions_thread_idx on sessions (thread_id, created_at);

create table if not exists chunks (                -- the RAG store
  id uuid primary key default gen_random_uuid(),
  subject text,
  chapter text,
  source_ref text,
  content text not null,
  content_hash text unique,                        -- idempotent re-ingestion
  embedding vector(1024)
);
create index if not exists chunks_embedding_idx
  on chunks using hnsw (embedding vector_cosine_ops);

create table if not exists billing_events (        -- Stripe webhook idempotency
  stripe_event_id text primary key,
  processed_at timestamptz default now()
);

-- P0.2: trace log — the data flywheel. One row per ask, keyed to the session.
-- Cost/tokens stay on `sessions`; everything a solve *did* lives here. This is
-- the only table allowed to grow unbounded.
-- Retention: raw traces 18 months (DPDP-aligned), aggregates forever. Never
-- store raw images — the session's image_url (a storage ref) is enough.
create table if not exists traces (
  session_id uuid primary key references sessions on delete cascade,
  classification jsonb,                    -- Understand stage output (P4+)
  retrievers_used text[],                  -- e.g. {vector} today; +keyword (P2)
  chunks jsonb,                            -- [{id, source_ref, score, rank}]
  prompt_hash text,                        -- dedupe / cache-hit analysis
  gate_outcome text,                       -- show | partial | error | disconnected
  verify jsonb,                            -- verifier verdicts (P5)
  stage_latency_ms jsonb,                  -- {retrieve_ms, stream_ms, ...}
  disconnected boolean not null default false,
  created_at timestamptz default now()
);
create index if not exists traces_created_idx on traces (created_at);

-- Defense in depth: the API talks to Postgres directly (bypasses RLS), but if a
-- client ever reads through PostgREST these policies keep data per-user.
alter table profiles enable row level security;
alter table sessions enable row level security;

drop policy if exists "own profile" on profiles;
create policy "own profile" on profiles
  for select using (auth.uid() = id);

drop policy if exists "own sessions" on sessions;
create policy "own sessions" on sessions
  for select using (auth.uid() = user_id);

-- RLS was additionally enabled on `chunks`, `billing_events` and `traces` on the
-- live project (2026-07-12, security advisors) — no policies needed, the backend
-- uses direct asyncpg / service-role which bypasses RLS. Mirrored here so a fresh
-- project matches live.
alter table chunks enable row level security;
alter table billing_events enable row level security;
alter table traces enable row level security;

-- Storage: create a public bucket named `question-images` in the Supabase
-- dashboard; the app uploads photos there and passes the public URL to /v1/ask.
-- (Buckets are not DDL — this stays a manual setup step; see backend/README.md.)
