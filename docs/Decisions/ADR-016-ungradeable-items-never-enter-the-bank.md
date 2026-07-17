---
tags: [type/adr, domain/startup, startup/content, startup/verifier]
status: accepted
date: 2026-07-17
landed: A.3 (item_spec.check_gradeable)
---
# ADR-016 — An item the verifier cannot grade never enters the bank

**Decision:**
Every item's `answer` is validated at lint time by constructing the canonical
correct response and handing it to the **real** `GoldAnswerChecker`. Anything but
`PASS` is a fatal lint error. Content is linted against **files**, not the
database, so it runs in CI.

**Context:**
Items carry `answer_gold`; `GoldAnswerChecker` (A.0) grades attempts against it.
Nothing connected the two until an item was served to a student — at which point
a malformed gold produces `INAPPLICABLE`, which B.2 stores as `correct = null`
("not gradeable", [[ADR-003]]).

**Reason:**
A `null` is not an error. Nothing alerts. The item sits in the bank being served,
teaching nobody, contributing no evidence to Elo, forever — and the failure looks
like a quiet gap in the data rather than a broken item. **If the checker cannot
grade the correct answer, it will never grade a student's.** That is knowable at
authoring time, in a file, in front of a human — so it must be caught there.

**Consequences:**
- The linter imports the checker rather than re-deriving what "gradeable" means.
  When P5.0 adds `pint` and sympy, previously-rejected items become admissible
  **with no linter change** — the gate tracks the engine automatically.
- **Symbolic-only gold (`expr:` with no `value:`) is rejected today** — it returns
  INAPPLICABLE until the sympy checker lands ([[ADR-009]]). Curation must give a
  numeric `value` for now. This is the linter honestly reporting the engine's
  current reach, not a permanent rule.
- The rule is one-directional: the checker must never import content code
  (`verify/` stays import-clean so the verifier-API pivot survives).
- Corollary the linter also enforces: **no `difficulty` in item YAML** ([[ADR-012]]
  — Elo learns it), **no duplicate stems within a KC** (the loop would serve the
  same question twice and count the second attempt as independent evidence), and
  **`source` is required** (attribution for NCERT/JEE material is a licensing
  obligation, not garnish).
- Coverage is **reported, not enforced**: items-per-KC is what says whether B.2
  can adapt (a KC with one item can be served but not adapted over), but a thin
  bank is a curation status, not a broken file.
