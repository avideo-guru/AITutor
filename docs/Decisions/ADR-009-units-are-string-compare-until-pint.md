---
tags: [type/adr, domain/startup, startup/architecture, startup/verifier]
status: accepted (temporary — revisit at P5.0)
date: 2026-07-16
landed: PR #8 (A.0)
---
# ADR-009 — A.0 unit checking is a string compare; `pint` lands at P5.0

**Decision:**
`GoldAnswerChecker` compares units by **normalized string equality**
(casefold + strip + collapse whitespace), not dimensional analysis. `m/s^2` ==
`M/S^2 `; `N/kg` != `m/s^2`.

**Context:**
A.0's acceptance required "unit mismatch ⇒ FAIL" while also forbidding new
dependencies. Real dimensional analysis needs `pint`, which is a P5.0 dependency
([[Opus-Execution-Plan]] P5.0).

**Reason:**
The no-new-dependency fence. The alternative — hand-rolling an SI normalizer in
A.0 — is scope creep into P5's job, is the kind of code that stays subtly wrong
for years, and would be deleted wholesale when `pint` arrives.

**Consequences:**
- **Known false negative:** dimensionally equivalent units written differently
  (`N/kg` vs `m/s^2`, `N·m` vs `J`) return FAIL. This is pinned by
  `test_dimensionally_equivalent_units_fail_until_pint_lands`, a test **designed
  to fail and be deleted** when real unit handling lands. When it goes red,
  someone did the right thing.
- **Scope limit, load-bearing:** use this checker to grade **curated items**
  (where the gold's unit string is authored alongside the item, so the strings
  match by construction). Do **not** badge a student's free-form physics work on
  it before P5.0 — a false "wrong" is as bad as a false "verified" (edge #4).
- The fix is local: only `_units_match()` changes. The `Verifier` contract, the
  registry, and every caller stay as they are — which is the point of
  [[ADR-001]].
