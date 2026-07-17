---
tags: [type/adr, domain/startup, startup/architecture]
status: accepted
date: 2026-07-16
landed: PR #8; live-project reconciliation still owed (infra account)
---
# ADR-011 — Migrations are immutable, numbered files; `schema.sql` is not the source of truth

**Decision:**
Schema changes are **timestamp-numbered, immutable files** in
`supabase/migrations/`. Once merged, a migration is never edited — you add a new
one. `backend/schema.sql` is demoted to a pointer and is no longer applied.

**Context:**
Until now the schema was one evolving `backend/schema.sql`, run by hand in the
Supabase SQL editor (`backend/README.md` step 1), with change history kept as
`-- Migration (P0.1)` comment blocks appended to the bottom. Meanwhile the infra
account applied P0.1–P0.3 to the live project via the Supabase MCP, which wrote
to that project's own `supabase_migrations.schema_migrations` ledger. So there
were **two records of schema history, neither aware of the other**, and the
authoritative one (the live ledger) wasn't in git.

**Reason:**
- **`if not exists` masks drift instead of catching it.** The file was 16 such
  guards. If live diverges — a hand-edited column type, a missing index — a
  re-run silently no-ops and reports success. "It ran fine" plus a wrong schema
  is strictly worse than an error.
- **One evolving file cannot express a non-additive change.** It has no place to
  put a backfill, a rename, or a type change — only `add column if not exists`.
  A.1 adds five tables; Phase C rebuilds `student_kc_state` ([[ADR-006]]).
  Neither fits.
- **"Which version is this database?" had no answer.** A ledger answers it; a
  file whose contents you diff by eye does not.
- **The stack already supports this natively** — the Supabase CLI's migration
  ledger is the same one the MCP was writing to. We were half-using it by
  accident.

**Consequences:**
- New schema work = `supabase migration new <name>` → one file → review → merge →
  `supabase db push`. A.1's tables are the first real user.
- **Timestamps, not `0008_`-style sequence numbers.** Two accounts on two
  branches both pick `0008`, and git merges the two files *without a conflict*
  because the filenames differ — leaving an undefined apply order and no signal.
  Timestamps don't collide and survive merges.
- New migrations should not use `if not exists`; the baseline does, and says why
  in its header.
- `supabase db reset` (local, free) replays the whole chain into an empty DB —
  that is the test that a migration is real and not just true of one laptop.
- **Owed, not done:** the live project's ledger disagrees with this directory,
  and nobody currently knows what it contains. The reconciliation (`migration
  list` → `repair` → verify) is a human step for the infra account and is
  spelled out in `supabase/README.md`. **`db push` must not run against live
  until then.** This ADR is not fully landed until that reconciliation is
  reported on the board.
