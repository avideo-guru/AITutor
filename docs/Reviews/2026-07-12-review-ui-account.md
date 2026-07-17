---
tags: [type/review, domain/startup, lane/ui-infra]
updated: 2026-07-12
audience: UI/Infra account (this laptop) — feat/ui-redesign, feat/deploy-cloudrun
source: 3-pass repo review, 2026-07-12 (all branches) + architecture re-validation
---
# 🔍 Review — UI/Infra lane (2026-07-12)

> Companion docs: [[2026-07-12-review-backend-account]] (backend lane) ·
> [[2026-07-12-review-combined]] (full picture + market analysis, on `main`).
> Board → [[Status]].

## What was reviewed and validated

- All 6 branches audited; frontend read file-by-file on `main` and
  `feat/ui-redesign` (diff: 18 files, +718/−114).
- **Validated by execution:** backend suite passes on `main` (23/23) and on
  `feat/backend-phase1-seams` (29/29) — the P0 API contract the UI codes
  against is test-pinned and real.
- **Validated by inspection:** Google OAuth on the redesign branch is genuinely
  wired (`supabase.auth.signInWithOAuth({provider: "google"})` in
  `sign-in.tsx`), not just a button. The redesign's platform-split pattern
  (`.web.tsx` siblings for Branches/GoogleG/entrance) matches the existing
  `math.tsx`/`math.web.tsx` convention — consistent, keep it.

## Frontend architecture verdict

Sound for its size. Clean layering: typed API client (`lib/api.ts`) with a
hand-rolled SSE parser; server state in TanStack Query; exactly one Zustand
store (the live stream) — the comment "everything else is server state" is
honored in practice. KaTeX render is platform-split correctly. No test
runner and no lint config exist (only `tsc --noEmit`) — acceptable now, add
before the codebase grows past ~10 screens.

## Findings (ordered by product leverage)

### F1 — No follow-up questions (highest leverage)
The backend accepts `thread_id` on `/v1/ask`, loads the last 4 Q/A pairs of
that thread as model context, and returns `thread_id` in the SSE `meta`
event. The frontend never sends it, and `AskMeta` in `lib/api.ts` doesn't
even declare the field — the capability is invisible. Tutoring is
conversational; a student's next message is "why step 3?".

**Fix sketch:** add `thread_id` to `AskMeta` and store it in the stream
store's `onMeta`; render the redesign's `Composer` at the bottom of
`thread/[id].tsx` (live mode); submitting there calls `ask()` with the
stored `thread_id` and appends a new bubble instead of replacing. The store
becomes a turn list (`turns: {question, answer, ...}[]`) rather than a
single Q/A — a contained refactor of `state/stream.ts`.

### F2 — No feedback UI (the flywheel is starving)
`POST /v1/sessions/{id}/feedback` (👍/👎 + optional reason) shipped in P0.3
and is idempotent — but no screen renders it, so the helpfulness data the
whole eval/verifier plan feeds on collects **zero rows**. Fix: two icon
buttons on `Bubble` once `status === "done"` (session_id arrives in `meta`),
optimistic update, one mutation. Half a day including a "tell us why" sheet
on 👎.

### F3 — Past-session lookup is fragile
`thread/[id].tsx#findSession` pages through `/v1/sessions` (5 pages × 20) to
find one session client-side; anything older than ~100 sessions renders
"Session not found." Blocked on the backend adding `GET /v1/sessions/{id}`
(requested in the backend review doc) — when it lands, replace `findSession`
with a single fetch. Also: a thread view should eventually fetch *all
sessions of a thread_id*, which pairs naturally with F1.

### F4 — Question images are public
`uploadQuestionImage` uploads to the public `question-images` bucket and
passes the public URL. Anyone with the URL can view a student's photo
(names/doodles/notebook pages — DPDP surface). MVP-acceptable; plan the move
to a private bucket + signed URLs. Coordinate with backend: the Gemini path
fetches that URL server-side, so switching to signed URLs must land on both
sides at once (backend review doc, finding B1, covers the server half).

### F5 — Minor
- `LiveThread` line 47: `s.answer || (s.status === "streaming" ? "" : s.answer)`
  is a no-op expression — simplify to `s.answer`.
- No retry/abort on the stream; navigating away leaks a running fetch
  (harmless today, matters when threads land — add an AbortController).
- `history.tsx` shows raw question text only; after F1, group by `thread_id`.

## The UI plan (ordered)

1. **Finish + merge `feat/ui-redesign`** — review the two still-uncommitted
   files (`Branches.web.tsx`, `Input.tsx`), commit, PR to `main`. Everything
   below builds on the redesign's `Composer`.
2. **F1 follow-up threads** — the single biggest product gap.
3. **F2 feedback buttons** — cheapest flywheel unlock in the repo.
4. **F3 session-by-id** — after backend adds the endpoint.
5. **F4 signed URLs** — jointly with backend, pre-scale.

## Infra lane (unchanged, still the critical path)

Everything above is queued behind: human-authenticated `gcloud` → run
`backend/deploy/cloudrun.sh` (validated: Secret Manager for all keys, 600s
SSE timeout, `$PORT` honored in the Dockerfile with `exec` for SIGTERM
drain) → wire `frontend/.env` + Stripe webhook → ingest Physics–Optics →
run the P0 prove-it (which also unblocks the backend account's P1 merge).
