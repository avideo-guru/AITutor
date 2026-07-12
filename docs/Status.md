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

## Backend (`feat/backend-phase0`)
- **Status:** Phase 0 COMPLETE — P0.1 + P0.2 + P0.3 done. Ready for P1
  (pipeline seams) — but per orchestration call, next real step is getting the
  MVP running end-to-end (needs Supabase reconnect, see Blocking).
- **Last update:** 2026-07-12
- **Done:**
  - P0.1 Pro fair-use monthly cap (`questions_month*` cols, IST-month atomic
    SQL, `PRO_FAIR_USE_LIMIT` 402, `remaining_month` + tests).
  - P0.2 trace logging — `traces` table (per-ask flywheel row); `ask.py`
    persistence moved into `try/finally` + made idempotent so a mid-stream
    client disconnect still writes a partial trace (`disconnected=true`);
    zero-token LLM failure refunds the quota claim (daily + monthly) and
    traces `gate_outcome=error`; session+trace in one txn; behavioural tests
    (fake pool) for show / error+refund / disconnect.
  - P0.3 feedback + history — `POST /v1/sessions/{id}/feedback` (idempotent,
    404 not 403 on foreign session); `thread_id` on `AskRequest` loads last 4
    caller-owned turns as `history` (after the cache-stable system prompt),
    truncation keeps the boxed answer; `thread_id` persisted + returned in
    `meta`. Suite 23 passing.
- **Next:** directive from UI account (2026-07-12), Phase 0 review ACCEPTED —
  do these in order, code-only:
  1. **Open the PR `feat/backend-phase0` → `main`.** Phase 0 is shippable
     alone; main becomes the deploy baseline for the UI account's e2e work.
  2. First commit after merge: the `deps.py` **lazy-init fix** (JWKS client is
     built at import time; nothing imports without `SUPABASE_URL` set).
  3. Start **P1 pipeline seams** on a fresh branch off main
     (`feat/backend-phase1-seams`). Pure refactor, zero behavior change is
     the acceptance test — the failover-only-before-first-token subtlety in
     `stream_answer` must move intact.
  4. Contract decisions inside P1: give the `verify/` stub's `Verdict` an
     optional `confidence: float` (one line now, avoids a Protocol migration
     when an ML/RLVR verifier lands); failover policy belongs in the
     **Router**, not inside each model adapter — set that seam now even while
     the logic stays hardcoded.
  5. **Do NOT merge P1** until the UI account's live e2e prove-it passes on
     P0 — its recorded SSE transcript is P1's byte-identical baseline. Use
     the mocked-LLM equality test in the meantime.
  - Do NOT touch deploy/Supabase from this account — see below, the blocker
    moved sides.
- **Blocking:** nothing for the steps above (all code-only). The old Supabase
  blocker is VOID for you: the live project (`xdszkwjkaamyycirfslz`) is
  connected via MCP on the **UI account**, which now owns all live-infra work
  — applying the P0 migrations from `schema.sql`, enabling RLS on
  `chunks`/`billing_events` (Supabase advisor flag), wiring secrets, ingesting
  Physics–Optics, and running the P0 prove-it (3 questions + mid-stream kill).
  Coordination rule: if the e2e run surfaces a bug, it gets fixed on main
  *before* P1 rebases on it — don't race fixes in parallel in `ask.py` /
  `core/llm.py`.

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
