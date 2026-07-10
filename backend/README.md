# AITutor Backend (FastAPI)

## Run (Windows)

```powershell
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

The Angular dev server proxies `/api/*` to `http://localhost:8000` (see `proxy.conf.json`), so run both and open http://localhost:4200.

## Switching the model provider

Providers live behind one interface (`app/llm/base.py`):

- `mock` (default) — canned streaming answers, zero cost.
- `anthropic` — set `LLM_PROVIDER=anthropic` and `ANTHROPIC_API_KEY` in `backend/.env` (model: `claude-haiku-4-5`).
- Later: local / own fine-tuned model = one new file implementing `LLMProvider`.

## API

- `POST /api/chat` — SSE stream: `token`* → `verification` → `done` (or `error`).
- `GET /api/health` — liveness + active provider.
