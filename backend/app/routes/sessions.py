import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.db import get_pool
from app.deps import get_profile
from app.errors import ApiError

router = APIRouter()
PAGE_SIZE = 20


class FeedbackBody(BaseModel):
    rating: Literal["up", "down"]
    reason: str | None = Field(default=None, max_length=1000)


@router.get("/v1/sessions")
async def list_sessions(cursor: str | None = None,
                        profile: dict = Depends(get_profile)):
    before = None
    if cursor:
        try:
            before = datetime.fromisoformat(cursor)
        except ValueError:
            raise ApiError(400, "BAD_CURSOR", "cursor must be an ISO timestamp")

    rows = await get_pool().fetch(
        """
        select id, thread_id, question, image_url, answer, model, cost_usd,
               feedback_rating, created_at
        from sessions
        where user_id = $1 and ($2::timestamptz is null or created_at < $2)
        order by created_at desc
        limit $3
        """,
        profile["id"], before, PAGE_SIZE,
    )
    items = [
        dict(r) | {"id": str(r["id"]),
                   "thread_id": str(r["thread_id"]) if r["thread_id"] else None}
        for r in rows
    ]
    next_cursor = (
        items[-1]["created_at"].isoformat() if len(items) == PAGE_SIZE else None
    )
    return {"items": items, "next_cursor": next_cursor}


@router.post("/v1/sessions/{session_id}/feedback", status_code=204)
async def feedback(session_id: uuid.UUID, body: FeedbackBody,
                   profile: dict = Depends(get_profile)):
    """One-tap 👍/👎 (+ optional reason) on an answer. Idempotent — re-rating
    overwrites. A session that isn't the caller's 404s (never 403, so we don't
    leak that the id exists)."""
    row = await get_pool().fetchrow(
        """
        update sessions
        set feedback_rating = $1, feedback_reason = $2, feedback_at = now()
        where id = $3 and user_id = $4
        returning id
        """,
        body.rating, body.reason, session_id, profile["id"],
    )
    if row is None:
        raise ApiError(404, "NOT_FOUND", "Session not found")
