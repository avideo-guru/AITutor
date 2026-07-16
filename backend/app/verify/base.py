"""Verification plane contracts — the engine's building blocks (no domain logic
here; the symbolic/dimensional checkers land in P5). Placed in P1 so the
pipeline could reserve the seam; widened in A.0 so the registry has something
to dispatch on ([[Adaptive-Loop-Architecture]] §3.3a/§3.3b).

Design decision locked here (cheap now, a Protocol migration later): `Verdict`
carries an optional `confidence`. Today's checkers are deterministic (symbolic /
numeric / dimensional) and return None. But an ML- or RLVR-based checker
([[Durable-Moat]]) returns a probability, not a discrete yes/no — so the gate
must be able to threshold a confidence. Baking the field in now means adding
that checker doesn't force every `Verifier` to change signature.

A.0 widening, all additive (the P1 shape and field names are unchanged, so the
P1 contract test still passes byte-for-byte):
  - `Outcome.TIMEOUT` — a checker that ran out of time knows nothing; it is not
    a FAIL (that would show a student a false "wrong") and not an INAPPLICABLE
    (the claim *was* checkable, we just failed to check it). It needs to be
    distinguishable so the gate can abstain rather than badge.
  - `Verdict.checker` — provenance ("gold@v1", "sympy@1.13"). Without it a
    stored verdict can't be attributed to the code that produced it, which makes
    the P5 false-verified audit impossible after any checker upgrade.
  - `Claim` — the unit of work a checker checks. It is deliberately NOT the
    tutor's session/step type: `verify/` must stay import-clean of tutor code so
    the verifier-API pivot stays available ([[Opus-Execution-Plan]] §Parallel).
  - `Verifier` gains `name`/`domain`/`applies_to` — the registry needs to know
    what a checker is and whether it wants a claim before calling it.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable


class Outcome(str, Enum):
    PASS = "pass"                  # step/answer checks out
    FAIL = "fail"                  # provably wrong (carries a reason)
    INAPPLICABLE = "inapplicable"  # not checkable (e.g. unparseable LaTeX) — never FAIL
    TIMEOUT = "timeout"            # checkable, but the checker ran out of time — never PASS


@dataclass(frozen=True)
class Verdict:
    outcome: Outcome
    reason: str | None = None
    # None for deterministic checkers; [0,1] for probabilistic ones (ML/RLVR).
    # The gate thresholds this; checkers never decide show/abstain themselves.
    confidence: float | None = None
    # Which checker produced this, versioned: "gold@v1". Set by the registry if
    # the checker didn't set it, so a stored verdict is always attributable.
    checker: str | None = None


@dataclass(frozen=True)
class Claim:
    """One assertion to be checked. `kind` and `domain` are what `applies_to`
    matches on; `gold` is the curated answer when the item bank has one
    (`items.answer_gold` — A.2/A.3). `ctx` stays free-form until P5 pins the
    structured-solution types: it carries item_id / kc_id / step index, never a
    session or a user."""

    kind: str                    # "final_answer" | "step_transition" | "dimensional"
    domain: str                  # "curated" | "math" | "physics" | …
    response: str                # what the student or the LLM asserted
    gold: dict[str, Any] | None = None
    ctx: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class Verifier(Protocol):
    """One implementation per check type (curated final-answer, step-transition,
    dimensional, …). Pure: never calls a model or the DB — the repair loop is the
    orchestrator's job, not the checker's. Must not raise: return
    INAPPLICABLE instead (the registry defends against this anyway, but a
    checker that raises is a bug, not a verdict)."""

    name: str                    # versioned: "gold@v1"
    domain: str                  # what this checker knows about

    def applies_to(self, claim: Claim) -> bool: ...

    def check(self, claim: Claim) -> Verdict: ...
