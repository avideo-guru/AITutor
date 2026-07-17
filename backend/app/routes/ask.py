"""POST /v1/ask — thin route. Parse + validate, claim quota (the one thing that
must happen before a single token streams), then hand off to the orchestrator.
Everything from retrieval onward lives in `orchestrator/pipeline.py`."""

import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, model_validator

from app.config import allowed_image_prefix, settings
from app.db import get_pool
from app.deps import get_profile
from app.errors import ApiError
from app.orchestrator import pipeline

router = APIRouter()


class AskRequest(BaseModel):
    text: str | None = Field(default=None, max_length=4000)
    image_url: str | None = None
    chapter: str | None = None
    thread_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def _something_asked(self):
        if not (self.text or self.image_url):
            raise ValueError("Provide text and/or image_url")
        return self


async def _claim_quota(pool, profile: dict) -> None:
    """Atomic lazy-reset + cap-check + increment in one statement (no race).
    Free is gated by the daily counter (UTC calendar day); Pro is gated by a
    monthly fair-use counter (calendar month, IST — students live in IST, not
    UTC), not an unconditional bypass. Raises 402 when the cap is hit."""
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


@router.post("/v1/ask")
async def ask(body: AskRequest, profile: dict = Depends(get_profile)):
    # SSRF guard: the backend fetches image_url server-side (Gemini vision), so
    # only the app's own upload bucket is fetchable. Checked BEFORE the quota
    # claim — a rejected image must not consume a question. Fail closed when no
    # prefix is configured.
    if body.image_url:
        prefix = allowed_image_prefix()
        if prefix is None or not body.image_url.startswith(prefix):
            raise ApiError(
                400, "INVALID_IMAGE_URL",
                "Images must be uploaded through the app before asking.",
            )

    pool = get_pool()
    await _claim_quota(pool, profile)
    return StreamingResponse(
        pipeline.run(pool, profile, body),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
