---
tags: [type/review, domain/startup, decision/input]
updated: 2026-07-12
audience: both accounts
source: 3-pass repo review (all 6 branches) + architecture re-validation, 2026-07-12
---
# 🔍 Combined repo review — 2026-07-12

> Per-lane actionables split out to [[2026-07-12-review-ui-account]] (on
> `feat/ui-redesign`) and [[2026-07-12-review-backend-account]] (on
> `feat/backend-phase0`). This doc is the shared picture: branch state,
> architecture validation, cross-cutting gaps, and the market-impact items
> nobody owns yet. Board → [[Status]] · Plan → [[Opus-Execution-Plan]].

## 1. Branch state

| Branch | State | Note |
|---|---|---|
| `main` | ✅ P0 complete | 23/23 tests pass (verified this session) |
| `feat/backend-phase1-seams` | open, 1 commit | 29/29 tests pass (verified in clean worktree); merge correctly gated on the live e2e transcript |
| `feat/ui-redesign` | open, WIP | redesign (+718/−114 over 18 files); Google OAuth genuinely wired; 2 files still uncommitted |
| `feat/deploy-cloudrun` | open, 1 commit | `$PORT` Dockerfile fix + deploy runbook — **PR to `main` soon; both lanes need it** |
| `feat/backend-phase0` | fully merged | history only |
| `archive/angular-fastapi-redesign` | archive | untouched, as intended |

## 2. Architecture validation (re-checked against code, not docs)

**Verdict: the architecture is sound and the plan is being executed
faithfully. The system's weaknesses are around the code, not in it.**

Validated by execution or line-level inspection this session:
- **Quota:** atomic lazy-reset + cap-check + increment in one UPDATE (no
  race); Pro fair-use monthly cap in IST; refund only on zero-token LLM
  failure; never on disconnect. Matches plan P0.1 + edge cases #1/#2 exactly.
- **Streaming/persistence:** SSE generator persists on happy path, LLM-death
  path, and (detached task, GC-protected) client-disconnect path — once.
  Traces capture retriever set, chunk ranks, prompt hash, stage latency,
  gate outcome. Matches P0.2.
- **Model plane (seams branch):** router owns failover
  (only-before-first-token moved intact, now test-pinned); vendor adapters
  are leaf modules; `core/llm.py` shim keeps `ask.py` byte-identical.
  `Verdict.confidence` + `INAPPLICABLE`-never-`FAIL` in `verify/base.py`
  match edge case #4 and the future probabilistic checker. Matches P1.
- **Auth:** JWKS-verified (ES256/RS256, audience-checked), lazy client init.
- **Deploy:** Dockerfile honors `$PORT`, `exec` for SIGTERM SSE drain;
  runbook uses Secret Manager (no keys in env), `asia-south1`, 600s timeout.
- **Frontend:** clean layering (typed client / TanStack Query / single
  Zustand store), platform-split KaTeX. No tests/lint yet — acceptable at
  this size.

Exceptions found (the two real defects):
- 🔴 **B1 — SSRF + unbounded fetch on `image_url`** (both `main` and seams
  branch): server fetches a client-supplied URL unvalidated; no size or
  content-type cap (plan edge case #5 unimplemented). Fix spec in the
  backend doc. **Should land before the Cloud Run deploy.**
- **B2 — no `GET /v1/sessions/{id}`**, forcing a 5-page client-side scan
  that breaks for old sessions.

## 3. The cross-cutting gap: frontend is a phase behind

P0.3 (feedback + thread history) is "done" on `main` but has **no UI
surface**: the app never sends `thread_id` (no follow-up questions — the
core tutoring interaction) and never renders 👍/👎 (the data flywheel
collects zero rows). The plan's phases are backend-scoped, which is how a
phase got marked done while being invisible to users.

**Proposed rule for the board:** *a phase isn't done until its capability
has a UI surface* — add a frontend-parity line item to every phase.

## 4. Critical path (unchanged, restated because everything queues on it)

```
human gcloud auth → cloudrun.sh deploy → env/webhook wiring
  → ingest Physics–Optics → P0 prove-it (live SSE transcript)
    → P1 merge unblocks → P2+ proceed on a real corpus
```
One ~30-minute human step (gcloud auth) is currently blocking every
downstream engineering hour. Do it next.

Also note: until ingestion, retrieval runs against an **empty corpus** —
the product's stated differentiator (groundedness) is inert in any demo
given today.

## 5. Market-impact items with no owner (the expensive silence)

These gate the business case, need little or no code, and appear on no
lane in [[Status]]:

1. **The 100-problem Phase-0 dataset** (JEE Main physics + ground truth).
   Gates the P3 eval harness AND the P5 verifier accuracy gate (≥95%
   final-answer, ≥99% step-precision — the pre-registered kill criterion).
   Pure curation. Every week it doesn't exist, the moat work has no
   yardstick.
2. **Institute design-partner conversations** — the 90-day bet the entire
   plan hedges around ([[Viability-Brutal-Honesty]] §1.4). Zero movement
   recorded. The code is ahead of the validation it exists to serve.
3. **Payments for India:** Stripe subscription-mode vs a ₹299 UPI-first
   market. Stripe India constrains recurring INR/e-mandates; Razorpay/
   Cashfree are the default rails. The billing seam is 2 routes + an
   idempotency table — swapping is cheap now, expensive after real
   subscribers. Decide before wiring live prices.
4. **WhatsApp funnel:** the docs' own GTM (Doubtnut/Byju's lessons) says
   distribution = institutes + WhatsApp, but the only surface is a PWA.
   The SSE backend can serve a WhatsApp bot behind a thin adapter
   (non-streaming: accumulate → send). Cheapest acquisition experiment
   available once deployed.
5. **Privacy posture:** question photos in a public bucket + DPDP-aligned
   retention already promised in `schema.sql` comments. Signed URLs are a
   joint frontend+backend change; schedule pre-scale.

## 6. Suggested sequencing (both lanes, next ~2 weeks)

| # | Item | Lane | Size |
|---|---|---|---|
| 1 | gcloud auth + deploy + ingest + P0 prove-it | UI/infra (human) | hours |
| 2 | B1 SSRF/image-cap fix on `main`, port to seams | backend | ~20 lines + tests |
| 3 | Merge `feat/deploy-cloudrun` + `feat/ui-redesign` | both | PRs |
| 4 | Follow-up threads (F1) + feedback UI (F2) | UI | days |
| 5 | `GET /v1/sessions/{id}` (+ `/v1/threads/{id}`) | backend | small |
| 6 | Start the 100-problem dataset + institute outreach | founders | parallel, non-code |
| 7 | P1 remaining increments → merge after e2e | backend | on plan |
