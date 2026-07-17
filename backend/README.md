# AITutor API

FastAPI monolith for the AITutor MVP (see `../AITutor.md` §3). One container,
Supabase Postgres + pgvector, DeepSeek/Gemini behind a single adapter file.

## Setup

1. Create a Supabase project, then apply the schema with the Supabase CLI —
   **not** by pasting `schema.sql` into the SQL editor. That file is no longer
   the source of truth; the immutable migrations in `supabase/migrations/` are
   (why → `docs/Decisions/ADR-011-migrations-are-immutable.md`).

   ```sh
   supabase link --project-ref <ref>
   supabase db push
   ```

   ⚠️ If the project **already has tables** (the live one does), read
   `supabase/README.md` § "Reconciling the live project" *before* pushing — the
   live migration ledger and this repo do not yet agree.

   Then create a **public storage bucket** named `question-images` (buckets
   aren't DDL, so this stays a manual step).
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

**Google Cloud Run** (canonical host; region `asia-south1` / Mumbai for IST
latency, scale-to-zero pre-launch, supports SSE streaming): build the
Dockerfile, deploy the image, set the env vars from `.env.example`, point
Stripe's webhook at `https://<host>/v1/billing/webhook`. The service is a plain
container, so any other host (Fly / Render / a VM) also works if economics
change.
