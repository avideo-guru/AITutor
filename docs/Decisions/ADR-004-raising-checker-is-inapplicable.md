---
tags: [type/adr, domain/startup, startup/architecture, startup/verifier]
status: accepted
date: 2026-07-16
landed: PR #8 (A.0)
---
# ADR-004 — A checker that raises returns INAPPLICABLE, never FAIL

**Decision:**
`Registry.check()` catches any exception from a checker's `check()` or
`applies_to()`, converts it to `INAPPLICABLE(reason="checker raised")`, and logs
at error level. A broken checker never takes down the other checkers.

**Context:**
Checkers are pure but not trusted. P5's SymPy can hang or throw on malformed
LaTeX; any checker can have a bug.

**Reason:**
A bug in our code must never surface to a student as "your answer is wrong". FAIL
is a claim about the *student*; a crash is a claim about *us*.

**Consequences:**
- A dead checker degrades to "nothing was checkable" — safe, but **silent**,
  which is how a broken verifier goes unnoticed for a month. Hence the loud log;
  the P3 eval report's step-coverage % is the other tripwire.
- Combined with [[ADR-003]], a crashing checker can only make the gate abstain,
  never mis-badge.
- A timeout is *not* an exception: it has its own outcome
  (`Outcome.TIMEOUT`) because a checker that ran out of time tells us the claim
  was checkable and we failed to check it — strictly more information than a
  crash.
