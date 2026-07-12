"""The orchestrator — the fixed v1 pipeline ([[Target-Architecture]] §2). It is
the only component that knows the stage order:

    Retrieve → (build prompt) → Reason(stream) → [Verify: P5] → Teach(SSE) → Log

`run()` is an async generator of SSE frames; `routes/ask.py` stays thin (parse +
quota + hand off). No agent framework — agentic behaviour arrives later as
bounded loops *inside* a stage, never as free-running planning. Behaviour here
is byte-identical to the pre-P1 inline generator; the 23 behavioural tests are
the guard.
"""

import asyncio
import hashlib
import json
import logging
import time
import uuid
from typing import AsyncIterator

from app import sse
from app.core.prompts import build_messages
from app.models.base import ImageRejected, Usage
from app.models.router import stream_answer
from app.retrieval import vector

log = logging.getLogger(__name__)

# Holds references to detached persistence tasks (the disconnect path) so the
# event loop doesn't garbage-collect them mid-write. See run()'s finally.
_pending: set[asyncio.Task] = set()

HISTORY_PAIRS = 4            # prior Q/A pairs fed back as context
HISTORY_ANSWER_CHARS = 1000  # per-answer truncation budget


def _truncate_history_answer(answer: str, limit: int = HISTORY_ANSWER_CHARS) -> str:
    """Keep the history token budget bounded, but preserve the boxed final
    answer line — that's the part a follow-up most likely refers back to."""
    if len(answer) <= limit:
        return answer
    head = answer[:limit].rstrip()
    boxed = next(
        (ln.strip() for ln in reversed(answer.splitlines()) if "\\boxed" in ln), ""
    )
    if boxed and boxed not in head:
        return f"{head}\n…\n{boxed}"
    return head + "…"


async def _load_history(pool, thread_id, user_id) -> list[dict]:
    """Last N answered turns of this thread, owned by the caller, oldest-first,
    as OpenAI-style messages. Filtering by user_id means another user's
    thread_id simply yields no history — no leak, no cross-user context."""
    rows = await pool.fetch(
        """
        select question, answer from sessions
        where thread_id = $1 and user_id = $2
          and answer is not null and answer <> ''
        order by created_at desc
        limit $3
        """,
        thread_id, user_id, HISTORY_PAIRS,
    )
    msgs: list[dict] = []
    for r in reversed(rows):
        msgs.append({"role": "user", "content": r["question"]})
        msgs.append({"role": "assistant",
                     "content": _truncate_history_answer(r["answer"])})
    return msgs


def _prompt_hash(messages: list[dict]) -> str:
    joined = json.dumps(messages, sort_keys=True, default=str)
    return hashlib.sha256(joined.encode()).hexdigest()[:32]


async def _refund_quota(pool, user_id) -> None:
    """Edge #2: LLM died mid-stream with zero tokens shown — the student got
    nothing, so reverse the claim. Reverses exactly what the atomic claim bumped
    (daily always; monthly for Pro). Never called on client disconnect."""
    try:
        await pool.execute(
            """
            update profiles set
              questions_today = greatest(questions_today - 1, 0),
              questions_month = case when plan = 'pro'
                then greatest(questions_month - 1, 0) else questions_month end
            where id = $1
            """,
            user_id,
        )
    except Exception:
        log.exception("quota refund failed")


async def run(pool, profile: dict, body) -> AsyncIterator[str]:
    """Drive one ask, yielding SSE frames. Quota is already claimed by the
    caller (routes/ask.py) — this owns everything from retrieval onward."""
    question = body.text or "Solve the problem shown in the attached image."

    # A new ask starts a fresh thread; a follow-up carries the client's thread_id.
    thread_id = body.thread_id or uuid.uuid4()

    # Retrieval — errors degrade (answer without context), never fail the stream.
    stage_latency: dict[str, int] = {}
    t = time.perf_counter()
    try:
        chunks = await vector.retrieve(pool, question, body.chapter)
        retrievers_used = ["vector"]
    except Exception:
        log.exception("retrieval failed; answering without context")
        chunks = []
        retrievers_used = []
    stage_latency["retrieve_ms"] = int((time.perf_counter() - t) * 1000)

    history: list[dict] = []
    if body.thread_id is not None:
        try:
            history = await _load_history(pool, thread_id, profile["id"])
        except Exception:
            log.exception("history load failed; answering without it")

    messages = build_messages(chunks, history, question)
    prompt_hash = _prompt_hash(messages)
    chunk_json = [
        {
            "id": str(c["id"]) if c.get("id") is not None else None,
            "source_ref": c.get("source_ref"),
            "score": round(float(c["similarity"]), 4) if c.get("similarity") is not None else None,
            "rank": i,
        }
        for i, c in enumerate(chunks)
    ]

    answer_parts: list[str] = []
    usage: Usage | None = None
    persisted = False
    session_row = None

    async def persist(*, disconnected: bool, gate_outcome: str):
        """Write session + trace atomically. Runs on the happy path, the
        LLM-failure path, and (detached) the client-disconnect path — but only
        once. Must never raise into the request: the answer is already streamed,
        so a persistence failure is logged, not surfaced."""
        nonlocal persisted, session_row
        if persisted:
            return session_row
        persisted = True
        answer = "".join(answer_parts)
        try:
            async with pool.acquire() as conn:
                async with conn.transaction():
                    session_row = await conn.fetchrow(
                        """
                        insert into sessions
                          (user_id, thread_id, question, image_url, answer,
                           model, tokens_in, tokens_out, cost_usd)
                        values ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                        returning id, created_at
                        """,
                        profile["id"], thread_id, question, body.image_url,
                        answer,
                        usage.model if usage else None,
                        usage.tokens_in if usage else None,
                        usage.tokens_out if usage else None,
                        usage.cost_usd if usage else None,
                    )
                    await conn.execute(
                        """
                        insert into traces
                          (session_id, retrievers_used, chunks, prompt_hash,
                           gate_outcome, stage_latency_ms, disconnected)
                        values ($1, $2, $3::jsonb, $4, $5, $6::jsonb, $7)
                        """,
                        session_row["id"], retrievers_used,
                        json.dumps(chunk_json), prompt_hash, gate_outcome,
                        json.dumps(stage_latency), disconnected,
                    )
        except Exception:
            log.exception("failed to persist session/trace")
        return session_row

    stream_t0 = time.perf_counter()
    try:
        try:
            async for item in stream_answer(messages, body.image_url):
                if isinstance(item, Usage):
                    usage = item
                else:
                    answer_parts.append(item)
                    yield sse.format_event(sse.TOKEN, {"t": item})
        except Exception as exc:
            # LLM died. Failover already had its chance (only fires before the
            # first token, by design — that policy lives in the Router). Record
            # the failure as a trace.
            log.exception("llm stream failed")
            stage_latency["stream_ms"] = int((time.perf_counter() - stream_t0) * 1000)
            if not answer_parts:
                # Zero tokens shown → refund (edge #2). Some tokens shown →
                # partial answer delivered, no refund.
                await _refund_quota(pool, profile["id"])
                gate = "error"
            else:
                gate = "partial"
            await persist(disconnected=False, gate_outcome=gate)
            if isinstance(exc, ImageRejected):
                # Image fetch/validation failed before any token — tell the
                # student what to fix instead of blaming the tutor.
                yield sse.format_event(sse.ERROR, {
                    "code": "IMAGE_REJECTED",
                    "message": "That image couldn't be used. Upload a photo "
                               "under 4 MB (JPEG/PNG) and try again.",
                })
            else:
                yield sse.format_event(sse.ERROR, {
                    "code": "LLM_UNAVAILABLE",
                    "message": "The tutor is unavailable. Try again.",
                })
            return

        stage_latency["stream_ms"] = int((time.perf_counter() - stream_t0) * 1000)
        row = await persist(disconnected=False, gate_outcome="show")
        yield sse.format_event(sse.META, {
            "session_id": str(row["id"]) if row else None,
            "thread_id": str(thread_id),
            "model": usage.model if usage else None,
            "tokens_in": usage.tokens_in if usage else 0,
            "tokens_out": usage.tokens_out if usage else 0,
            "cost_usd": usage.cost_usd if usage else 0,
            "sources": [c["source_ref"] for c in chunks],
        })
        yield sse.format_event(sse.DONE, {})
    finally:
        # Reached without persisting == client disconnected mid-stream (the token
        # yield raised GeneratorExit/CancelledError). Save what we have with
        # disconnected=true. Quota is NOT refunded on disconnect (abuse vector:
        # ask, grab tokens, disconnect). Detached so the write survives the
        # generator being torn down.
        if not persisted:
            stage_latency.setdefault(
                "stream_ms", int((time.perf_counter() - stream_t0) * 1000)
            )
            task = asyncio.create_task(
                persist(disconnected=True, gate_outcome="disconnected")
            )
            _pending.add(task)
            task.add_done_callback(_pending.discard)
