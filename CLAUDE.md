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

**Standing instruction from the user:** whenever `docs/Status.md` is edited
in this repo, commit and push that change immediately without asking for
confirmation first — it's the cross-account handoff mechanism and delay
defeats the purpose. This permission is scoped to `docs/Status.md` pushes
only, not other files or destructive git operations.

## Deployment / auth notes
- Cloudflare deploy is static-assets-only (Workers static site from
  `frontend/dist`), per `frontend/wrangler.jsonc`.
- Supabase auth: JWTs are verified via JWKS (fixed from shared HS256 secret
  in `dd930f6`).
- Supabase MCP (`list_projects`) returned no projects for the currently
  connected account — if you need to inspect the live Supabase project,
  confirm which account/org the MCP is authenticated as first.

## Prior implementation
Earlier Angular + FastAPI/SQLite build preserved on
`archive/angular-fastapi-redesign` — nothing was deleted on stack change.
