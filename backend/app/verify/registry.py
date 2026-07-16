"""The verification engine's dispatcher ([[Adaptive-Loop-Architecture]] §3.3b).

"Mechanical verifier" (singular) is the wrong mental model — the backend
diversifies by domain (curated gold now; sympy/pint at P5; chemistry, sandboxed
execution, SMT later). This module is the part that does NOT change when that
happens: it asks every registered checker whether it applies, runs the ones that
do, and folds their verdicts into one gate outcome.

The aggregation precedence is the whole point, so it is stated once here and
tested as a truth table:

    FAIL  >  TIMEOUT  >  PASS  >  INAPPLICABLE

  - any FAIL ⇒ FAIL — one checker proving it wrong outranks any number of
    passes. A wrong answer that passes four checks and fails one is wrong.
  - else any TIMEOUT ⇒ TIMEOUT — something checkable went unchecked, so we do
    not know. Ranking TIMEOUT above PASS is what stops "3 passed, 1 timed out"
    from badging as verified. Abstain, don't badge.
  - else any PASS ⇒ PASS.
  - else INAPPLICABLE — including the no-checker-applied case. Nothing was
    checked, so nothing is claimed. **Never a PASS** (edge #4,
    [[Opus-Execution-Plan]] §2): an unchecked claim and a verified claim must
    never be indistinguishable downstream.

Timeout enforcement itself is P5.0's job (SymPy's LaTeX parser can hang, so its
checkers run in a ProcessPoolExecutor with a hard per-check budget — a hang
in-process would block the whole async event loop). A.0's checkers are pure and
fast; the TIMEOUT rung exists so that landing P5 is a registration, not a
redesign of this file.
"""

import logging

from app.verify.base import Claim, Outcome, Verdict, Verifier

log = logging.getLogger(__name__)

# Precedence, worst-known-outcome first. Index = rank; lower wins.
_PRECEDENCE = (Outcome.FAIL, Outcome.TIMEOUT, Outcome.PASS, Outcome.INAPPLICABLE)


class Registry:
    """Holds the checkers and dispatches claims to them. Construct one per
    process and register at import time (P5 will register its checkers here);
    it holds no state beyond the checker list."""

    def __init__(self, checkers: list[Verifier] | None = None):
        self._checkers: list[Verifier] = list(checkers or [])

    def register(self, checker: Verifier) -> None:
        self._checkers.append(checker)

    @property
    def checkers(self) -> tuple[Verifier, ...]:
        return tuple(self._checkers)

    def applicable(self, claim: Claim) -> list[Verifier]:
        """Checkers that want this claim. A checker whose `applies_to` raises is
        treated as not applicable — a broken checker must not take down a claim
        every other checker could have handled."""
        out = []
        for c in self._checkers:
            try:
                if c.applies_to(claim):
                    out.append(c)
            except Exception:
                log.exception("verify: applies_to raised in %s", getattr(c, "name", c))
        return out

    def check(self, claim: Claim) -> list[Verdict]:
        """Run every applicable checker. Never raises: a checker that blows up
        yields INAPPLICABLE (never FAIL — a bug in our code must never surface
        to a student as "your answer is wrong") and is logged loudly, because
        silent degradation to 'nothing was checkable' is how a dead verifier
        goes unnoticed for a month."""
        verdicts: list[Verdict] = []
        for c in self.applicable(claim):
            name = getattr(c, "name", c.__class__.__name__)
            try:
                v = c.check(claim)
            except Exception:
                log.exception("verify: checker %s raised on %s", name, claim.kind)
                v = Verdict(Outcome.INAPPLICABLE, reason="checker raised", checker=name)
            # Provenance is not optional in a stored verdict; fill it if the
            # checker didn't bother.
            if v.checker is None:
                v = Verdict(v.outcome, v.reason, v.confidence, name)
            verdicts.append(v)
        return verdicts

    def gate(self, claim: Claim) -> Verdict:
        """check() + aggregate() — what a caller (P5's post-stream gate, or
        A.3's practice grading) actually wants."""
        return aggregate(self.check(claim))


def aggregate(verdicts: list[Verdict]) -> Verdict:
    """Fold many verdicts into the one the gate acts on, by the precedence in
    this module's docstring. The winning verdict is returned intact (reason and
    checker preserved) so the gate can tell the student *which* check failed —
    an aggregate that loses the reason is useless for remediation."""
    if not verdicts:
        return Verdict(Outcome.INAPPLICABLE, reason="no checker applied")
    return min(verdicts, key=lambda v: _PRECEDENCE.index(v.outcome))
