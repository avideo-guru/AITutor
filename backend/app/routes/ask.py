import asyncio
import hashlib
import json
import logging
import time
from typing import AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, model_validator

from app.config import settings
from app.core import rag
from app.core.llm import Usage, stream_answer
from app.core.prompts import build_messages
from app.db import get_pool
from app.deps import get_profile
from app.errors import ApiError

log = logging.getLogger(__name__)
router = APIRouter()

# Holds references to detached persistence tasks (the disconnect path) so the
# event loop doesn't garbage-collect them mid-write. See event_stream's finally.
_pending: set[asyncio.Task] = set()


class AskRequest(BaseModel):
    text: str | None = Field(default=None, max_length=4000)
    image_url: str | None = None
    chapter: str | None = None

    @model_validator(mode="after")
    def _something_asked(self):
        if not (self.text or self.image_url):
            raise ValueError("Provide text and/or image_url")
        return self


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


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


@router.post("/v1/ask")
async def ask(body: AskRequest, profile: dict = Depends(get_profile)):
    pool = get_pool()

    # Atomic lazy-reset + cap-check + increment in one statement (no race).
    # Free is gated by the daily counter (UTC calendar day); Pro no longer
    # bypasses entirely — it's gated by a monthly fair-use counter instead
    # (calendar month, IST — students live in IST, not UTC).
    claimed = await pool.fetchrow(
        """
        update profiles set
          questions_today = case when questions_reset_on < current_date
                                 then 1 else questions_today + 1 end,
          questions_reset_on = current_date,
          questions_month = case when plan = 'pro' then
              case when date_trunc('month', questions_month_reset_on)
                        < date_trunc('month', (now() at time zone 'Asia/Kolkata')::date)
                   then 1 else questions_month + 1 end
            else questions_month end,
          questions_month_reset_on = case when plan = 'pro'
            then (now() at time zone 'Asia/Kolkata')::date
            else questions_month_reset_on end
        where id = $1
          and (
            (plan = 'pro' and
              (case when date_trunc('month', questions_month_reset_on)
                         < date_trunc('month', (now() at time zone 'Asia/Kolkata')::date)
                    then 0 else questions_month end) < $3)
            or
            (plan <> 'pro' and
              (case when questions_reset_on < current_date
                    then 0 else questions_today end) < $2)
          )
        returning id
        """,
        profile["id"],
        settings.free_daily_limit,
        settings.pro_monthly_limit,
    )
    if claimed is None:
        if profile["plan"] == "pro":
            raise ApiError(
                402, "PRO_FAIR_USE_LIMIT",
                f"You've hit the Pro fair-use limit ({settings.pro_monthly_limit} "
                "questions/month). Contact support if you need more.",
            )
        raise ApiError(
            402, "QUOTA_EXCEEDED",
            f"Free plan is limited to {settings.free_daily_limit} questions per "
            "day. Upgrade to Pro for unlimited questions.",
        )

    question = body.text or "Solve the problem shown in the attached image."

    # Retrieval happens before the stream opens so retrieval errors are clean 5xx.
    stage_latency: dict[str, int] = {}
    t = time.perf_counter()
    try:
        chunks = await rag.retrieve(pool, question, body.chapter)
        retrievers_used = ["vector"]
    except Exception:
        log.exception("retrieval failed; answering without context")
        chunks = []
        retrievers_used = []
    stage_latency["retrieve_ms"] = int((time.perf_counter() - t) * 1000)

    messages = build_messages(chunks, [], question)
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

    async def event_stream() -> AsyncIterator[str]:
        answer_parts: list[str] = []
        usage: Usage | None = None
        persisted = False
        session_row = None

        async def persist(*, disconnected: bool, gate_outcome: str):
            """Write session + trace atomically. Runs on the happy path, the
            LLM-failure path, and (detached) the client-disconnect path — but
            only once. Must never raise into the request: the answer is already
            streamed, so a persistence failure is logged, not surfaced."""
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
                              (user_id, question, image_url, answer, model,
                               tokens_in, tokens_out, cost_usd)
                            values ($1, $2, $3, $4, $5, $6, $7, $8)
                            returning id, created_at
                            """,
                            profile["id"], question, body.image_url, answer,
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
                        yield _sse("token", {"t": item})
            except Exception:
                # LLM died. Failover already had its chance (only fires before
                # the first token, by design). Record the failure as a trace.
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
                yield _sse("error", {"code": "LLM_UNAVAILABLE",
                                     "message": "The tutor is unavailable. Try again."})
                return

            stage_latency["stream_ms"] = int((time.perf_counter() - stream_t0) * 1000)
            row = await persist(disconnected=False, gate_outcome="show")
            yield _sse("meta", {
                "session_id": str(row["id"]) if row else None,
                "model": usage.model if usage else None,
                "tokens_in": usage.tokens_in if usage else 0,
                "tokens_out": usage.tokens_out if usage else 0,
                "cost_usd": usage.cost_usd if usage else 0,
                "sources": [c["source_ref"] for c in chunks],
            })
            yield _sse("done", {})
        finally:
            # Reached without persisting == client disconnected mid-stream
            # (the token yield raised GeneratorExit/CancelledError). Save what we
            # have with disconnected=true. Quota is NOT refunded on disconnect
            # (abuse vector: ask, grab tokens, disconnect). Detached so the write
            # survives the generator being torn down.
            if not persisted:
                stage_latency.setdefault(
                    "stream_ms", int((time.perf_counter() - stream_t0) * 1000)
                )
                task = asyncio.create_task(
                    persist(disconnected=True, gate_outcome="disconnected")
                )
                _pending.add(task)
                task.add_done_callback(_pending.discard)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
