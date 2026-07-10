import json
from typing import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..llm import get_provider

router = APIRouter()


class ChatRequest(BaseModel):
    subject: str = Field(min_length=1, max_length=40)
    message: str = Field(min_length=1, max_length=4000)
    session_id: str | None = None


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/api/chat")
async def chat(req: ChatRequest) -> StreamingResponse:
    """Stream the tutor's answer as SSE: token* -> verification -> done."""

    provider = get_provider()

    async def event_stream() -> AsyncIterator[str]:
        chunks: list[str] = []
        try:
            async for chunk in provider.stream_answer(req.subject, req.message):
                chunks.append(chunk)
                yield _sse("token", {"text": chunk})
            verdict = await provider.verification(req.subject, req.message, "".join(chunks))
            yield _sse("verification", {"verified": verdict.verified})
            yield _sse("done", {})
        except Exception as exc:  # surface provider failures to the client instead of a dead stream
            yield _sse("error", {"message": str(exc)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
