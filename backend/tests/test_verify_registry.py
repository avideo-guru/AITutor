"""A.0: the verification engine's dispatch + aggregation, and the first real
checker ([[Adaptive-Loop-Architecture]] §3.3b).

The aggregation truth table is the reason this file exists. "Never badge an
unchecked claim as verified" is the rule the whole verifier moat rests on
(kill-criterion 4: false-verified <1% or the badge does not ship), and a rule
written only in a docstring is a rule that regresses.
"""

import pytest

from app.verify.base import Claim, Outcome, Verdict, Verifier
from app.verify.checkers.gold import GoldAnswerChecker
from app.verify.registry import Registry, aggregate


def _claim(response="9.8 m/s^2", gold=None, kind="final_answer", domain="curated"):
    return Claim(kind=kind, domain=domain, response=response, gold=gold)


class _Stub:
    """A checker that returns whatever it's told."""

    def __init__(self, outcome, name="stub@v1", applies=True, domain="curated"):
        self.name = name
        self.domain = domain
        self._outcome = outcome
        self._applies = applies

    def applies_to(self, claim):
        return self._applies

    def check(self, claim):
        return Verdict(self._outcome, reason=f"{self.name} says {self._outcome.value}")


# --- the contract shape (P1's decision preserved, A.0's widening additive) ---

def test_p1_verdict_contract_is_unchanged():
    # The P1 shape must survive the A.0 widening byte-for-byte — this mirrors
    # test_model_plane.py's assertion on purpose: two tests, one contract.
    assert Verdict(Outcome.PASS).confidence is None
    assert Verdict(Outcome.FAIL, reason="bad step", confidence=0.87).confidence == 0.87
    assert Outcome.INAPPLICABLE.value == "inapplicable"
    assert Verdict(Outcome.PASS).checker is None      # additive, defaults to None


def test_timeout_is_its_own_outcome():
    # A checker that ran out of time knows nothing: it must be neither FAIL
    # (false "wrong" to a student) nor INAPPLICABLE (the claim WAS checkable).
    assert Outcome.TIMEOUT.value == "timeout"
    assert Outcome.TIMEOUT not in (Outcome.FAIL, Outcome.INAPPLICABLE, Outcome.PASS)


def test_gold_checker_satisfies_the_verifier_protocol():
    assert isinstance(GoldAnswerChecker(), Verifier)


# --- aggregation truth table (FAIL > TIMEOUT > PASS > INAPPLICABLE) ---

@pytest.mark.parametrize("outcomes, expected", [
    # any FAIL wins, however many passes it is buried under
    ([Outcome.PASS, Outcome.PASS, Outcome.FAIL], Outcome.FAIL),
    ([Outcome.FAIL, Outcome.PASS], Outcome.FAIL),
    ([Outcome.FAIL, Outcome.TIMEOUT], Outcome.FAIL),
    ([Outcome.FAIL], Outcome.FAIL),
    # TIMEOUT outranks PASS: "3 passed, 1 timed out" is NOT verified
    ([Outcome.PASS, Outcome.TIMEOUT], Outcome.TIMEOUT),
    ([Outcome.PASS, Outcome.PASS, Outcome.TIMEOUT], Outcome.TIMEOUT),
    ([Outcome.TIMEOUT, Outcome.INAPPLICABLE], Outcome.TIMEOUT),
    # PASS only when everything that ran passed
    ([Outcome.PASS], Outcome.PASS),
    ([Outcome.PASS, Outcome.INAPPLICABLE], Outcome.PASS),
    # nothing checkable ⇒ nothing claimed
    ([Outcome.INAPPLICABLE], Outcome.INAPPLICABLE),
    ([Outcome.INAPPLICABLE, Outcome.INAPPLICABLE], Outcome.INAPPLICABLE),
])
def test_aggregate_truth_table(outcomes, expected):
    assert aggregate([Verdict(o) for o in outcomes]).outcome is expected


def test_all_inapplicable_is_never_a_pass():
    # Edge #4, stated as a test: an unchecked claim and a verified claim must
    # never be indistinguishable downstream.
    assert aggregate([Verdict(Outcome.INAPPLICABLE)] * 3).outcome is not Outcome.PASS


def test_no_checkers_is_inapplicable_not_pass():
    assert aggregate([]).outcome is Outcome.INAPPLICABLE
    assert Registry([]).gate(_claim()).outcome is Outcome.INAPPLICABLE


def test_aggregate_preserves_the_winning_reason_and_checker():
    # An aggregate that loses the reason can't tell a student WHICH check failed.
    v = aggregate([
        Verdict(Outcome.PASS, reason="ok", checker="a@v1"),
        Verdict(Outcome.FAIL, reason="unit mismatch", checker="b@v1"),
    ])
    assert v.reason == "unit mismatch" and v.checker == "b@v1"


# --- dispatch ---

def test_registry_only_runs_applicable_checkers():
    yes, no = _Stub(Outcome.FAIL, "yes@v1"), _Stub(Outcome.PASS, "no@v1", applies=False)
    r = Registry([yes, no])
    assert r.applicable(_claim()) == [yes]
    assert r.gate(_claim()).outcome is Outcome.FAIL


def test_registry_fills_in_checker_provenance():
    # A stored verdict with no provenance can't be audited after an upgrade.
    r = Registry([_Stub(Outcome.PASS, "prov@v2")])
    assert r.check(_claim())[0].checker == "prov@v2"


def test_a_raising_checker_degrades_to_inapplicable_never_fail():
    # A bug in our code must never surface to a student as "you are wrong".
    class Boom:
        name, domain = "boom@v1", "curated"
        def applies_to(self, claim):
            return True
        def check(self, claim):
            raise RuntimeError("sympy hung, or we have a bug")

    verdicts = Registry([Boom()]).check(_claim())
    assert [v.outcome for v in verdicts] == [Outcome.INAPPLICABLE]
    assert verdicts[0].checker == "boom@v1"


def test_a_checker_raising_in_applies_to_does_not_kill_the_others():
    class BadGate:
        name, domain = "badgate@v1", "curated"
        def applies_to(self, claim):
            raise ValueError("nope")
        def check(self, claim):
            return Verdict(Outcome.PASS)

    r = Registry([BadGate(), _Stub(Outcome.PASS, "good@v1")])
    assert [c.name for c in r.applicable(_claim())] == ["good@v1"]
    assert r.gate(_claim()).outcome is Outcome.PASS


def test_registry_register_appends():
    r = Registry()
    assert r.checkers == ()
    c = GoldAnswerChecker()
    r.register(c)
    assert r.checkers == (c,)


# --- the gold checker ---

def test_gold_applies_only_to_final_answers_with_gold():
    c = GoldAnswerChecker()
    assert c.applies_to(_claim(gold={"value": 9.8}))
    assert not c.applies_to(_claim(gold=None))              # no gold to compare
    assert not c.applies_to(_claim(gold={"value": 1}, kind="step_transition"))


@pytest.mark.parametrize("response", ["9.8 m/s^2", "9.8m/s^2", "  9.8   M/S^2 ", "9.8005 m/s^2"])
def test_gold_numeric_passes_within_tolerance_and_normalized_units(response):
    v = GoldAnswerChecker().check(_claim(response, {"value": 9.8, "unit": "m/s^2"}))
    assert v.outcome is Outcome.PASS, v.reason


@pytest.mark.parametrize("response, why", [
    ("9.9 m/s^2", "outside rel_tol 1e-3"),
    ("-9.8 m/s^2", "sign matters"),
    ("98 m/s^2", "order of magnitude"),
])
def test_gold_numeric_fails_outside_tolerance(response, why):
    v = GoldAnswerChecker().check(_claim(response, {"value": 9.8, "unit": "m/s^2"}))
    assert v.outcome is Outcome.FAIL, why


def test_gold_tolerance_boundary_is_relative():
    c = GoldAnswerChecker()
    # rel_tol=1e-3 => 1000 ± ~1
    assert c.check(_claim("1000.5", {"value": 1000})).outcome is Outcome.PASS
    assert c.check(_claim("1002", {"value": 1000})).outcome is Outcome.FAIL


def test_gold_zero_value_does_not_break_relative_compare():
    c = GoldAnswerChecker()
    assert c.check(_claim("0", {"value": 0})).outcome is Outcome.PASS
    assert c.check(_claim("5", {"value": 0})).outcome is Outcome.FAIL


def test_gold_unit_mismatch_fails():
    v = GoldAnswerChecker().check(_claim("9.8 km/s^2", {"value": 9.8, "unit": "m/s^2"}))
    assert v.outcome is Outcome.FAIL and "unit" in (v.reason or "")


def test_gold_missing_unit_fails_when_gold_requires_one():
    v = GoldAnswerChecker().check(_claim("9.8", {"value": 9.8, "unit": "m/s^2"}))
    assert v.outcome is Outcome.FAIL and "unit" in (v.reason or "")


def test_gold_ignores_units_when_gold_has_none():
    v = GoldAnswerChecker().check(_claim("42 apples", {"value": 42}))
    assert v.outcome is Outcome.PASS


def test_dimensionally_equivalent_units_fail_until_pint_lands():
    # KNOWN, ACCEPTED false negative for A.0: N/kg IS m/s^2. String compare can't
    # know that; pint fixes this in place at P5.0 without changing the contract.
    # This test documents the limitation on purpose — when it starts failing,
    # someone has landed real unit handling and should delete it.
    v = GoldAnswerChecker().check(_claim("9.8 N/kg", {"value": 9.8, "unit": "m/s^2"}))
    assert v.outcome is Outcome.FAIL
    assert "unit" in (v.reason or "")


@pytest.mark.parametrize("response", ["", "   ", "I don't know", "$\\frac{1}{2}$"])
def test_gold_unparseable_is_inapplicable_never_fail(response):
    # Edge #4: a false "wrong" shown to a student is as bad as a false "verified".
    v = GoldAnswerChecker().check(_claim(response, {"value": 9.8, "unit": "m/s^2"}))
    assert v.outcome is Outcome.INAPPLICABLE, v.reason


def test_gold_symbolic_only_is_inapplicable_until_sympy():
    v = GoldAnswerChecker().check(_claim("v^2/(2g)", {"expr": "v**2/(2*g)"}))
    assert v.outcome is Outcome.INAPPLICABLE and "sympy" in (v.reason or "")


def test_gold_with_no_answer_at_all_is_inapplicable():
    v = GoldAnswerChecker().check(_claim("9.8", {"source": "NCERT"}))
    assert v.outcome is Outcome.INAPPLICABLE


@pytest.mark.parametrize("response", ["B", "b", " B "])
def test_gold_mcq_exact_match(response):
    v = GoldAnswerChecker().check(_claim(response, {"choices": ["B"]}))
    assert v.outcome is Outcome.PASS


@pytest.mark.parametrize("response", ["B,D", "BD", "D, B", ["B", "D"]])
def test_gold_mcq_multi_correct_is_a_set_compare(response):
    # JEE Advanced multi-correct: order must not matter, format must not matter.
    text = response if isinstance(response, str) else ",".join(response)
    v = GoldAnswerChecker().check(_claim(text, {"choices": ["B", "D"]}))
    assert v.outcome is Outcome.PASS, v.reason


@pytest.mark.parametrize("response", ["A", "B,C", "B,D,A"])
def test_gold_mcq_wrong_selection_fails(response):
    v = GoldAnswerChecker().check(_claim(response, {"choices": ["B", "D"]}))
    assert v.outcome is Outcome.FAIL


def test_gold_checker_is_pure():
    # Same claim twice ⇒ same verdict. No clock, no RNG, no I/O.
    c, claim = GoldAnswerChecker(), _claim("9.8 m/s^2", {"value": 9.8, "unit": "m/s^2"})
    assert c.check(claim) == c.check(claim)


# --- the pivot guard ---

def test_verify_plane_stays_import_clean_of_tutor_code():
    # verify/ must stay reusable as a standalone product if the 90-day institute
    # test fails ([[Opus-Execution-Plan]] §Parallel track). Importing a session
    # or a profile in here is what would quietly kill that option.
    import ast
    import pathlib

    root = pathlib.Path(__file__).resolve().parents[1] / "app" / "verify"
    banned = ("app.routes", "app.orchestrator", "app.models", "app.db", "app.deps")
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            mod = None
            if isinstance(node, ast.ImportFrom):
                mod = node.module or ""
            elif isinstance(node, ast.Import):
                mod = node.names[0].name
            if mod and any(mod.startswith(b) for b in banned):
                pytest.fail(f"{path.name} imports tutor code: {mod}")
