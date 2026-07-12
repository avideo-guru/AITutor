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

## Backend (P1 COMPLETE on `feat/backend-phase1-seams`, unmerged)
- **Status:** Phase 0 + deps fix on `main`. **All 3 P1 seam increments done**
  on `feat/backend-phase1-seams`; branch open, NOT merged (see Rule). Ready
  for the UI account's e2e prove-it now that P0 migrations are confirmed live
  (see Infra section below) — that run is P1's merge gate.
- **Last update:** 2026-07-12
- **Done:**
  - P0.1/P0.2/P0.3 + deps.py fix on `main` (see prior entries / commit history).
  - **P1 increment 1** (commit d9b733b) — model plane split: `core/llm.py` →
    `models/{deepseek,gemini,router,base}.py`, shim kept. Failover policy
    moved into the **Router**, failover-only-before-first-token pinned by
    tests. `verify/base.py` `Verdict` gains optional `confidence`.
    `retrieval/base.py`, `tools/base.py`, `sse.py` stubs added.
  - **P1 increment 2** (commit 2130416) — `core/rag.py` → `retrieval/vector.py`
    (`VectorRetriever` implementing the `Retriever` Protocol), shim kept.
  - **P1 increment 3** (commit 2130416) — `routes/ask.py` collapsed to ~100
    lines (parse, claim quota, hand off); `orchestrator/pipeline.py` now owns
    the fixed stage order (retrieve → history → build → stream → persist/SSE),
    moved intact from the old inline generator — same try/finally disconnect
    handling, same refund-on-zero-token, same detached-task write.
  - **Proof: 30 tests passing** (23 P0 behavioural tests — driving the real
    `/v1/ask` route — pass unchanged through the new thin-route→pipeline path,
    which is the equivalence evidence; +1 byte-exact SSE-frame test as the
    interim byte-identical check; +6 model-plane seam tests incl. the
    failover-only-before-first-token cases).
- **Next:** wait for the UI account's live e2e prove-it (3 questions + mid-
  stream kill against the now-live, now-migrated DB) — its recorded SSE
  transcript is P1's byte-identical baseline, then merge P1 to `main`.
- **Rule:** Do NOT merge P1 until that e2e prove-it passes. Do NOT touch
  deploy/Supabase from this account.
- **Blocking:** none — code-only, done. Waiting on the UI account's e2e run.
- **Flagging back to the UI account's review findings (not yet actioned,
  backend lane, needs a decision on priority vs. P1 merge):**
  1. **Security — SSRF risk:** `image_url` in the Gemini vision path
     (`models/gemini.py::stream`, moved from the old `core/llm.py`) fetches a
     user-supplied URL server-side with no allowlist/size/content-type check.
     Pre-existing behavior (not introduced by P1 — carried over verbatim per
     the zero-behavior-change rule), but real. Fix: allowlist the Supabase
     storage URL prefix, cap ~4MB, check content-type before fetching.
  2. **Missing endpoint:** `GET /v1/sessions/{id}` doesn't exist; frontend
     paginates client-side as a workaround. Small addition to
     `routes/sessions.py`.
  Recommend fixing #1 before ingest/prove-it happens against a public image
  bucket; #2 can wait.

## UI/UX + Infra (`feat/ui-redesign`, `feat/deploy-cloudrun`)
- **Status:** in progress — UI redesign + owns live-infra/deploy lane
- **Last update:** 2026-07-12
- **Done (UI):** (carried over, not yet committed) modified `index.tsx`,
  `sign-in.tsx`, `thread/[id].tsx`, `Bubble.tsx`, `Input.tsx`, `Screen.tsx`,
  `theme.ts`; new `Branches.tsx`/`.web.tsx`, `Brand.tsx`, `Composer.tsx`,
  `DottedBackground.tsx`, `GoogleG.tsx`/`.web.tsx`, `entrance.ts`/`.web.ts`
- **Done (Infra):** Cloud Run deploy prep on `feat/deploy-cloudrun` (off
  `main`) — **fixed `backend/Dockerfile`** to honor `$PORT` (was hardcoded
  8080; Cloud Run contract) + `exec` for SIGTERM SSE drain; added
  `backend/deploy/cloudrun.sh` (deploy-from-source, `asia-south1`,
  scale-to-zero, Secret Manager, 600s SSE timeout). PR to `main` pending.
  *Backend account: the `$PORT` Dockerfile fix is on that branch — pull it
  before any deploy; it does NOT touch P1 files.*
- **Done (Infra — live DB, 2026-07-12):** P0.1/P0.2/P0.3 applied to live
  Supabase (`xdszkwjkaamyycirfslz`) as tracked migrations — now matches
  `main`'s `schema.sql`. RLS enabled on `chunks`, `billing_events`, **and
  `traces`** (new public table from P0.2, same exposure). All ERROR/critical
  security advisors cleared; only benign `rls_enabled_no_policy` INFO remains
  (backend uses direct asyncpg / service-role, which bypass RLS — no policy
  needed). Pre-existing WARNs untouched (`vector` in `public`, Auth
  leaked-password protection off).
- **Next (Infra):**
  - install/auth `gcloud`, create Secret Manager secrets, run
    `bash backend/deploy/cloudrun.sh` → get service URL.
  - Wire `frontend/.env` API base + Stripe webhook to the URL; ingest
    Physics–Optics; run the P0 prove-it (produces P1's baseline SSE transcript).
- **Next (UI):** review + commit the carried-over redesign changes.
- **Blocking:** actual `gcloud run deploy` needs a human-authenticated GCP CLI
  (account/auth can't be done by the agent) — script is ready to run.

## 3-pass repo review (2026-07-12, UI account — full-branch audit)
Findings both sides should see. **Detailed write-ups now in the repo:**
combined → [[2026-07-12-review-combined]] (`docs/Reviews/`, on `main`);
per-lane → [[2026-07-12-review-ui-account]] (on `feat/ui-redesign`) and
[[2026-07-12-review-backend-account]] (on `feat/backend-phase0`).
Architecture re-validated by execution: `main` 23/23 tests, seams 29/29
in a clean worktree; Google OAuth wiring and Cloud Run deploy config
confirmed by inspection. Summary of the findings:
- **Frontend lags backend by a phase:** P0.3 is "done" on `main` but the app
  never sends `thread_id` (no follow-up questions) and has **no feedback UI**
  (👍/👎 endpoint unused → the data flywheel isn't being fed). These are the
  two highest-leverage UI tasks after the redesign merge.
- **Backend security gap (pre-deploy fix):** `/v1/ask` `image_url` is fetched
  server-side unvalidated in the Gemini path — SSRF on Cloud Run + no size/
  content-type cap (plan edge case #5 not yet implemented). Fix: allowlist the
  Supabase storage URL prefix, cap ~4MB, check content-type. Backend lane.
- **Missing endpoint:** no `GET /v1/sessions/{id}` — thread screen paginates
  up to 5 pages client-side to find one session; sessions older than ~100
  entries show "not found". Small backend add + frontend switch.
- **Critical path unchanged:** nothing is live e2e (gcloud deploy blocked on
  human auth), corpus is empty until Physics–Optics ingest → P0 prove-it →
  P1 merge. Everything else queues behind this.
- **Untracked market-impact items (no owner on this board):** the 100-problem
  Phase-0 dataset (gates P3 evals + P5 verifier — zero code, pure curation);
  institute design-partner conversations (the 90-day kill test); Razorpay/UPI
  vs Stripe for ₹299 India B2C; WhatsApp funnel. Suggest assigning lanes.

## Zero-spend deploy guardrails (2026-07-12, backend account — verified research)
Decision from the user: **₹0 total spend until the app is properly functional.**
Verified free-tier facts + required changes, for whoever runs the deploy:
1. **🔴 Code blocker: `gemini-2.5-pro` is NOT on the Gemini free tier anymore**
   (2.5 Flash / Flash-Lite are; embeddings `gemini-embedding-001` is). Our
   Gemini adapter hardcodes 2.5-pro → every vision/failover call fails on a
   free key. **Fix LANDED on the P1 branch (33e9d09):** adapter reads
   `GEMINI_MODEL` env at call time (default unchanged = 2.5-pro); zero-spend
   deploys add `GEMINI_MODEL=gemini-2.5-flash` to `--set-env-vars`. Free Flash
   limits: 10 RPM / 250 req/day, resets midnight PT — plenty for the prove-it.
   ⇒ the prove-it/deploy should therefore run against the **P1 branch build**
   (or wait for P1's merge) — `main`'s adapter can't do ₹0 vision.
2. **Hard cap = two GCP projects.** Gemini API key from an AI Studio project
   with **no billing attached** (can't be charged — over-limit = 429, not a
   bill). Cloud Run lives in a separate project with billing + a kill switch:
   budget → Pub/Sub → function that detaches billing (official pattern:
   cloud.google.com/billing/docs/how-to/disable-billing-with-notifications;
   turnkey: github.com/Cyclenerd/poweroff-google-cloud-cap-billing). Budget
   ~₹500, alerts 50/90/100%.
3. **`cloudrun.sh` changes for this phase:** `--max-instances 1` (was 4);
   region `us-central1` (was `asia-south1` — Mumbai is pricing Tier 2, burns
   the free allowance ~40% faster; free 1 GiB egress is NA-only; flip back at
   pilot). Trim to ≤6 secrets (Secret Manager free = 6 versions): keep real
   secrets, move `SUPABASE_URL`/`STRIPE_PRICE_ID`/dummy Stripe to env vars,
   **skip `DEEPSEEK_API_KEY` entirely** — no DeepSeek spend this phase, all
   text routes to Flash.
4. **Privacy line = end of ₹0 phase:** Gemini free tier content is "used to
   improve" Google products (training); paid tier is excluded. Test questions
   fine; real students' questions NOT (DPDP). First real student ⇒ attach
   billing to the Gemini project, flip paid, restore DeepSeek/2.5-pro routing.
5. **Supabase free projects pause after ~1 week idle** → dead backend. Put a
   free uptime pinger (UptimeRobot) on `/healthz` every 5 min.
Cloud Run free tier itself (2M req / 180k vCPU-s / 360k GiB-s per month) fits
~6k solves/mo — not the constraint; Flash's 250 req/day is.

## Connections
- Tracks execution of → [[Opus-Execution-Plan]]
- Hub → [[Startup-MOC]]
