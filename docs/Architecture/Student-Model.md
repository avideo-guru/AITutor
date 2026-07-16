---
tags: [type/note, domain/startup, startup/architecture]
updated: 2026-06-28
---
# 🧑‍🎓 The Student Model (active student state)

> Conversational memory alone isn't enough. A human tutor keeps a **mental model** of *this* student — what they know, where they're shaky, how they learn. We make that explicit and continuous. This is the engine behind [[Human-vs-AI-Tutor-Gap|gaps 1, 2, 4]].

## Not chat history — a living state
```
Student Graph → Knowledge State → Confidence → Misconceptions → Learning velocity
```
The AI should always be able to answer: *"What does this student understand? What do they misunderstand? What's the hidden confusion behind this question?"* (intent — Gap 1).

## The math (this is psychometrics, our home turf)
- **Mastery estimation:** Bayesian Knowledge Tracing (BKT) / Item Response Theory (IRT) — real per-skill mastery, not heuristics.
- **Spaced repetition:** FSRS / half-life regression scheduler.
- **Diagnosis:** localize the **first wrong step** in a student's attempt and classify the error (conceptual / computational / careless) → targeted remediation. Powered by the [[Verification-Engine]].

## The flywheel (this is the [[Durable-Moat|data moat]])
Every attempt / error / correction → labeled dataset → better mastery model + the step-error corpus that → fine-tunes the [[Durable-Moat|RLVR small model]]. **Design the product so usage *generates* the moat.**

## Powers the "smart default" for [[Fast-vs-Guided-Toggle]]
Mastery sets the default mode per topic: guided-on for weak topics, fast-on for mastered ones — but the student can always flip it (default ≠ force; the Khanmigo lesson in [[Competitive-Landscape]]).

## Operate over the *environment*, not one prompt
A student has PDFs, notebooks, lecture videos, mocks, mistakes, calendar. The model should see the **corpus**, like NotebookLM but over the student's *evolving work*, not just uploads. This is the link to [[Lecture-Companion-Overlay]].

## Open / contested
- ~~`#decision/open` BKT vs IRT vs a simple Elo-style rating for v1 mastery?~~ **RESOLVED 2026-07-16 → Elo** ([[ADR-007]]). Design in [[Adaptive-Loop-Architecture]] §3.3; ships in B.1 behind a `StateEstimator` Protocol. Learned estimators are gated on ≥100k attempts and must beat Elo out-of-sample or they don't ship.
- `#decision/open` What's the minimum "active state" we ship in Phase 2 vs. the full graph?

## Connections
- Realized by → [[Adaptive-Loop-Architecture]] (the loop, the schema, phases A–D)
- Fed by → [[Verification-Engine]] (step-errors)
- Drives → [[Fast-vs-Guided-Toggle]], [[Durable-Moat]] (flywheel)
- Answers → [[Human-vs-AI-Tutor-Gap]] gaps 1/2/4 · Hub → [[Startup-MOC]]
