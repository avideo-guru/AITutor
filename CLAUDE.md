# AITutor — working memory

Grounded AI tutoring for IIT-JEE/NEET aspirants. RAG-grounded Q&A now; a
verified-reasoning engine ("LLM proposes, math disposes") is the long-term
moat. See [docs/Startup-MOC.md](docs/Startup-MOC.md).

## Stack
- `frontend/` — Expo/React Native, web-first PWA. Deployed to **Cloudflare**
  (Workers static assets — see `frontend/wrangler.jsonc`, `assets.directory:
  dist`, SPA fallback).
- `backend/` — FastAPI monolith. RAG (Supabase Postgres + pgvector) →
  DeepSeek primary / Gemini vision+failover, SSE streaming, Stripe billing.
  Deployed to **Google Cloud Run** (single container, region `asia-south1` /
  Mumbai; scale-to-zero pre-launch, `min-instances=1` at pilot). Host-agnostic
  — any container host works if economics change.
- **Supabase** — auth (JWKS-verified, not shared HS256 secret — see commit
  `dd930f6`), Postgres + pgvector, file storage.

## Cross-account orchestration (IMPORTANT — read every session)

This repo is worked on by **two people/accounts on two machines** sharing one
repo. [docs/Status.md](docs/Status.md) is the async message board between
them — it is the source of truth for "who's doing what, what's blocking."

- `feat/backend-phase0` — backend work, other account, executes
  [docs/Opus-Execution-Plan.md](docs/Opus-Execution-Plan.md) from Phase 0.
- `feat/ui-redesign` — UI/UX work, this account/laptop.
- `main` — merge only via PR once a branch is stable; never push WIP directly.

Workflow each session:
1. Pull `main` before starting (`git checkout <branch> && git merge main`).
2. Push small, push often — reviewable chunks, not one giant end-of-session diff.
3. **Update the relevant section of `docs/Status.md` before ending a session**
   (Status/Last update/Done/Next/Blocking) — this is the handoff to the other
   account.
4. Merge to `main` via PR, not a direct push.

**Standing instruction from the user:** after doing any work in this repo,
update `docs/Status.md` to reflect it, then commit and push that change
**directly to `main`** immediately, without asking for confirmation first.
Status.md is the cross-account handoff board and must always be current on
`main` (the branch both sides pull from) — delay, or leaving it on an
unmerged feature branch, defeats the purpose. This is the one carve-out from
rule 4 above ("merge to `main` via PR, never push WIP directly"): it is
scoped to `docs/Status.md` **only**, never code, this file, or any
destructive git operation.

## Deployment / auth notes
- **Final stack:** Cloudflare (frontend static assets) · Supabase
  (auth + Postgres/pgvector + storage) · Google Cloud Run (FastAPI backend).
  Railway/Fly/Render were considered and dropped in favor of Cloud Run
  (Mumbai region, scale-to-zero, SSE-friendly, generous free tier).
- Cloudflare deploy is static-assets-only (Workers static site from
  `frontend/dist`), per `frontend/wrangler.jsonc`.
- Cloud Run: single container from `backend/Dockerfile`, region `asia-south1`.
  Backend streams SSE, so the host must allow long-lived responses (rules out
  short-timeout serverless). Host-agnostic — the image runs anywhere.
- Supabase auth: JWTs are verified via JWKS (fixed from shared HS256 secret
  in `dd930f6`). Google OAuth is brokered *through* Supabase (Google → Supabase
  JWT → backend JWKS verify) — this is why Supabase, not Firebase: pgvector,
  atomic-SQL quotas, traces, and Postgres FTS are all load-bearing.
- Supabase MCP: the live project (`xdszkwjkaamyycirfslz`) is connected on the
  **UI/laptop account**, which owns live-infra work. The backend account's MCP
  showed 0 projects — confirm which account/org is authenticated before
  inspecting the live DB.

## Prior implementation
Earlier Angular + FastAPI/SQLite build preserved on
`archive/angular-fastapi-redesign` — nothing was deleted on stack change.
