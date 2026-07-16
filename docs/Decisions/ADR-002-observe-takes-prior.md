---
tags: [type/adr, domain/startup, startup/architecture]
status: accepted
date: 2026-07-16
landed: PR #8 (A.0)
---
# ADR-002 — `observe(event, prior)`

**Decision:**
`StateEstimator.observe(ev: AttemptEvent, prior: KCMastery | None) -> StateDelta`.
The caller passes the prior mastery in. `prior=None` means cold start.

**Context:**
[[Adaptive-Loop-Architecture]] §3.3a sketched `observe(ev)` *and* required the
method be pure. Those are contradictory: an Elo update needs the student's
current rating, and a pure function cannot fetch it.

**Reason:**
Replay purity. The route that calls `observe()` already holds the
`student_kc_state` row it is about to update, so passing it costs nothing —
whereas letting the estimator fetch it would put I/O inside the one function
that must be replayable.

**Consequences:**
- Estimator implementations never perform I/O in `observe()` — no DB, no clock,
  no RNG. `occurred_at` rides on the event so replaying yesterday's log produces
  yesterday's state, not today's.
- The identical function runs online (B.2's route) and in bulk replay
  (`rebuild()`, Phase C's backfill). This is what makes [[ADR-006]] true.
- `observe()` returns a `StateDelta`; the caller persists. The estimator never
  writes.
- Testable against a hand-computed Elo trace with no Postgres (B.1).
