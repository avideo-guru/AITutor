---
tags: [type/adr, domain/startup, startup/architecture]
status: accepted
date: 2026-07-16
landed: PR #8 (A.0 contracts); enforced by A.1 migrations
---
# ADR-006 — `student_kc_state` is a derived cache, never a source of truth

**Decision:**
`attempts` and `traces` are append-only. `student_kc_state` is a cache of what
replaying `attempts` would produce: it may be `TRUNCATE`d and rebuilt at any
time, and nothing may depend on it holding data the log doesn't.

**Context:**
Event sourcing ([[Adaptive-Loop-Architecture]] §3.1). The tempting alternative is
to treat the mastery row as the record and the log as history.

**Reason:**
If state can't be rebuilt from the log, the Phase C estimator swap becomes a
**migration** instead of a **re-run** — you'd have to translate Elo ratings into
JEPA-derived mastery, which is meaningless ([[ADR-005]]). Rebuildability is what
makes the estimator a swappable implementation rather than a schema commitment.

**Consequences:**
- `rebuild(pool, user_id)` is on the `StateEstimator` Protocol — not a utility,
  a contract obligation. An estimator that can't rebuild doesn't satisfy it.
- Phase C serving is a nightly batch that writes `student_kc_state` via
  `rebuild()`; the online system never changes shape.
- No `UPDATE`/`DELETE` on `attempts` outside the 18-month DPDP retention job.
  Corrections are new events, not edits.
- [[ADR-002]]'s purity is a precondition: a replay only reproduces history if
  `observe()` has no clock and no I/O.
- The event log is the asset ([[Durable-Moat]]); the cache is disposable. If
  they ever disagree, the log is right.
