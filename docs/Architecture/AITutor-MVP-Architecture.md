---
tags: [type/note, domain/startup, startup/architecture, decision/anchor, status/active]
updated: 2026-07-11
---
# 🏗️ AITutor MVP Architecture (v3 — Expo + FastAPI + Supabase)

> Concrete build spec for the **current codebase** (`frontend/` + `backend/` in this repo). Complements [[Architecture-Options]] (the router/model-selection thinking) and [[Cognitive-Architecture]] (the conceptual layers) with the actual MVP shape: what ships in ~4 weeks, what's deliberately deferred, and why.

## ⚠️ Honest read: this is the fast path, not the moat — yet
This spec optimizes for **speed to a paying-student MVP**, not for [[Verification-Engine|the verifier]] that [[Startup-MOC]] calls the actual moat ("LLM proposes, math disposes"). The `/v1/ask` pipeline below is RAG-grounded (citations from ingested chapters) but has **no SymPy step-checker, no per-step verified/unsure badges** — the design that lived in [[Backend-Implementation-Plan]] (now superseded, verifier design preserved there for later). The deliberate bet: prove the RAG-tutor loop retains paying users first, then bolt the verifier on as its own service boundary (§2 of [[Architecture-Options]] already reserves that seam: `POST /verify {structured_solution} → verdicts[]`, stateless, swappable in). Don't market "verified" badges until that's actually wired up.

The previous Angular + Claude/SymPy-verifier-planned implementation is preserved on the `archive/angular-fastapi-redesign` branch — nothing was lost, this repo just leads with a different stack now.

---

## 0. Governing Principles
1. **Simplicity beats cleverness.** Every box in the architecture must justify its existence. The default answer to "should we add X?" is *no* until a real user forces it.
2. **Speed to MVP.** A paying-student-ready product in **~4 weeks**, not an enterprise platform. Anything that doesn't serve the first 100 users is deferred.
3. **Minimalist frontend.** Few screens, typography-first, one accent color, near-zero UI dependencies. The product is the *answer quality*, not the chrome.
4. **One-way doors avoided, everything else decided fast.** The only choices that are hard to reverse are the database and the auth provider — those get care. Everything else hides behind a thin interface and can be swapped in a day.

## 1. MVP Scope (ruthless cut)
| In (v1.0) | Out (deferred, with trigger to revisit) |
|---|---|
| Web app (responsive, installable PWA) | Native iOS/Android builds → *after 100 paying web users* (skips app-store review + IAP entirely) |
| Email + Google login | Apple SSO, phone OTP → *with native apps* |
| Text/image question → streamed, RAG-grounded answer | Explainer-video generation → *Phase 2* |
| One subject ingested end-to-end (Physics) | Full syllabus → *after retrieval quality is proven on one subject* |
| Free tier (10 Q/day) + one Pro plan via Stripe Checkout | Multiple tiers, credits, IAP → *with video + native apps* |
| Session history | Progress analytics, mastery models, streaks, [[Student-Model]] |
| Sentry + provider logs | OTel/Grafana stack → *when there's traffic worth graphing* |
| — | **SymPy/CAS verification + per-step badges** → the actual moat, next phase after the Q&A loop retains users |

The MVP kill-test question: *will a JEE aspirant pay ₹299/mo for grounded, syllabus-accurate answers?* Everything above the line answers that; nothing below it does. This is a narrower, faster kill-test than [[Roadmap]] Phase 0's verifier-accuracy gate — it precedes it, not replaces it.

## 2. High-Level Architecture (MVP)
Three deployables. One cloud region. No queues, no cross-cloud calls, no microservices.

```
┌───────────────────────────────────────────────┐
│         frontend/  Expo App (single codebase) │
│   Web-first PWA · React Native ready for      │
│   iOS/Android later · KaTeX math rendering    │
└──────────────────────┬────────────────────────┘
                       │ HTTPS (Supabase JWT)
                       ▼
┌───────────────────────────────────────────────┐
│         backend/  one FastAPI service          │
│   (single container on Google Cloud Run)     │
│   auth middleware · RAG · quotas · billing   │
└──────┬─────────────────┬──────────────────────┘
       │                 │
       ▼                 ▼
┌──────────────┐   ┌───────────────────────────┐
│  Supabase    │   │  LLM APIs                 │
│  Auth (JWT)  │   │  DeepSeek chat (primary)  │
│  Postgres    │   │  Gemini 2.5 (vision +     │
│   + pgvector │   │  failover)                │
│  Storage     │   └───────────────────────────┘
└──────────────┘         + Stripe Checkout (billing)
                         + Sentry (errors)
```

**Why these pieces:**
- **Supabase** replaces separate auth/DB/vector/storage services with one: managed Postgres with **pgvector** (RAG store *and* app data in one DB), JWT auth with Google OAuth built in, file storage for question images. Free tier covers the MVP; it's plain Postgres underneath, so exit is just `pg_dump`.
- **One FastAPI monolith** instead of serverless functions: no cold starts on the hot path, trivial local dev, one deploy, one log stream. SSE streaming is first-class. This matches the Option A pipeline direction in [[Architecture-Options]] (FastAPI + Postgres/pgvector) — the two docs now agree, and Option A → Option B (gateway) → verifier-as-service is still the intended evolution.
- **DeepSeek primary / Gemini fallback** — DeepSeek's automatic context caching prices a byte-stable system-prompt prefix at a fraction of cache-miss cost (indicative, verify at build time); Gemini 2.5 handles vision (photographed problems) and failover.
- **Stripe Checkout on the web** means no in-app-purchase compliance, no webhook zoo — two events handled, done.

## 3. Backend — Low-Level Design (`backend/`)
```
backend/
├── app/
│   ├── main.py               FastAPI app, CORS, error envelope, Sentry init
│   ├── deps.py                auth dependency (verify Supabase JWT), profile upsert
│   ├── routes/
│   │   ├── ask.py             POST /v1/ask          (SSE stream)
│   │   ├── sessions.py        GET  /v1/sessions
│   │   ├── billing.py         POST /v1/billing/checkout · /webhook
│   │   └── me.py              GET/DELETE /v1/me
│   ├── core/
│   │   ├── rag.py             embed → pgvector retrieve
│   │   ├── prompts.py         cache-stable system prompt + message assembly
│   │   ├── embeddings.py      embedding adapter (swap seam)
│   │   ├── llm.py             DeepSeek/Gemini clients, routing, metering (swap seam)
│   │   └── quota.py           daily-cap check + lazy reset (pure, unit-tested)
│   └── ingest/cli.py           `python -m app.ingest.cli chapter.md` (offline, admin-run)
├── tests/                      core logic tested with zero cloud mocks
├── schema.sql                  five tables incl. pgvector HNSW index
└── Dockerfile
```
Rules: pydantic validation at every boundary; one error envelope `{error: {code, message, request_id}}`; vendor SDKs only inside `core/llm.py`, `core/embeddings.py`, `routes/billing.py` (the swap seam — same Replaceability Principle as [[Durable-Moat]]).

**API surface (complete):** `POST /v1/ask`, `GET /v1/sessions`, `GET|DELETE /v1/me`, `POST /v1/billing/checkout`, `POST /v1/billing/webhook`, `GET /healthz`.

**Data model — five tables** (`profiles`, `sessions`, `chunks` w/ pgvector HNSW, `billing_events`, plus Supabase's `auth.users`). Quota reset is lazy (compare `questions_reset_on` to today on read, no cron); the quota check-and-increment is one atomic `UPDATE`. **No credit ledger yet** — one flat Pro plan needs none; returns with video credits in Phase 2.

**The ask pipeline (hot path):** verify JWT (cached JWKS) → quota check → embed question → pgvector top-8 cosine within chapter, keep ≥0.75 similarity top 4 → assemble prompt (byte-stable system block + context + trimmed history) → route (image→Gemini, text→DeepSeek, DeepSeek 5xx→Gemini) → stream SSE tokens → persist session row + bump quota. Routing is three `if` statements, not a router service — see [[Architecture-Options]] §1 Option A for why that's the right level of machinery at this stage.

**Billing (the whole design):** Checkout session creation → webhook with **one-line idempotency** (`insert stripe_event_id … on conflict do nothing`) → tier flip. IAP, proration, credit packs are Phase 2+.

## 4. Frontend — Low-Level Design (`frontend/`, minimalist by construction)
Four screens total — Ask, Answer/Thread, History, Account — no tabs beyond these, no onboarding carousel. System font stack, one type scale (15/17/22/28), monochrome + one indigo accent, motion budget ≈ zero (the streaming text itself is the only animation). No component library — ~6 hand-rolled primitives (`Screen`, `Button`, `Input`, `Badge`, `Bubble`) instead of fighting a theme system.

```
frontend/
├── app/              expo-router file routes: index (Ask), thread/[id], history, account, sign-in
├── components/        the ~6 owned primitives
├── lib/                theme tokens · supabase auth · API client + SSE consumer · LaTeX (KaTeX web / mono-fallback native)
└── state/              one Zustand store: the live streaming answer buffer; TanStack Query for everything else
```
PWA installable, last-20-sessions cached — covers "app-like" until native builds ship in Phase 2 (Expo makes that mostly free when it's time).

## 5. Cross-Cutting (MVP-sized)
- **Security:** Supabase RLS as defense-in-depth; secrets in the host's secret store; per-user rate limit on `/v1/ask`; retrieved chunks delimited in the prompt as reference-data-only (prompt-injection containment).
- **Observability:** Sentry (client + API, `request_id` correlated) + host log stream. Grafana/OTel: not yet — [[Architecture-Options]]'s gateway-layer tracing (§1 Option B) is the natural next step once there's traffic worth graphing.
- **CI/CD:** GitHub Actions — typecheck, `pytest`, docker build, deploy on merge to `main`.

## 6. Phase 2 — Video Generation Engine (deferred, design retained)
Ship only after the Q&A loop retains paying users. `backend/`: hold credit, enqueue job → SQS → Lambda (FFmpeg+Manim, 12-min timeout) → script-gen (DeepSeek) + Edge-TTS + stock/Manim b-roll → FFmpeg stitch → S3 → HMAC callback → credit captured → push. Credits are **held, not spent**, until READY; this is the only place a second cloud enters, fully async. Native apps + IAP land in this phase too.

## 7. Scale-Out Path (kept as an option, not a plan)
A prior draft of this spec explored a tri-cloud design (Cognito + Azure Functions/Cosmos + AWS Lambda video pipeline) purely for free-tier arbitrage. That's a distraction pre-MVP — revisit only if infra bill exceeds ~$500/mo *and* arbitrage would meaningfully recover it, a hard requirement lands for a capability only one cloud has, or auth MAU outgrows Supabase's pricing curve. Until then: one FastAPI container + managed Postgres scales further than intuition suggests, and the vendor-SDK swap seams (§3) keep the door open without paying the tri-cloud tax today.

## 8. Cost Model (MVP, indicative — re-verify at build time)
| Item | 0–1k MAU | Notes |
|---|---|---|
| Supabase | $0–25 | free tier → Pro at scale |
| API host (Cloud Run) | $0–10 | scale-to-zero pre-launch; `min-instances=1` at pilot |
| DeepSeek + embeddings | ~$3–15 | cache-hit heavy, metered per session |
| Gemini (vision/failover) | ~$2–10 | ~5% of questions |
| Stripe / Sentry | $0 + 2.9% | usage-based |
| **Total** | **≈ $10–60/mo** | vs. weeks of tri-cloud setup saved |

## 9. Build Plan (4 weeks to MVP)
| Week | Deliverable |
|---|---|
| 1 | Supabase project + schema; FastAPI skeleton; auth middleware; `/v1/ask` streaming DeepSeek *without* RAG (walking skeleton) |
| 2 | Ingestion CLI + pgvector retrieval on Physics-Optics; prompt/caching structure; Gemini image path; quota enforcement |
| 3 | Expo app: Ask/Thread/History/Account, KaTeX streaming, Google login; Sentry both sides |
| 4 | Stripe checkout + webhook; PWA polish; staging→prod pipeline; ingest 3 more chapters; invite 20 beta students |

**Definition of done for MVP:** a student signs up with Google, asks a JEE optics question with a photo, watches a grounded LaTeX answer stream in under 10 s, hits the free cap, and upgrades with a card — all on their phone's browser.

**Definition of done for "the moat is real"** (next, not this phase): the same flow, but with SymPy step-verification wired behind the retained `/verify` seam and per-step ✓/⚠ badges rendered in `Bubble` — gated on [[Roadmap]] Phase 0's ≥95% accuracy / ≥99% step-precision bar, not shipped early just because it demos well.

## Connections
- Implements the MVP slice of → [[Architecture-Options]] (Option A) · [[Cognitive-Architecture]]
- Defers → [[Verification-Engine]] (the actual moat), [[Student-Model]], [[Backend-Implementation-Plan]] (superseded verifier design, preserved for the next phase)
- Codebase mapped in → [[Codebase-AITutor]] · Phased against → [[Roadmap]] · Hub → [[Startup-MOC]]
