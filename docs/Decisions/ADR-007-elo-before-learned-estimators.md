---
tags: [type/adr, domain/startup, startup/architecture]
status: accepted
date: 2026-07-16
landed: design (PR #6/#7); implemented in B.1
---
# ADR-007 — Elo is the v1 estimator; learned models are gated behind it

**Decision:**
v1 mastery estimation is **Elo** (Pelánek 2016), not BKT, not IRT, not a neural
model. This resolves the open `#decision/open` in [[Student-Model]].

**Context:**
[[Student-Model]] left "BKT vs IRT vs Elo for v1" open. The research lane wants
Student-JEPA ([[Adaptive-Loop-Architecture]] §3.4).

**Reason:**
Elo needs zero training data, has no cold-start model, and is one `UPDATE` per
attempt — it runs at ₹0 on day one. Every learned alternative needs a corpus we
do not have yet, and the only way to get that corpus is to run a loop that
retains students. A model cannot fix a loop nobody comes back to (the Khanmigo
lesson: engagement > cleverness).

**Consequences:**
- B.1 ships `EloEstimator` behind `StateEstimator` ([[ADR-002]]).
- Phase C is gated on **≥100k logged attempts** — attempts only Elo can
  generate. The gate is not bureaucratic; it's the data dependency.
- **Student-JEPA must beat Elo out-of-sample (AUC + calibration) or it does not
  ship** — pre-registered, P3-style. A negative result gets published, not
  buried.
- Elo's uncertainty is proxied by attempt count. That is a known weakness
  (a real posterior would be better) and is precisely what a learned estimator
  should improve on — making it the first thing to measure in Phase C.
