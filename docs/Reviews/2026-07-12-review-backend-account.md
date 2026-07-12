---
tags: [type/review, domain/startup, lane/backend]
updated: 2026-07-12
audience: Backend account — feat/backend-phase0, feat/backend-phase1-seams
source: 3-pass repo review, 2026-07-12 (all branches) + architecture re-validation
---
# 🔍 Review — Backend lane (2026-07-12)

> Companion docs: [[2026-07-12-review-ui-account]] (UI lane) ·
> [[2026-07-12-review-combined]] (full picture + market analysis, on `main`).
> Board → [[Status]].

## What was validated (by execution, not just reading)

- **`main`: 23/23 tests pass** (1.3s).
- **`feat/backend-phase1-seams`: 29/29 tests pass** in a clean worktree — the
  "23 behavioural preserved + 6 new" equivalence claim on the board is real.
- **Seams increment 1 verified faithful:** `models/router.py` is a
  line-for-line move of the old `stream_answer` — the
  failover-only-before-first-token policy survived intact and is now
  test-pinned. `core/llm.py` shim keeps `ask.py` byte-identical as claimed.
- **Protocol stubs are sound:** `verify/base.py`'s `INAPPLICABLE`-never-`FAIL`
  outcome and optional `Verdict.confidence` match plan edge case #4 and the
  future RLVR checker; `retrieval/base.py` matches the P2 RRF-merge shape.
- `quota.py` is **not** dead code — its pure helpers back `/v1/me` and are
  unit-tested; the atomic claim in `ask.py`'s SQL is the write path. Correct
  split, leave as is.

Overall verdict: the P0 backend is genuinely strong for ~1,400 lines —
atomic quota claim, disconnect-safe persistence via detached task,
refund-only-on-zero-tokens, per-solve traces, cache-stable system prompt,
Stripe webhook idempotency, JWKS auth. The findings below are the gaps.

## Findings

### B1 — SSRF + unbounded fetch on `image_url` (fix BEFORE deploy) 🔴
`/v1/ask` passes the client-supplied `image_url` straight to the Gemini
path, which does `client.get(image_url)` server-side with **no validation**.
Confirmed present in both `main`'s `core/llm.py` (~line 113) and the seams
branch's `models/gemini.py`. On Cloud Run this lets any authenticated user
make the backend probe arbitrary internal/external URLs. There is also no
size cap or content-type check — plan edge case #5 (cap ~4MB, downscale,
reject non-images) is written down but not implemented.

**Fix spec (small):** before fetching — require the URL to start with the
Supabase storage public prefix
(`{SUPABASE_URL}/storage/v1/object/public/question-images/`); on fetch —
`Content-Type` must be `image/*`, stream with a 4MB cap, 10s timeout;
reject politely with a 400 `BAD_IMAGE` envelope otherwise.

**Coordination (per the board's rule):** fix it on `main` in `core/llm.py`
first, then rebase/port to `models/gemini.py` on the seams branch — don't
let the two copies drift. It's ~20 lines + 2 tests; it does not disturb the
byte-identical `ask.py` discipline.

### B2 — Missing `GET /v1/sessions/{id}`
The frontend currently pages through `/v1/sessions` (up to 5 pages)
client-side to find one session; sessions older than ~100 entries show
"not found." Add the obvious endpoint (owner-scoped, 404-not-403 like the
feedback route). Consider `GET /v1/threads/{thread_id}` too — the UI's
follow-up work (their F1) will want all sessions of a thread in one call.

### B3 — Retrieval is inert until ingestion happens
Vector-only, top-8/keep-4, 0.75 similarity floor — over an **empty corpus**.
Every answer today is ungrounded general knowledge with the grounded-tutor
framing. Not your lane to fix (ingest is the UI/infra account's), but P2
multi-retrieval work should not start before there's a corpus to measure
against — otherwise the RRF merge is tuned on nothing.

### B4 — Minor
- `/v1/sessions` returns full `answer` bodies per page — fine at 20/page,
  but consider a truncated preview field when the UI only shows list rows.
- `_prompt_hash` hashes the full message list including history — two asks
  of the same question in a thread hash differently. Intended? If the goal
  is dedupe/cache-hit analysis, also storing a question-only hash would make
  the traces query easier. Cheap to add now, annoying to backfill.
- Free plan has no monthly backstop (daily cap only) — 10/day × 30 = 300
  free solves/mo ≈ ₹24 COGS at text rates. Acceptable; just watch the
  photo share (Gemini path is ~12× dearer).

### B5 — Billing provider (flag for the combined doc)
Checkout is Stripe subscription-mode. For ₹299/mo India B2C, UPI
autopay/e-mandates dominate and Stripe India has real constraints on
recurring INR billing. The billing surface is small (2 routes + webhook
idempotency table) — swapping to Razorpay later is contained, but decide
before wiring real prices. Details in [[2026-07-12-review-combined]].

## P1 continuation — no course change

The remaining increments on the board (rag→`retrieval/vector.py`, thin
`ask.py` + `orchestrator/pipeline.py`) are the right next moves and the
23-test guard is the right discipline. Two notes:
1. When the pipeline extraction happens, B1's validated-fetch helper should
   land in the pipeline/util layer, not inside a vendor adapter.
2. The merge gate (wait for the UI account's live e2e SSE transcript)
   stands — everything in this review respects it.
