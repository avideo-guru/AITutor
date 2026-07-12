"""Daily/monthly-quota logic. The atomic check-and-increment lives in
ask.py's SQL; these pure helpers compute 'remaining' for /v1/me and are
unit-tested."""

from datetime import date


def remaining_today(
    plan: str,
    questions_today: int,
    questions_reset_on: date,
    today: date,
    free_daily_limit: int,
) -> int | None:
    """None means unlimited (pro). Lazy reset: a stale reset date counts as 0 used."""
    if plan == "pro":
        return None
    used = 0 if questions_reset_on < today else questions_today
    return max(free_daily_limit - used, 0)


def remaining_month(
    plan: str,
    questions_month: int,
    questions_month_reset_on: date,
    today: date,
    pro_monthly_limit: int,
) -> int | None:
    """The Pro fair-use cap. None means not applicable (free plan is gated by
    the daily cap only). Lazy reset: a stale reset month counts as 0 used.
    Calendar-month boundary — `today` should already be in IST, matching the
    reset date ask.py's SQL writes."""
    if plan != "pro":
        return None
    stale = (questions_month_reset_on.year, questions_month_reset_on.month) < (
        today.year, today.month,
    )
    used = 0 if stale else questions_month
    return max(pro_monthly_limit - used, 0)
