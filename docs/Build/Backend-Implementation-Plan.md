---
tags: [type/note, domain/ai, domain/startup, status/active]
updated: 2026-07-10
---
> 🧠 Part of the [[Startup-MOC|Startup brain]] · implements → [[A1-Math-Verified-Tutor-Dev-Plan]] · [[High Level Architecture]]

# Backend Implementation Plan (v1 — "Basic Backend")

**Goal:** replace the simulated `AiTutorService` in the Angular app with a real backend that does three things: (1) stream real AI tutor answers, (2) verify math steps with a real engine, (3) persist chats + study planner. Everything else (auth at scale, WhatsApp, voice, fine-tuning) is explicitly out of scope for v1.

---

## 0. Stack Decision

| Piece | Choice | Why |
|---|---|---|
| API framework | **FastAPI (Python)** | The verifier is SymPy-based (Python). One language, one service, one deploy for v1. |
| LLM | **Claude `claude-opus-4-8`** via official `anthropic` Python SDK | Adaptive thinking (`thinking: {"type": "adaptive"}`), structured outputs for step JSON, SSE streaming. |
| Verifier | **SymPy + NumPy** in-process module (not a separate service yet) | "LLM proposes, math disposes." Split into its own service only when latency demands it. |
| DB | **SQLite → Postgres** | SQLite for week 1–2 (zero ops), same SQLAlchemy models port to Postgres unchanged. |
| Streaming | **SSE** (`text/event-stream`) | Matches the Anthropic streaming model; trivial to consume from Angular with `fetch` + ReadableStream. |
| Auth (v1) | Anonymous device ID → later phone OTP | Don't block the demo on auth. |

Single repo layout:

```
backend/
  app/
    main.py            # FastAPI app, CORS for localhost:4200
    routers/chat.py    # POST /api/chat (SSE)
    routers/tasks.py   # CRUD /api/tasks
    llm.py             # Anthropic client, prompt templates
    verifier/          # core moat — SymPy step checker
      schema.py        # structured step JSON (from A1 plan §1.1)
      cas.py           # symbolic equivalence checks
      numeric.py       # random-sample numeric testing, unit checks
    models.py          # SQLAlchemy: users, sessions, messages, tasks
  tests/
```

---

## 1. API Contract (what the Angular app calls)

| Endpoint | Method | Body / Returns |
|---|---|---|
| `/api/chat` | POST → SSE | `{session_id, subject, message}` → stream of events: `token` (text chunk), `verification` (final verdict per step), `done` |
| `/api/sessions` | POST/GET | create / list chat sessions |
| `/api/sessions/{id}/messages` | GET | chat history for a session |
| `/api/tasks` | GET/POST | study-planner tasks, filtered by `?subject=` |
| `/api/tasks/{id}` | PATCH/DELETE | toggle complete / delete |
| `/api/health` | GET | liveness |

SSE event shapes (matches what the UI already renders):

```
event: token          data: {"text": "Calculus is..."}
event: verification   data: {"verified": true, "steps": [{"idx":1,"status":"pass"}, ...]}
event: done           data: {"message_id": "...", "usage": {...}}
```

The `verification` event drives the existing `✓ Steps machine-checked` / `△ Not verified` badges.

---

## 2. The Chat Pipeline (core flow)

```
user question
  → LLM call #1: emit STRUCTURED solution (step JSON per A1 §1.1) via output_config.format
  → verifier: each step → CAS equivalence + numeric sampling + unit check
  → all pass  → LLM call #2 (or same response): stream the prose explanation, badge = verified
  → any fail  → one repair attempt with verifier feedback → still fails = honest abstention, badge = unverified
```

LLM call sketch (per current API surface):

```python
from anthropic import Anthropic
client = Anthropic()  # ANTHROPIC_API_KEY from env

# Call 1 — structured steps for the verifier
resp = client.messages.parse(
    model="claude-opus-4-8",
    max_tokens=16000,
    system=TUTOR_SYSTEM_PROMPT,          # frozen — enables prompt caching
    output_config={"format": {"type": "json_schema", "schema": STEP_SCHEMA}},
    messages=history + [{"role": "user", "content": question}],
)

# Call 2 — stream the student-facing explanation
with client.messages.stream(
    model="claude-opus-4-8",
    max_tokens=16000,
    thinking={"type": "adaptive"},
    system=TUTOR_SYSTEM_PROMPT,
    messages=...,
) as stream:
    for text in stream.text_stream:
        yield sse("token", {"text": text})
```

Cost controls from day one: prompt caching (`cache_control` on the system prompt), cap history at N turns, `claude-haiku-4-5` for the cheap paths (classifying subject, short factual answers) once measured.

---

## 3. Verifier v1 (the moat, minimum honest version)

Scope for v1 — exactly what SymPy is good at:

1. **Algebraic equivalence:** `simplify(lhs - rhs) == 0` between consecutive steps.
2. **Numeric spot-check:** substitute 5–10 random values for free symbols; reject on mismatch beyond tolerance. Catches what `simplify` can't prove.
3. **Unit/dimension check** for physics: parse quantities (`20 m/s`), verify dimensional consistency per step.
4. **Verdict per step:** `pass` / `fail` / `cannot_verify`. Any `fail` or `cannot_verify` on a load-bearing step ⇒ the whole answer is "not verified — flagged honestly." Never fake a pass.

Explicit non-goals for v1: geometry proofs, calculus limit rigor, combinatorics arguments — those return `cannot_verify` honestly.

---

## 4. Persistence (minimum schema)

```sql
users(id, device_id, created_at)
chat_sessions(id, user_id, subject, created_at)
messages(id, session_id, sender, text, verified BOOLEAN NULL, step_json JSON NULL, created_at)
tasks(id, user_id, subject, title, completed, created_at)
```

`step_json` is stored on every tutor message — this is the beginning of the diagnostic dataset (A1 §"diagnostic flywheel").

---

## 5. Angular Changes (small, contained)

- `AiTutorService.streamResponse()` → `fetch('/api/chat', {method:'POST'})` + ReadableStream parsing of SSE; keep the same `Observable<string>` signature so components don't change.
- `isVerifiable()` disappears — the badge now comes from the backend's `verification` event (add a `verified$` channel or extend the observable to emit typed events).
- Study planner signals swap their in-memory array for `/api/tasks` calls (keep optimistic updates).
- Dev proxy: `proxy.conf.json` → `/api` → `http://localhost:8000` so no CORS pain in dev.

---

## 6. Phases & Order of Work

| Phase | Deliverable | Definition of done |
|---|---|---|
| **P0 (½ day)** | FastAPI skeleton + `/api/health` + CORS + SQLite | Angular hits `/api/health` through proxy |
| **P1 (2–3 days)** | `/api/chat` SSE with real Claude streaming, no verifier yet (badge = "cannot verify") | Real answers stream into the existing chat UI |
| **P2 (1 week)** | Verifier v1 (algebra + numeric + units) wired into the pipeline; structured-step call | ≥20 canned JEE problems: verified answers badge green, broken steps get caught (seed known-wrong solutions in tests) |
| **P3 (2–3 days)** | Persistence: sessions, message history, planner CRUD | Refresh the page, chat + tasks survive |
| **P4 (2 days)** | Hardening: rate limit per device, token budget caps, error states in UI, Dockerfile | `docker compose up` runs the whole stack |

**Deferred (v2+):** phone-OTP auth, wrong-step diagnosis of *student* attempts (the paste-your-attempt feature), Hinglish/voice, WhatsApp delivery, fine-tuned cheap model, Postgres + hosted deploy.

---

## 7. Risks / Open Questions

- **Latency:** two LLM calls + verification vs the "<8s to a verified answer" promise. Mitigations: stream call 2 while verifier runs, prompt caching, Haiku for classification. Measure in P2 before promising.
- **Structured-step quality:** if the model's step JSON is sloppy, the verifier's value collapses. P2 must include a small eval set (the A1 plan's problem bank) run on every prompt change.
- **API key custody:** backend-only; never ship the key to the Angular client.
