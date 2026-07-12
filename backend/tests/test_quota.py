from datetime import date

from app.core.quota import remaining_month, remaining_today

TODAY = date(2026, 7, 11)
YESTERDAY = date(2026, 7, 10)


def test_pro_is_unlimited():
    assert remaining_today("pro", 999, TODAY, TODAY, 10) is None


def test_free_counts_down():
    assert remaining_today("free", 3, TODAY, TODAY, 10) == 7


def test_free_exhausted_clamps_at_zero():
    assert remaining_today("free", 15, TODAY, TODAY, 10) == 0


def test_lazy_reset_restores_full_quota():
    assert remaining_today("free", 10, YESTERDAY, TODAY, 10) == 10


# --- Pro monthly fair-use cap (P0.1) ---

def test_free_has_no_monthly_cap():
    assert remaining_month("free", 9999, TODAY, TODAY, 1500) is None


def test_pro_counts_down_within_month():
    assert remaining_month("pro", 100, date(2026, 7, 1), TODAY, 1500) == 1400


def test_pro_exhausted_clamps_at_zero():
    assert remaining_month("pro", 2000, date(2026, 7, 1), TODAY, 1500) == 0


def test_pro_lazy_reset_same_year():
    # last claim was in June, today is in July -> stale, full quota restored
    assert remaining_month("pro", 1500, date(2026, 6, 15), TODAY, 1500) == 1500


def test_pro_lazy_reset_across_year_boundary():
    # last claim was in December, today is in January -> stale
    jan = date(2027, 1, 5)
    assert remaining_month("pro", 1500, date(2026, 12, 20), jan, 1500) == 1500


def test_pro_no_reset_within_same_month():
    assert remaining_month("pro", 200, date(2026, 7, 1), date(2026, 7, 31), 1500) == 1300
