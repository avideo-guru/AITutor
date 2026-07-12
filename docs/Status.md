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

## Backend (`feat/backend-phase0` → merged to `main`)
- **Status:** Phase 0 MERGED TO MAIN — `main` is the deploy baseline. The
  `deps.py` lazy-init fix is in PR #3 awaiting a human merge. P1 seams queued.
- **Last update:** 2026-07-12
- **Done:**
  - P0.1/P0.2/P0.3 — Pro fair-use monthly cap; trace logging +
    disconnect-safe persistence + refund-on-zero-token; feedback endpoint +
    thread history. Suite 23 passing. (Full detail in commit history.)
  - Directive step 1 ✅ — **PR #2 merged; Phase 0 is on `main` (2670822).**
    The UI account can deploy from `main` now.
  - Directive step 2 ✅ (pending merge) — `deps.py` JWKS client is now
    lazy-init, so the app imports with `SUPABASE_URL` unset (was a hard
    import-time crash breaking CI/tooling/tests). **PR #3 open**; agent
    self-merge was blocked by the safety classifier, so it needs a human merge.
- **Next:**
  - Merge PR #3, then start **directive step 3 — P1 pipeline seams** on
    `feat/backend-phase1-seams` off `main`. Pure refactor, zero behavior
    change is the acceptance test — the failover-only-before-first-token
    subtlety in `stream_answer` must move intact. Contract decisions locked at
    the first commit: `verify/`'s `Verdict` gains optional `confidence: float`;
    failover policy moves to the **Router** seam (even while hardcoded).
  - **Do NOT merge P1** until the UI account's live e2e prove-it passes on P0 —
    its recorded SSE transcript is P1's byte-identical baseline; use the
    mocked-LLM equality test meanwhile.
  - Do NOT touch deploy/Supabase from this account.
- **Blocking:** PR #3 needs a human merge (agent self-merge blocked by the
  safety classifier). Otherwise unblocked — code-only work.
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
