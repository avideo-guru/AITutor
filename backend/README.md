# AITutor API

FastAPI monolith for the AITutor MVP (see `../AITutor.md` §3). One container,
Supabase Postgres + pgvector, DeepSeek/Gemini behind a single adapter file.

## Setup

1. Create a Supabase project. Run `schema.sql` in the SQL editor. Create a
   **public storage bucket** named `question-images`.
2. `cp .env.example .env` and fill in the values (Supabase → Settings →
   Database for `DATABASE_URL`, Settings → API for `SUPABASE_URL`).
3. Install & run:

   ```sh
   python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements-dev.txt
   uvicorn app.main:app --reload --port 8080
   ```

4. Ingest content (repeatable — idempotent by content hash):

   ```sh
   python -m app.ingest.cli notes/optics.md --subject PHY --chapter PHY::optics::12
   ```

5. Stripe: create a subscription Price, set `STRIPE_PRICE_ID`; forward webhooks
   locally with `stripe listen --forward-to localhost:8080/v1/billing/webhook`.

## Tests

```sh
pytest          # pure-logic tests: quota, chunker, prompt assembly
```

## Endpoints

| Method | Path | Notes |
|---|---|---|
| POST | `/v1/ask` | SSE stream: `token` → `meta` → `done` (or `error`) |
| GET | `/v1/sessions?cursor=` | cursor = ISO timestamp of last item |
| GET / DELETE | `/v1/me` | profile + quota / full data purge |
| POST | `/v1/billing/checkout` | returns Stripe Checkout URL |
| POST | `/v1/billing/webhook` | Stripe events (idempotent) |
| GET | `/healthz` | liveness + DB probe |

Auth: `Authorization: Bearer <supabase access token>` on everything except the
webhook and `/healthz`. Errors always use
`{"error": {"code", "message", "request_id"}}`.

## Deploy

Any container host (Railway / Fly / Render): build the Dockerfile, set the env
vars from `.env.example`, point Stripe's webhook at
`https://<host>/v1/billing/webhook`.
