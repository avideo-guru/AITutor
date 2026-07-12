from datetime import date, datetime
from zoneinfo import ZoneInfo

import httpx
from fastapi import APIRouter, Depends

from app.config import settings
from app.core.quota import remaining_month, remaining_today
from app.db import get_pool
from app.deps import get_profile

router = APIRouter()


@router.get("/v1/me")
async def me(profile: dict = Depends(get_profile)):
    return {
        "id": str(profile["id"]),
        "email": profile["email"],
        "exam_target": profile["exam_target"],
        "plan": profile["plan"],
        "plan_expires_at": profile["plan_expires_at"],
        "questions_remaining_today": remaining_today(
            profile["plan"], profile["questions_today"],
            profile["questions_reset_on"], date.today(),
            settings.free_daily_limit,
        ),
        "free_daily_limit": settings.free_daily_limit,
        "questions_remaining_month": remaining_month(
            profile["plan"], profile["questions_month"],
            profile["questions_month_reset_on"],
            datetime.now(ZoneInfo("Asia/Kolkata")).date(),
            settings.pro_monthly_limit,
        ),
        "pro_monthly_limit": settings.pro_monthly_limit,
    }


@router.delete("/v1/me", status_code=204)
async def delete_me(profile: dict = Depends(get_profile)):
    """Full purge (DPDP): app data always; the auth record too when a service
    role key is configured."""
    pool = get_pool()
    await pool.execute("delete from sessions where user_id = $1", profile["id"])
    await pool.execute("delete from profiles where id = $1", profile["id"])
    if settings.supabase_url and settings.supabase_service_role_key:
        async with httpx.AsyncClient(timeout=15) as client:
            await client.delete(
                f"{settings.supabase_url}/auth/v1/admin/users/{profile['id']}",
                headers={
                    "apikey": settings.supabase_service_role_key,
                    "Authorization": f"Bearer {settings.supabase_service_role_key}",
                },
            )
