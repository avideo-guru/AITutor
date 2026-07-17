---
tags: [type/adr, domain/startup, startup/architecture]
status: accepted
date: 2026-07-16
landed: PR #8 (A.0)
---
# ADR-005 — The policy reads `p_correct`, never `rating`

**Decision:**
`KCMastery` carries both `rating` (estimator-native) and `p_correct` (calibrated
probability). `Policy` implementations consume **`p_correct` only**.

**Context:**
The estimator is going to be replaced: Elo (B.1) → SAKT/AKT → Student-JEPA
(Phase C). The policy is not.

**Reason:**
Elo ratings (~0–3000), IRT thetas (~−3..3), and a JEPA head's outputs are not
comparable to each other. A calibrated probability is the only unit that means
the same thing across all of them. If the policy read `rating`, swapping the
estimator would silently change item-selection semantics — the desirable-
difficulty target (p≈0.7) would quietly become a different target.

**Consequences:**
- `p_correct` and `confidence` are validated `0..1` at the seam; an estimator
  emitting `p_correct=1.7` fails loudly instead of skewing the policy.
- `rating` is deliberately **unbounded** and is kept only for the estimator's own
  next update and for debugging. Do not "clean this up" by making it a
  probability — see [[ADR-002]]: `observe()` needs it back verbatim.
- Phase C's swap is a re-run, not a policy rewrite ([[ADR-006]]).
- Calibration becomes a measured quantity: `StateDelta.p_correct_expected`
  records the prediction *before* the outcome on every attempt, so ECE is
  computable after the fact without re-running the old model.
