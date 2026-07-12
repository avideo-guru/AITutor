"""Verification plane contracts — the gate's building blocks (empty of logic in
P1; the checkers land in P5). Placed now so the pipeline can reserve the seam.

Design decision locked here (cheap now, a Protocol migration later): `Verdict`
carries an optional `confidence`. Today's checkers are deterministic (symbolic /
numeric / dimensional) and return None. But an ML- or RLVR-based checker
([[Durable-Moat]]) returns a probability, not a discrete yes/no — so the gate
must be able to threshold a confidence. Baking the field in now means adding
that checker doesn't force every `Verifier` to change signature.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol


class Outcome(str, Enum):
    PASS = "pass"                 # step/answer checks out
    FAIL = "fail"                 # provably wrong (carries a reason)
    INAPPLICABLE = "inapplicable"  # not checkable (e.g. unparseable LaTeX) — never FAIL


@dataclass(frozen=True)
class Verdict:
    outcome: Outcome
    reason: str | None = None
    # None for deterministic checkers; [0,1] for probabilistic ones (ML/RLVR).
    # The gate thresholds this; checkers never decide show/abstain themselves.
    confidence: float | None = None


class Verifier(Protocol):
    """One implementation per check type (final-answer equivalence,
    step-transition, dimensional, …). Pure: never calls a model or the DB — the
    repair loop is the orchestrator's job, not the checker's. `step`/`ctx` are
    left as Any until P5 pins the structured-solution types."""

    def check(self, step: Any, ctx: Any) -> Verdict: ...
