"""Adaptive-plane contracts ([[Adaptive-Loop-Architecture]] §3.3a).

Why this file exists before any estimator does: implementations churn and
contracts don't. Elo (B.1) gets replaced by Student-JEPA (Phase C); the policy
gets rewritten; the routes get rewritten. `KnowledgeState`, `StateDelta`, and
the `p_correct` convention are what survive — freezing them now costs a day and
saves a migration later.

The decisions here that look arbitrary are recorded in `docs/Decisions/`:
[[ADR-002]] (`observe(ev, prior)`), [[ADR-005]] (`p_correct`, not `rating`),
[[ADR-006]] (state is a rebuildable cache), [[ADR-007]] (Elo first),
[[ADR-010]] (pydantic here, dataclasses in `verify/`). Read the record before
changing any of them — each exists to prevent a specific failure.

Four rules make these contracts load-bearing rather than decorative. Each is
enforced by a test in `tests/test_adaptive_contracts.py`:

1. **`p_correct` is the portable unit.** Elo ratings, JEPA latents and IRT
   thetas are not comparable across estimators — a calibrated probability is.
   `Policy` consumes `p_correct` ONLY, never `rating`. That is what makes
   swapping the estimator unable to silently change item-selection semantics.
2. **`observe()` is pure; the caller persists.** No DB, no clock, no RNG. Same
   inputs ⇒ same `StateDelta`. This is what lets the identical function run
   online (B.2's route) and in bulk replay (`rebuild()`, Phase C backfill).
3. **Decisions carry their reason and policy version.** `NextDecision.reason`
   and `.policy` go into the log on every serve. Without them no off-policy
   evaluation is possible later — you cannot A/B a policy against history that
   doesn't record why it acted.
4. **State is derived, never authoritative.** `student_kc_state` is a cache of
   what replaying `attempts` would produce; `rebuild()` is the proof. If we ever
   can't rebuild from the log, the Phase C estimator swap becomes a migration
   instead of a re-run.

Pydantic (not dataclasses, unlike the verify plane) because these cross the API
boundary in B.2 and the validation is load-bearing: an estimator that emits
p_correct=1.7 is a bug that must fail at the seam, not silently skew the policy.
No new dependency — FastAPI already brings pydantic v2.
"""

from datetime import datetime
from typing import Literal, Protocol, runtime_checkable
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# Why a knowledge component is a str and not a UUID: IDs are human-readable
# paths ('phy.mech.kinematics.projectile') so content tagging is reviewable in a
# diff and a wrong prerequisite edge is visible in code review (A.2).
KCId = str

NextReason = Literal["frontier", "review", "probe", "remediate"]


class KCMastery(BaseModel):
    """What we believe about one student on one knowledge component."""

    model_config = ConfigDict(frozen=True)

    # Estimator-native and NOT comparable across estimators (Elo ~0-3000, a JEPA
    # head could emit anything). Stored for debugging and for the estimator's own
    # next update — never for cross-estimator comparison, never for the policy.
    rating: float
    # The portable unit (rule 1). Calibrated P(correct) on a hypothetical
    # median-difficulty item for this KC.
    p_correct: float = Field(ge=0.0, le=1.0)
    # How much to trust the above. Elo: a function of attempts. JEPA: predictive
    # variance. Bounded so the policy can threshold it identically either way.
    confidence: float = Field(ge=0.0, le=1.0)
    attempts: int = Field(ge=0)
    due_at: datetime | None = None


class KnowledgeState(BaseModel):
    """A student's mastery across some set of KCs, as of one moment, from one
    estimator. `estimator` is provenance and is required: a state whose origin is
    unknown can't be compared in a Phase C A/B, and mixing two estimators'
    numbers in one decision is the bug this field exists to make visible."""

    model_config = ConfigDict(frozen=True)

    user_id: UUID
    kc: dict[KCId, KCMastery] = Field(default_factory=dict)
    computed_at: datetime
    estimator: str                      # versioned: "elo@v1", "sjepa@v3"


class AttemptEvent(BaseModel):
    """One thing a student did — the append-only unit of the event log
    (`attempts`, migration A.3). Everything downstream is derived from a stream
    of these.

    `occurred_at` is carried on the event rather than read from a clock inside
    the estimator: that is what keeps `observe()` pure (rule 2) and what makes a
    replay of yesterday's log produce yesterday's state rather than today's."""

    model_config = ConfigDict(frozen=True)

    user_id: UUID
    item_id: UUID
    kc_id: KCId
    correct: bool
    # Elo needs the item's current difficulty to compute an update. Passed in
    # (not looked up) so the estimator stays pure.
    item_rating: float = 0.0
    time_ms: int | None = None
    hints_used: int = 0
    occurred_at: datetime


class StateDelta(BaseModel):
    """What one `AttemptEvent` changes. Returned by `observe()`, applied by the
    caller — the estimator never writes. Additive deltas (not absolute values)
    so a replay and an online update compose identically."""

    model_config = ConfigDict(frozen=True)

    user_id: UUID
    kc_id: KCId
    item_id: UUID
    rating_delta: float
    # Elo updates the item too (a question everyone gets right is easy). The
    # policy reads item ratings to hit its target success probability.
    item_rating_delta: float = 0.0
    # What the estimator predicted BEFORE seeing the outcome. Stored on every
    # attempt because it is the only way to measure calibration after the fact
    # (Phase C's ECE) without re-running history through the old model.
    p_correct_expected: float = Field(ge=0.0, le=1.0)
    attempts_delta: int = 1
    correct_delta: int = 0
    due_at: datetime | None = None      # FSRS scheduling (B.1)
    estimator: str
    occurred_at: datetime


class NextRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    user_id: UUID
    subject: str
    chapter: str | None = None
    # Items the student just saw; the policy must not serve them again.
    exclude_item_ids: tuple[UUID, ...] = ()


class NextDecision(BaseModel):
    """What the policy chose, and why. `reason` and `policy` are not
    diagnostics — they are rule 3, and they are what makes the log
    replay-evaluable later."""

    model_config = ConfigDict(frozen=True)

    item_id: UUID
    kc_id: KCId
    reason: NextReason
    # The policy's own prediction, for calibration measurement and for the
    # desirable-difficulty target (~0.7) to be auditable after the fact.
    p_correct_expected: float = Field(ge=0.0, le=1.0)
    # Runners-up, for off-policy evaluation: knowing what was NOT served is what
    # lets a future policy be scored against this history.
    alternatives: tuple[UUID, ...] = ()
    policy: str                         # versioned: "greedy@v1"


@runtime_checkable
class StateEstimator(Protocol):
    """Elo (B.1) → Student-JEPA (Phase C). Swapping one for the other must be a
    new implementation of this Protocol and nothing else — the same trick P1
    played with `Retriever`.

    `observe` takes `prior` explicitly rather than looking it up: an Elo update
    needs the current rating, and a pure function cannot fetch it (rule 2). The
    caller — which already holds the row it is about to update — passes it in.
    `prior=None` means the student has never touched this KC (cold start).
    """

    name: str                           # versioned: "elo@v1"

    def observe(self, ev: AttemptEvent, prior: KCMastery | None) -> StateDelta: ...

    async def state(
        self, pool, user_id: UUID, kc_ids: list[KCId]
    ) -> KnowledgeState: ...

    async def rebuild(self, pool, user_id: UUID) -> None: ...


@runtime_checkable
class Policy(Protocol):
    """Next-item selection (B.2). Reads `p_correct`, never `rating` (rule 1)."""

    name: str                           # versioned: "greedy@v1"

    async def next(self, pool, req: NextRequest) -> NextDecision | None: ...
