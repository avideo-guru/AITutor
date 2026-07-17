"""A.0: the adaptive-plane contracts ([[Adaptive-Loop-Architecture]] §3.3a).

These tests exist to keep four rules from decaying into docstrings:
  1. p_correct is the portable unit (the policy reads it, never `rating`)
  2. observe() is pure — same input ⇒ same StateDelta, no I/O
  3. decisions carry reason + policy version (or no off-policy eval later)
  4. state is derived — rebuild() exists and the Protocol demands it

A Protocol with no implementor is a guess, so the fakes below are also the proof
that these contracts are implementable at all.
"""

import ast
import asyncio
import pathlib
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.adaptive.contracts import (
    AttemptEvent,
    KCMastery,
    KnowledgeState,
    NextDecision,
    NextRequest,
    Policy,
    StateDelta,
    StateEstimator,
)

USER, ITEM, KC = uuid4(), uuid4(), "phy.mech.kinematics.projectile"
T0 = datetime(2026, 7, 16, 9, 0, tzinfo=UTC)


def _event(correct=True, item_rating=0.0):
    return AttemptEvent(
        user_id=USER, item_id=ITEM, kc_id=KC, correct=correct,
        item_rating=item_rating, time_ms=4200, hints_used=0, occurred_at=T0,
    )


def _mastery(**kw):
    base = dict(rating=1200.0, p_correct=0.62, confidence=0.4, attempts=7)
    return KCMastery(**{**base, **kw})


class FakeEstimator:
    """The minimum thing that satisfies StateEstimator — a stand-in for B.1's
    EloEstimator. Deliberately pure: no pool use in observe()."""

    name = "fake@v1"

    def observe(self, ev: AttemptEvent, prior: KCMastery | None) -> StateDelta:
        rating = prior.rating if prior else 0.0
        expected = 0.5 if prior is None else prior.p_correct
        delta = (1.0 if ev.correct else 0.0) - expected
        return StateDelta(
            user_id=ev.user_id, kc_id=ev.kc_id, item_id=ev.item_id,
            rating_delta=32.0 * delta, item_rating_delta=-32.0 * delta,
            p_correct_expected=expected, correct_delta=int(ev.correct),
            estimator=self.name, occurred_at=ev.occurred_at,
        )

    async def state(self, pool, user_id: UUID, kc_ids: list[str]) -> KnowledgeState:
        return KnowledgeState(
            user_id=user_id, kc={k: _mastery() for k in kc_ids},
            computed_at=T0, estimator=self.name,
        )

    async def rebuild(self, pool, user_id: UUID) -> None:
        return None


class FakePolicy:
    """Reads p_correct only — rule 1 made executable."""

    name = "fake-greedy@v1"

    async def next(self, pool, req: NextRequest) -> NextDecision | None:
        return NextDecision(
            item_id=ITEM, kc_id=KC, reason="frontier",
            p_correct_expected=0.7, alternatives=(uuid4(),), policy=self.name,
        )


# --- the Protocols are implementable ---

def test_fakes_satisfy_the_protocols():
    assert isinstance(FakeEstimator(), StateEstimator)
    assert isinstance(FakePolicy(), Policy)


def test_estimator_protocol_demands_rebuild():
    # Rule 4: state is a derived cache. An estimator that can't rebuild from the
    # log turns the Phase C swap into a migration.
    assert hasattr(StateEstimator, "rebuild")

    class NoRebuild:
        name = "bad@v1"
        def observe(self, ev, prior): ...
        async def state(self, pool, user_id, kc_ids): ...

    assert not isinstance(NoRebuild(), StateEstimator)


# --- rule 2: observe() is pure ---

def test_observe_is_pure_same_input_same_delta():
    est, ev, prior = FakeEstimator(), _event(), _mastery()
    assert est.observe(ev, prior) == est.observe(ev, prior)


def test_observe_does_not_stamp_its_own_clock():
    # The delta must inherit the event's time, not now() — otherwise replaying
    # yesterday's log produces today's state and rebuild() is a lie.
    assert FakeEstimator().observe(_event(), _mastery()).occurred_at == T0


def test_observe_handles_cold_start():
    d = FakeEstimator().observe(_event(), None)     # never seen this KC
    assert d.p_correct_expected == 0.5 and d.rating_delta > 0


def test_observe_direction_correct_vs_wrong():
    est, prior = FakeEstimator(), _mastery(p_correct=0.62)
    assert est.observe(_event(correct=True), prior).rating_delta > 0
    assert est.observe(_event(correct=False), prior).rating_delta < 0


def test_delta_records_the_prediction_made_before_the_outcome():
    # The only way to measure calibration later without re-running the old model.
    d = FakeEstimator().observe(_event(), _mastery(p_correct=0.62))
    assert d.p_correct_expected == 0.62


# --- rule 1: p_correct is the portable unit ---

@pytest.mark.parametrize("bad", [-0.01, 1.01, 2.0])
def test_p_correct_must_be_a_probability(bad):
    # An estimator emitting p_correct=1.7 must fail at the seam, not skew the
    # policy silently.
    with pytest.raises(ValidationError):
        _mastery(p_correct=bad)


@pytest.mark.parametrize("bad", [-0.5, 1.5])
def test_confidence_must_be_bounded(bad):
    with pytest.raises(ValidationError):
        _mastery(confidence=bad)


def test_rating_is_unbounded_because_it_is_estimator_native():
    # Elo ~0-3000, a JEPA head could emit anything. Not comparable across
    # estimators — which is exactly why the policy must not read it.
    assert _mastery(rating=-1e4).rating == -1e4


def test_attempts_cannot_be_negative():
    with pytest.raises(ValidationError):
        _mastery(attempts=-1)


def test_p_correct_expected_is_validated_on_the_decision_too():
    with pytest.raises(ValidationError):
        NextDecision(item_id=ITEM, kc_id=KC, reason="frontier",
                     p_correct_expected=1.4, policy="p@v1")


# --- rule 3: decisions carry reason + policy version ---

def test_decision_requires_reason_and_policy_version():
    with pytest.raises(ValidationError):        # no reason
        NextDecision(item_id=ITEM, kc_id=KC, p_correct_expected=0.7, policy="p@v1")
    with pytest.raises(ValidationError):        # no policy version
        NextDecision(item_id=ITEM, kc_id=KC, reason="frontier", p_correct_expected=0.7)


def test_decision_reason_is_closed_vocabulary():
    for reason in ("frontier", "review", "probe", "remediate"):
        assert NextDecision(item_id=ITEM, kc_id=KC, reason=reason,
                            p_correct_expected=0.7, policy="p@v1").reason == reason
    with pytest.raises(ValidationError):
        NextDecision(item_id=ITEM, kc_id=KC, reason="vibes",
                     p_correct_expected=0.7, policy="p@v1")


def test_policy_returns_a_logged_decision():
    d = asyncio.run(FakePolicy().next(None, NextRequest(user_id=USER, subject="physics")))
    assert d.reason == "frontier" and d.policy == "fake-greedy@v1"
    assert d.alternatives                      # runners-up kept for off-policy eval


# --- state provenance ---

def test_knowledge_state_requires_its_estimator():
    # Mixing two estimators' numbers in one decision is the bug this prevents.
    with pytest.raises(ValidationError):
        KnowledgeState(user_id=USER, kc={}, computed_at=T0)


def test_state_round_trips_through_json():
    st = asyncio.run(FakeEstimator().state(None, USER, [KC]))
    assert KnowledgeState.model_validate_json(st.model_dump_json()) == st


def test_contracts_are_frozen():
    # A state object mutated after the fact is a state whose provenance lies.
    with pytest.raises(ValidationError):
        _mastery().rating = 1.0


# --- the seam guard ---

def test_adaptive_plane_stays_import_clean_of_routes_and_models():
    # The adaptive plane is consumed BY the routes, never the reverse (the P1
    # seam direction). This keeps the loop testable with no DB and no LLM, and
    # it is what lets B.1's estimator be unit-tested against a hand-computed Elo
    # trace instead of a live Postgres.
    root = pathlib.Path(__file__).resolve().parents[1] / "app" / "adaptive"
    banned = ("app.routes", "app.orchestrator", "app.models", "app.core")
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            mod = None
            if isinstance(node, ast.ImportFrom):
                mod = node.module or ""
            elif isinstance(node, ast.Import):
                mod = node.names[0].name
            if mod and any(mod.startswith(b) for b in banned):
                pytest.fail(f"{path.name} imports {mod}")


def test_a0_adds_no_runtime_dependency():
    # Acceptance #4: sympy/pint arrive with P5.0, not now. If this fails, someone
    # added a dep to make a contract compile — which is how a "contracts only"
    # PR turns into a P5 PR.
    reqs = (pathlib.Path(__file__).resolve().parents[1] / "requirements.txt").read_text()
    for forbidden in ("sympy", "pint", "antlr4", "numpy", "torch"):
        assert forbidden not in reqs.lower(), f"{forbidden} is not an A.0 dependency"
