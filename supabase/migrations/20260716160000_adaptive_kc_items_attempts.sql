-- 20260716160000_adaptive_kc_items_attempts — Phase A.1 of the adaptive loop.
--
-- The knowledge graph, the item bank, the event log, and the derived state
-- caches. Design: [[Adaptive-Loop-Architecture]] §3.2. Contracts these back:
-- app/adaptive/contracts.py (A.0). Nothing reads these tables yet — B.1/B.2 do.
--
-- Immutable ([[ADR-011]]): to change anything here, add a new migration. No
-- `if not exists` — a guard that silently no-ops is how drift hides.
--
-- TWO DEVIATIONS from §3.2's sketch, both found by implementing it. Each is
-- called out at the table below and in the PR:
--   1. Learned difficulty lives in `item_state`, not on `items.difficulty`
--      ([[ADR-012]]) — content and derived state must not share a table.
--   2. `student_kc_state` stores `p_correct`/`confidence`, which §3.2 omitted
--      ([[ADR-005]]) — without them the policy would have to know the
--      estimator's formula, which is the exact coupling ADR-005 forbids.

-- ---------------------------------------------------------------------------
-- Knowledge graph (authored content; A.2 seeds it)
-- ---------------------------------------------------------------------------

-- IDs are human-readable paths ('phy.mech.kinematics.projectile') so content
-- tagging is reviewable in a diff and a wrong prerequisite edge is visible in
-- code review.
create table knowledge_components (
  id text primary key,
  subject text not null,
  chapter text not null,
  name text not null,
  -- 1=subject 2=chapter 3=microconcept. Constrained because "resist 30k-KC
  -- fantasies" (§6) is a decision, and a depth of 7 should fail loudly.
  depth int not null default 3 check (depth between 1 and 3),
  created_at timestamptz not null default now()
);
create index knowledge_components_subject_chapter_idx
  on knowledge_components (subject, chapter);

-- The prerequisite DAG (ALEKS/KST). The policy walks this to find the frontier.
create table kc_edges (
  prereq text not null references knowledge_components on delete cascade,
  postreq text not null references knowledge_components on delete cascade,
  primary key (prereq, postreq),
  -- Self-loops are always a tagging error and would make a KC its own
  -- prerequisite: unreachable frontier, silently. Cheap to forbid here.
  -- NOTE: this does NOT prevent longer cycles (A->B->A). Postgres can't express
  -- that as a constraint; A.2's seed ingest must check reachability before
  -- insert. Tracked in that phase, not worked around here.
  constraint kc_edges_no_self_loop check (prereq <> postreq)
);
-- The PK covers (prereq, postreq) — i.e. "what does this unlock?". The policy's
-- actual question is the reverse ("what are this KC's prereqs?"), which the PK
-- can't serve.
create index kc_edges_postreq_idx on kc_edges (postreq);

-- ---------------------------------------------------------------------------
-- Item bank (authored content; A.3 fills it)
-- ---------------------------------------------------------------------------

create table items (
  id uuid primary key default gen_random_uuid(),
  kc_id text not null references knowledge_components,
  stem text not null,                     -- LaTeX, $...$ convention as today
  -- Same shape the P3 golden set uses and the shape GoldAnswerChecker (A.0)
  -- reads: {value, unit, choices?, expr?}. Curate once, use twice.
  answer_gold jsonb not null,
  hints jsonb,                            -- pre-authored ladder = the cheap path
  source_ref text,                        -- attribution (NCERT/JEE paper + year)
  content_hash text unique,               -- idempotent re-ingestion
  created_at timestamptz not null default now()
);
create index items_kc_idx on items (kc_id);

-- ---------------------------------------------------------------------------
-- The event log (append-only; the asset)
-- ---------------------------------------------------------------------------

-- Append-only per [[ADR-006]]: `student_kc_state` and `item_state` below are
-- rebuildable from this table, and that property is what makes the Phase C
-- estimator swap a re-run instead of a migration. No UPDATE/DELETE outside the
-- 18-month DPDP retention job, with ONE carve-out: `verify`/`error_class` are
-- late-arriving (P5 verifies post-stream, after the row is written). They are
-- write-once-later, not mutable — and they are not inputs to mastery, so a late
-- write cannot corrupt a replay.
--
-- DPDP: behavioural data of likely-minors. No PII beyond the user_id FK.
-- Retention: raw 18 months, aggregates forever — same rule as `traces`.
create table attempts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles on delete cascade,
  item_id uuid not null references items,
  -- NULLABLE on purpose: null = "not gradeable", which is exactly what a
  -- Verdict of INAPPLICABLE means ([[ADR-003]]). Do not default this to false —
  -- "we couldn't check it" and "they got it wrong" must not collapse into the
  -- same value, in the schema for the same reason they don't in the Verdict.
  correct boolean,
  response jsonb,                         -- raw answer as given
  time_ms int check (time_ms is null or time_ms >= 0),
  hints_used int not null default 0 check (hints_used >= 0),
  verify jsonb,                           -- Verdict from the engine (P5)
  -- Closed vocabulary, deliberately: a typo'd class silently poisons the
  -- remediation analytics that justify the whole misconception-tagging idea
  -- (Carnegie lesson). Adding a class is a migration — that's correct, not
  -- friction.
  error_class text check (
    error_class is null
    or error_class in ('conceptual', 'computational', 'careless')
  ),
  created_at timestamptz not null default now()
);
create index attempts_user_idx on attempts (user_id, created_at desc);
-- Rebuilding item_state replays every attempt of an item; without this that is
-- a seq scan over the largest table in the schema.
create index attempts_item_idx on attempts (item_id);

-- ---------------------------------------------------------------------------
-- Derived state (rebuildable caches — NOT sources of truth, [[ADR-006]])
-- ---------------------------------------------------------------------------

-- Safe to TRUNCATE and replay. If this ever disagrees with `attempts`, the log
-- is right.
create table student_kc_state (
  user_id uuid not null references profiles on delete cascade,
  kc_id text not null references knowledge_components on delete cascade,

  -- Estimator-native and NOT comparable across estimators (Elo ~0-3000; a JEPA
  -- head could emit anything). For the estimator's own next update only.
  rating real not null default 0,

  -- The portable unit ([[ADR-005]]). §3.2's sketch omitted these two columns;
  -- they are required, not a nicety: without a stored p_correct the policy would
  -- have to recompute it from `rating` via Elo's logistic formula in SQL — i.e.
  -- the policy would hard-code the estimator's internals, and swapping Elo for
  -- Student-JEPA would silently change item selection. That coupling is the one
  -- thing ADR-005 exists to prevent, so it must not exist in the schema either.
  p_correct real not null default 0.5 check (p_correct between 0 and 1),
  confidence real not null default 0 check (confidence between 0 and 1),

  attempts int not null default 0 check (attempts >= 0),
  correct int not null default 0 check (correct >= 0),
  last_attempt_at timestamptz,
  due_at timestamptz,                     -- FSRS review scheduling (B.1)
  -- Which estimator wrote this row. Provenance is not decoration: mixing two
  -- estimators' numbers in one decision is the bug this column makes visible,
  -- and a Phase C A/B is unreadable without it (mirrors KnowledgeState.estimator).
  estimator text not null default 'elo@v1',
  updated_at timestamptz not null default now(),
  primary key (user_id, kc_id),
  constraint student_kc_state_correct_le_attempts check (correct <= attempts)
);
-- The review half of the policy's candidate query ("what's due?").
create index student_kc_state_due_idx on student_kc_state (user_id, due_at)
  where due_at is not null;

-- Learned item difficulty. Separate from `items` per [[ADR-012]]: `items` is
-- authored content, this is derived state. Sharing one table would mean
-- rebuild() writes to the content table and A.3's re-ingest could clobber
-- learned difficulty.
create table item_state (
  item_id uuid primary key references items on delete cascade,
  rating real not null default 0,         -- Elo item rating; estimator-native
  attempts int not null default 0 check (attempts >= 0),
  correct int not null default 0 check (correct >= 0),
  estimator text not null default 'elo@v1',
  updated_at timestamptz not null default now(),
  constraint item_state_correct_le_attempts check (correct <= attempts)
);

-- ---------------------------------------------------------------------------
-- RLS — same posture as `sessions`/`chunks` in the baseline.
-- The API talks to Postgres directly (bypasses RLS); these are defence in depth
-- if a client ever reads through PostgREST.
-- ---------------------------------------------------------------------------

-- Per-student data: own rows only.
alter table attempts enable row level security;
alter table student_kc_state enable row level security;

create policy "own attempts" on attempts
  for select using (auth.uid() = user_id);
create policy "own kc state" on student_kc_state
  for select using (auth.uid() = user_id);

-- Shared content + aggregate state: RLS on, no policy (backend uses direct
-- asyncpg / service-role, which bypasses RLS — matches how `chunks` is handled;
-- the leftover advisor INFO `rls_enabled_no_policy` is expected and benign).
alter table knowledge_components enable row level security;
alter table kc_edges enable row level security;
alter table items enable row level security;
alter table item_state enable row level security;
