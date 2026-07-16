---
tags: [type/adr, domain/startup, startup/architecture, startup/research]
status: accepted
date: 2026-07-16
landed: PR #7 (design review)
---
# ADR-008 — Phases A/B are "JEPA-inspired"; only Phase C may be called JEPA

**Decision:**
Say **"JEPA-inspired architecture"** for Phases A/B, and **"Student-JEPA"** only
for the Phase C encoder. This applies to external wording — papers, decks,
investor conversations — not just the repo.

**Context:**
[[Adaptive-Loop-Architecture]] originally framed the whole loop as a JEPA fusion.
Phases A/B are an Elo estimator + a policy + an LLM decoder.

**Reason:**
JEPA means *learned predictive latent representations*. Elo + policy + decoder is
not that — it borrows VL-JEPA's **selective decoding** pattern (cheap latent
path, expensive decoder invoked only when needed), which is an architectural
idea, not the method. Calling A/B "JEPA" is inspirational rather than literal,
and it is the kind of claim that is indefensible in the one room where it
matters.

**Consequences:**
- The name is **earned** in Phase C, and only if the falsifiable test passes: a
  linear probe on the learned latents must beat `EloEstimator` AUC
  out-of-sample. If it doesn't, the representation isn't real — ship Elo
  ([[ADR-007]]) and publish the negative result.
- The genuinely novel claim, if one exists, is the **latent target** (grounding
  the representation in outcome windows / KC-graph structure / verifier-derived
  error classes), not the encoder. The transformer is a weekend; the target is
  the paper.
- Representation collapse is the default failure mode and must be measured
  (embedding variance/rank), not inferred from a falling loss curve — a
  collapsed model has a beautiful loss curve.
