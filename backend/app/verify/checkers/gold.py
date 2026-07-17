"""Curated final-answer checker — the first real `Verifier`
([[Adaptive-Loop-Architecture]] §3.3b, A.0).

Compares a response against a curated gold answer (`items.answer_gold`, A.2/A.3;
the same shape the P3 golden set uses — curate once, use twice). It is the
backstop the P5 badge copy leans on: symbolic step checks can pass a
consistent-but-wrongly-modeled solution, and only a gold final answer catches
that ([[Viability-Brutal-Honesty]] §1.5).

Deliberately narrow, because A.0 adds no dependencies (the unit limitation and
its expiry date are [[ADR-009]] in `docs/Decisions/`):

  - **numeric** — relative tolerance 1e-3 (the P3 grading tolerance).
  - **units** — normalized *string* compare, NOT dimensional analysis. `m/s^2`
    == `M/S^2 `, but `N/kg` != `m/s^2` even though they are the same dimension.
    That is a known false negative, accepted for A.0 and fixed in place at P5.0
    when `pint` lands (this checker's contract does not change then — only the
    body of `_units_match`). It is the safe direction of wrongness for a
    *grader* (a student is told "check your units", not told a right answer is
    wrong)… but it is exactly why this checker must NOT be used to badge a
    student's own physics work as failed until P5.0. Gate on it for item
    grading; abstain elsewhere.
  - **choices** — set compare, so JEE Advanced multi-correct items work.
  - **symbolic** (gold has `expr` but no `value`) — INAPPLICABLE. Symbolic
    equivalence needs sympy (P5.0). Returning INAPPLICABLE rather than guessing
    is edge #4 of [[Opus-Execution-Plan]] §2: a false "wrong" shown to a student
    is as bad as a false "verified".

Pure and dependency-free: no DB, no model, no I/O, stdlib only.
"""

import math
import re

from app.verify.base import Claim, Outcome, Verdict

NAME = "gold@v1"
DOMAIN = "curated"

REL_TOL = 1e-3          # matches the P3 eval grading tolerance
_ABS_TOL = 1e-12        # so that gold == 0 doesn't make every compare fail

# Leading number of a response: "9.8 m/s^2" -> 9.8, "-1.6e-19 C" -> -1.6e-19.
_NUM = re.compile(r"^\s*([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)\s*(.*)$", re.S)
_WS = re.compile(r"\s+")


def _normalize_unit(unit: str) -> str:
    """Casefold + strip + collapse internal whitespace. This is the whole of
    A.0's unit intelligence; see the module docstring on what it cannot do."""
    return _WS.sub(" ", unit.strip()).casefold()


def _units_match(response_unit: str, gold_unit: str) -> bool:
    return _normalize_unit(response_unit) == _normalize_unit(gold_unit)


def _split_number(text: str) -> tuple[float, str] | None:
    """'9.8 m/s^2' -> (9.8, 'm/s^2'). None when there's no leading number —
    which means unparseable, which means INAPPLICABLE, never FAIL."""
    m = _NUM.match(text)
    if not m:
        return None
    try:
        return float(m.group(1)), m.group(2).strip()
    except ValueError:
        return None


def _numbers_close(got: float, want: float) -> bool:
    return math.isclose(got, want, rel_tol=REL_TOL, abs_tol=_ABS_TOL)


def _as_choice_set(value) -> set[str]:
    """Accepts 'B', 'B,D', 'BD', ['B', 'D'] — students and item authors write
    multi-correct answers every one of those ways."""
    if isinstance(value, (list, tuple, set)):
        parts = [str(v) for v in value]
    else:
        text = str(value).strip()
        parts = re.split(r"[,\s;]+", text) if re.search(r"[,\s;]", text) else list(text)
    return {p.strip().casefold() for p in parts if p.strip()}


class GoldAnswerChecker:
    """Implements `Verifier`. Registered by callers; holds no state."""

    name = NAME
    domain = DOMAIN

    def applies_to(self, claim: Claim) -> bool:
        return claim.kind == "final_answer" and bool(claim.gold)

    def check(self, claim: Claim) -> Verdict:
        gold = claim.gold or {}
        response = (claim.response or "").strip()

        if not response:
            return Verdict(Outcome.INAPPLICABLE, reason="empty response", checker=NAME)

        if "choices" in gold:
            return self._check_choices(response, gold["choices"])
        if gold.get("value") is not None:
            return self._check_numeric(response, gold)
        if gold.get("expr"):
            # Symbolic equivalence needs sympy — P5.0. Never guess.
            return Verdict(
                Outcome.INAPPLICABLE,
                reason="symbolic gold needs the sympy checker (P5.0)",
                checker=NAME,
            )
        return Verdict(Outcome.INAPPLICABLE, reason="gold has no answer", checker=NAME)

    def _check_choices(self, response: str, gold_choices) -> Verdict:
        want = _as_choice_set(gold_choices)
        got = _as_choice_set(response)
        if not got:
            return Verdict(Outcome.INAPPLICABLE, reason="no choice parsed", checker=NAME)
        if got == want:
            return Verdict(Outcome.PASS, checker=NAME)
        return Verdict(
            Outcome.FAIL,
            reason=f"selected {sorted(got)}, expected {sorted(want)}",
            checker=NAME,
        )

    def _check_numeric(self, response: str, gold: dict) -> Verdict:
        parsed = _split_number(response)
        if parsed is None:
            return Verdict(
                Outcome.INAPPLICABLE, reason="no number in response", checker=NAME
            )
        got_value, got_unit = parsed

        try:
            want_value = float(gold["value"])
        except (TypeError, ValueError):
            return Verdict(
                Outcome.INAPPLICABLE, reason="gold value unparseable", checker=NAME
            )

        if not _numbers_close(got_value, want_value):
            return Verdict(
                Outcome.FAIL, reason=f"expected {want_value}, got {got_value}",
                checker=NAME,
            )

        want_unit = gold.get("unit")
        if want_unit:
            if not got_unit:
                return Verdict(
                    Outcome.FAIL, reason=f"missing unit, expected {want_unit!r}",
                    checker=NAME,
                )
            if not _units_match(got_unit, want_unit):
                # May be a false negative pre-P5.0 (N/kg vs m/s^2) — see module
                # docstring. The reason string says "unit" so a human reading a
                # trace can spot the pattern if it shows up in the P3 report.
                return Verdict(
                    Outcome.FAIL,
                    reason=f"unit {got_unit!r} != expected {want_unit!r}",
                    checker=NAME,
                )
        return Verdict(Outcome.PASS, checker=NAME)
