---
tags: [type/adr, domain/startup, startup/architecture]
status: accepted
date: 2026-07-16
landed: PR #8 (A.0)
---
# ADR-001 — Verifier contracts live in `verify/base.py`

**Decision:**
Verifier contracts live in `app/verify/base.py`. There is no
`verify/contracts.py`, and there will not be one.

**Context:**
[[Adaptive-Loop-Architecture]] §7 originally specified creating
`verify/contracts.py`. It was written without noticing that **P1 had already
shipped `verify/base.py`** carrying `Outcome`/`Verdict`/`Verifier` — its
docstring calls the `confidence` decision "locked here", and
`tests/test_model_plane.py` asserts on the shape.

**Reason:**
Avoid duplicate `Verdict` types. Two competing contract types in one package is
the exact failure §3.3a exists to prevent; shipping it *in the PR that
introduces the contracts* would have been self-refuting. A.0 widened `base.py`
additively instead (`+Outcome.TIMEOUT`, `+Verdict.checker`, `+Claim`,
`+name`/`+domain`/`+applies_to`).

**Consequences:**
- All future checkers implement `app.verify.base.Verifier` and register on
  `app.verify.registry.Registry` — including P5's sympy/pint checkers.
- P1's field names are kept (`outcome`/`reason`), **not** the `status`/`detail`
  the RFC sketched. Anywhere the RFC says `status`, read `outcome`.
- P1's contract test passes untouched, which is the proof the widening was
  additive.
- The RFC text is now wrong in one place on purpose; §7 records the correction
  rather than silently rewriting history.
