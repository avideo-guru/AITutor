---
tags: [type/index, domain/startup, startup/architecture]
updated: 2026-07-16
---
# 🧾 ADRs — architecture decision records

> Tiny records of decisions that look **weird** without their reason. Not
> documentation. Six months from now nobody will remember why
> `observe()` takes a `prior` it could have fetched itself — that's what these
> are for.

## Format (keep it this short)

```
ADR-00N

Decision:    what we do now, one line.
Context:     what made this a question at all.
Reason:      why this and not the obvious alternative.
Consequences: what future work must now live with.
```

Frontmatter carries `status` and the commit/PR that landed it. Nothing else.
If it needs sections, it's not an ADR — it's an architecture note, and those
live in `docs/Architecture/`.

## When to write one

Write an ADR when a reader would reasonably ask **"why is this like this?"**
and the answer isn't in the code:
- The obvious/RFC'd thing was rejected (**001**, **002**).
- A rule exists that looks over-cautious until you know the failure it prevents
  (**003**, **004**, **006**).
- A limitation is deliberate and temporary (**009**).
- Two parts of the codebase are inconsistent on purpose (**010**).

Do **not** write one for: anything the code already says plainly, decisions with
no alternative considered, or things that will change next week.

## Status values

`accepted` · `superseded by ADR-00N` · `reversed (see ADR-00N)`.
Never delete an ADR — a reversed decision is the most useful kind.

## The records

| # | Decision | Status |
|---|---|---|
| [001](ADR-001-verifier-contracts-in-base.md) | Verifier contracts live in `verify/base.py`, not `verify/contracts.py` | accepted |
| [002](ADR-002-observe-takes-prior.md) | `observe(event, prior)` — the estimator is handed its prior state | accepted |
| [003](ADR-003-verdict-aggregation-precedence.md) | Verdict aggregation is `FAIL > TIMEOUT > PASS > INAPPLICABLE` | accepted |
| [004](ADR-004-raising-checker-is-inapplicable.md) | A checker that raises returns INAPPLICABLE, never FAIL | accepted |
| [005](ADR-005-p-correct-is-the-portable-unit.md) | The policy reads `p_correct`, never `rating` | accepted |
| [006](ADR-006-state-is-a-derived-cache.md) | `student_kc_state` is a rebuildable cache, never a source of truth | accepted |
| [007](ADR-007-elo-before-learned-estimators.md) | Elo is the v1 estimator; learned models are gated behind it | accepted |
| [008](ADR-008-jepa-inspired-not-jepa.md) | Phases A/B are "JEPA-inspired"; only Phase C may be called JEPA | accepted |
| [009](ADR-009-units-are-string-compare-until-pint.md) | A.0 unit checking is a string compare; pint lands at P5.0 | accepted (temporary) |
| [010](ADR-010-pydantic-in-adaptive-dataclasses-in-verify.md) | pydantic in the adaptive plane, dataclasses in the verify plane | accepted |
| [011](ADR-011-migrations-are-immutable.md) | Migrations are immutable numbered files; `schema.sql` is not the source of truth | accepted (live reconciliation owed) |
| [012](ADR-012-content-and-derived-state-are-separate-tables.md) | Authored content and derived state never share a table | accepted |

## Connections
- Decisions from → [[Adaptive-Loop-Architecture]] · [[Opus-Execution-Plan]]
- Hub → [[Startup-MOC]] · Board → [[Status]]
