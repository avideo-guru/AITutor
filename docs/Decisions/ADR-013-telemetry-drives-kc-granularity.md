---
tags: [type/adr, domain/startup, startup/architecture, startup/content]
status: accepted
date: 2026-07-16
landed: A.2 (content/kc/phy_mechanics.yaml)
---
# ADR-013 — KC granularity is set by telemetry, not by a target number

**Decision:**
The knowledge graph's granularity evolves from data. We do not split, merge, or
pad KCs to hit a count. Mechanics ships with **57** because that is what was
coherent — not because ~50 was the target.

**Context:**
Squirrel AI reportedly runs ~30k KCs, and that number is quoted in our own
research notes ([[Adaptive-Loop-Architecture]] §1.3). It is an obvious thing to
anchor on, and the design doc's "~50 KCs/chapter" is an equally obvious thing to
mistake for a spec.

**Reason:**
Their 30k is the *output* of a decade of telemetry on their content and their
students. Copying the number without the telemetry copies the artefact and not
the mechanism — the same error as calling an Elo estimator "JEPA" ([[ADR-008]]).
A KC count is a result, not a goal.

**Consequences:**
- **The split signal is data:** a KC whose attempts-to-mastery sits at ~15 while
  its neighbours sit at ~3 is hiding two skills. That metric is §4.1's, and it
  exists partly to answer this question.
- **The merge signal is also data:** a KC that reaches mastery in 1–2 attempts
  every time is not a distinct skill.
- Neither signal exists until B.2 logs attempts, so **granularity is not a
  decision to reopen before then**. If the loop works with 57, keep 57.
- `test_seed_is_sanely_sized` bounds nodes to 40–70. That is a **smoke alarm for
  a broken import**, not a target — the docstring says so, and moving it because
  curation genuinely changed is expected and fine.
- Applies to the ID path too: `phy.mech.projectile` is topic-level. Deepening to
  `phy.mech.kinematics.projectile.time_of_flight` is the same premature move in
  a different costume.
