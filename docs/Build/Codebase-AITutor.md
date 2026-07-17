---
tags: [type/note, domain/startup, startup/build, reference]
repo: https://github.com/avideo-guru/AITutor
stack: Expo (React Native, web-first) + FastAPI + Supabase
updated: 2026-07-11
---
# 💻 Codebase — AITutor (MVP scaffold)

> **Repo:** https://github.com/avideo-guru/AITutor · **Stack:** Expo/React Native (`frontend/`) + FastAPI (`backend/`) + Supabase Postgres/pgvector. **State (2026-07-11):** MVP scaffold generated from [[AITutor-MVP-Architecture]] — real RAG plumbing and streaming, but **not yet wired to a live Supabase project**, no content ingested, no verifier.

## 🔭 What it actually is right now (honest read)
A complete, testable MVP skeleton — not a mockup, but not live either:
- `frontend/` — Expo app, four screens (Ask, Thread, History, Account) + sign-in, `expo-router`. Streams `/v1/ask` over SSE into a Zustand buffer, renders LaTeX with KaTeX on web. **No component library** — six hand-rolled primitives in `components/`. `npx tsc --noEmit` passes; the web build boots and renders the sign-in screen with zero console errors (verified in-browser this session).
- `backend/` — FastAPI monolith. `/v1/ask` does real embed → pgvector retrieve → prompt assembly → DeepSeek (Gemini fallback/vision) → SSE stream → persist session + meter cost. Stripe checkout + webhook (idempotent), quota enforcement (atomic UPDATE, lazy daily reset), DPDP-compliant account delete. **9/9 unit tests pass** (quota logic, prompt assembly, markdown chunker) — these run with zero cloud mocks, against pure functions only.
- **What's not real yet:** no Supabase project has been created, so `schema.sql` hasn't been run and nothing has actually been ingested or asked end-to-end against a live LLM. `frontend/.env` and `backend/.env` are placeholders. **No verifier at all** — see the honest-read warning at the top of [[AITutor-MVP-Architecture]]; this is a RAG tutor, not yet "LLM proposes, math disposes."
- The previous Angular prototype (`AiTutorService` with hardcoded canned replies) plus a second, more-built FastAPI backend (Claude + planned SymPy verifier, SQLite) are **preserved on the `archive/angular-fastapi-redesign` branch** — nothing was deleted, the repo just leads with this stack now. That archived backend's verifier design is still the intended next phase; see the supersession note atop [[Backend-Implementation-Plan]].

## 🧩 Where it plugs into our architecture
```
[ AITutor repo = Experience/Delivery + basic Reasoning layer ]   ← you are here (frontend/ + backend/)
        │  (the seam: lib/api.ts ↔ backend/app/routes/ask.py)
        ▼
[ RAG (embed → pgvector → prompt) → DeepSeek/Gemini ]  ← built, not yet live
        ▼
[ TODO: Verifier service boundary → Student Model → full Cognitive-Architecture stack ]
```
`backend/app/core/llm.py` and `core/embeddings.py` are the vendor-swap seams — the [[Durable-Moat|Replaceability Principle]] applied: DeepSeek/Gemini/embedding model can each be swapped without touching route handlers.

## ⚠️ Alignment notes
- **Scope is correctly narrow:** one subject (Physics) end-to-end per [[AITutor-MVP-Architecture]] §1 — matches [[Market-and-GTM]]'s JEE/NEET focus. Don't ingest the full syllabus before retrieval quality is proven on Optics.
- **Verified rendering is not built:** `Bubble` renders plain streamed answers with source-ref badges (citations), not per-step ✓/⚠ verification badges. That UI + the backend `/verify` service boundary is next-phase work, gated on [[Roadmap]] Phase 0's accuracy bar — don't call anything "verified" in-product until it is.
- **The toggle:** [[Fast-vs-Guided-Toggle]] is not built. Current UI is fast-mode only.
- **India rails:** WhatsApp delivery ([[Market-and-GTM]]) not built; this Expo app is the PWA half only so far.

## ▶️ Concrete next steps
- [ ] Stand up a real Supabase project, run `backend/schema.sql`, fill both `.env` files, confirm the end-to-end loop (sign up → ask → stream → history) against live DeepSeek/Gemini.
- [ ] Ingest real Physics-Optics content via `backend/app/ingest/cli.py`; tune the similarity floor (currently 0.75) against real retrieval quality.
- [ ] Deploy `backend/` (Google Cloud Run, region `asia-south1`) and `frontend/` as a PWA; wire Stripe live keys.
- [ ] Design and build the **verifier service boundary** (`POST /verify`) per [[Architecture-Options]] §2 and the preserved design in [[Backend-Implementation-Plan]] — this is what turns the RAG tutor into the actual moat.
- [ ] Build the **StepCard**/verified-badge UI once the verifier exists (extends `Bubble`, doesn't replace it).

## 🔌 Working with this repo from the vault
It lives on GitHub (not inside the vault). To hack on it via Claude Code:
```bash
git clone https://github.com/avideo-guru/AITutor
cd AITutor
# frontend
cd frontend && cp .env.example .env && npm install && npm run web   # http://localhost:8081
# backend (separate shell)
cd backend && cp .env.example .env && pip install -r requirements-dev.txt && uvicorn app.main:app --reload --port 8080
```
Both READMEs (`frontend/README.md`, `backend/README.md`) have full setup, including the Supabase project steps. Keep **product/architecture decisions here in the vault**; keep **code in the repo** — this note is the bridge between them.

## Connections
- Implements the MVP slice of → [[AITutor-MVP-Architecture]] · (UI of) [[Cognitive-Architecture]] (Teaching/Delivery layer)
- Must integrate → [[Verification-Engine]], [[Student-Model]], [[Fast-vs-Guided-Toggle]]
- Prior stack preserved in → [[Backend-Implementation-Plan]] (superseded, `archive/angular-fastapi-redesign` branch)
- Ships per → [[Roadmap]], [[Market-and-GTM]] · Hub → [[Startup-MOC]]
