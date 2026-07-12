---
tags: [type/status, domain/startup]
updated: 2026-07-12
---
# 🛰️ Status — cross-account orchestration board

> Two people, two accounts, two machines, one repo. This file is the async
> message board between them — update your section every session, before you
> stop and before the other side starts. Keep entries short: what's done,
> what's next, anything blocking. Full context lives in the branch's commits,
> not here.

## Branches
- `feat/backend-phase0` — backend work (this laptop's other account).
  Executes [[Opus-Execution-Plan]] starting at Phase 0.
- `feat/ui-redesign` — UI/UX work (this account, this laptop).
- `main` — only merge into this once a branch is stable and reviewed. Don't
  push work-in-progress directly to `main`.

## Workflow (both sides)
1. **Pull `main` before starting a session** — `git checkout <your-branch> &&
   git merge main` (or rebase if you prefer) — to avoid basing work on stale
   code.
2. **Push small, push often** — commit in reviewable chunks, not one giant
   diff at the end of a session.
3. **Update your section below before ending a session.**
4. **Merge to `main` via PR**, not a direct push, once a phase/feature is done
   — gives the other side a clean point to pull from.

---

## Backend (P1 in progress on `feat/backend-phase1-seams`)
- **Status:** Phase 0 + deps fix on `main`. **P1 pipeline seams STARTED** —
  increment 1 (model plane split) done on `feat/backend-phase1-seams`; branch
  open, NOT merged (see Rule). Deploy is the UI account's lane.
- **Last update:** 2026-07-12
- **Done:**
  - P0.1/P0.2/P0.3 on `main` (2670822) — fair-use cap; traces +
    disconnect-safe persistence + refund; feedback endpoint + thread history.
  - `deps.py` lazy-init fix + CLAUDE.md standing-instruction update
    (PRs #3, #4) merged to `main` — app now imports with `SUPABASE_URL` unset.
  - **P1 seams increment 1** (`feat/backend-phase1-seams`, commit d9b733b) —
    pure refactor, zero behavior change. `core/llm.py` split into
    `models/{deepseek,gemini,router,base}.py`; `core/llm.py` kept as a
    re-export shim so `ask.py` is byte-identical (untouched). Failover policy
    moved into the **Router** — failover-only-before-first-token moved intact
    and now test-pinned. Added Protocol stubs: `verify/base.py` (`Verdict`
    with optional `confidence`), `retrieval/base.py` (`Retriever`),
    `tools/base.py` (`Tool`), `sse.py` (SSE event-protocol constants).
    **29 tests** (23 behavioural preserved as the equivalence proof + 6 new).
- **Next (P1 remaining increments, same branch):**
  - `core/rag.py` → `retrieval/vector.py` implementing `Retriever` (shim kept).
  - `routes/ask.py` → thin: an `orchestrator/pipeline.py` owns the stream/gate
    loop + SSE emission (via `sse.py` constants); `ask.py` just parses request,
    checks quota, calls the pipeline. Behaviour must stay byte-identical (the
    23 behavioural tests are the guard).
- **Rule:** **Do NOT merge P1** until the UI account's live e2e prove-it
  passes on P0 — its recorded SSE transcript is P1's byte-identical baseline;
  the mocked-LLM + 23 behavioural tests are the interim check. Do NOT touch
  deploy/Supabase from this account.
- **Blocking:** none — code-only. P1 merge waits on the UI account's e2e run.
- **UI account's lane (unchanged):** the live project (`xdszkwjkaamyycirfslz`)
  is on the UI account's MCP, which owns all live-infra work — apply the P0
  migrations from `schema.sql`, enable RLS on `chunks`/`billing_events`
  (Supabase advisor flag), wire secrets, ingest Physics–Optics, run the P0
  prove-it (3 questions + mid-stream kill). Coordination rule: if e2e surfaces
  a bug, fix it on `main` *before* P1 rebases on it — don't race fixes in
  parallel in `ask.py` / `core/llm.py`.

## UI/UX (`feat/ui-redesign`)
- **Status:** in progress — picking up pre-existing uncommitted changes
- **Last update:** 2026-07-12
- **Done:** (carried over, not yet committed) modified `index.tsx`,
  `sign-in.tsx`, `thread/[id].tsx`, `Bubble.tsx`, `Input.tsx`, `Screen.tsx`,
  `theme.ts`; new `Branches.tsx`/`.web.tsx`, `Brand.tsx`, `Composer.tsx`,
  `DottedBackground.tsx`, `GoogleG.tsx`/`.web.tsx`, `entrance.ts`/`.web.ts`
- **Next:** review + commit the above, continue redesign pass
- **Blocking:**

## Connections
- Tracks execution of → [[Opus-Execution-Plan]]
- Hub → [[Startup-MOC]]
