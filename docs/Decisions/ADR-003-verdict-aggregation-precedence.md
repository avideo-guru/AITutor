---
tags: [type/adr, domain/startup, startup/architecture, startup/verifier]
status: accepted
date: 2026-07-16
landed: PR #8 (A.0)
---
# ADR-003 — Verdict aggregation is `FAIL > TIMEOUT > PASS > INAPPLICABLE`

**Decision:**
When many checkers run on one claim, the gate outcome is the worst-known one by
this precedence: **FAIL > TIMEOUT > PASS > INAPPLICABLE**. No checkers applied
⇒ INAPPLICABLE.

**Context:**
The verification engine ([[Adaptive-Loop-Architecture]] §3.3b) dispatches a
claim to every checker that applies. The gate needs exactly one outcome, and the
interesting cases are mixed ones.

**Reason:**
- *any FAIL ⇒ FAIL* — one proof of wrongness outranks any number of passes.
- *TIMEOUT above PASS* — this is the rung that looks wrong and isn't. "3 checks
  passed, 1 timed out" means something checkable went unchecked, so we do not
  know. Ranking TIMEOUT below PASS would let a hung SymPy silently become a
  verified claim — i.e. the false-verified rate that kill-criterion 4 measures.
- *INAPPLICABLE is never PASS* (edge #4, [[Opus-Execution-Plan]] §2) — an
  unchecked claim and a verified claim must never be indistinguishable
  downstream.

**Consequences:**
- Adding a checker can only ever make the gate **more** conservative. That is
  the property that makes landing P5's checkers a registration rather than a
  redesign.
- The badge abstains more often than a naive fold would. Accepted: the badge
  says "computation verified" and must mean it.
- Pinned by a truth-table test — a rule that lives only in a docstring regresses.
- The winning verdict is returned intact (reason + checker), so the gate can say
  *which* check failed. An aggregate that loses the reason is useless for
  remediation.
