---
tags: [type/adr, domain/startup, startup/architecture]
status: accepted
date: 2026-07-16
landed: PR #8 (A.0)
---
# ADR-010 — pydantic in the adaptive plane, dataclasses in the verify plane

**Decision:**
`app/adaptive/` models are pydantic `BaseModel`. `app/verify/` models are frozen
dataclasses. This inconsistency is deliberate.

**Context:**
Two adjacent packages landed in the same PR using two different model
libraries. That reads as an accident, and someone will eventually "harmonize"
it.

**Reason:**
- **adaptive** — these types cross the API boundary in B.2 (`/v1/next`,
  `/v1/attempts`) and their validation is load-bearing: an estimator emitting
  `p_correct=1.7` must fail at the seam rather than silently skew the policy
  ([[ADR-005]]). pydantic is already a FastAPI dependency, so this costs nothing.
- **verify** — `verify/` must stay import-light and dependency-minimal so it
  survives as a standalone product if the 90-day institute test fails
  ([[Opus-Execution-Plan]] §Parallel track). Its types are internal to checkers,
  never serialized to a client, and P1 already chose dataclasses here.

**Consequences:**
- Don't unify these without re-reading this record. Unifying *toward pydantic*
  taxes the verifier-API pivot; unifying *toward dataclasses* loses the
  boundary validation that makes an estimator swap safe.
- Neither choice adds a dependency today. The moment `verify/` needs pydantic
  for its own sake, this ADR should be reversed rather than worked around.
- The import-cleanliness tests in both planes are what actually enforce the
  separation; this ADR only explains why it's worth enforcing.
