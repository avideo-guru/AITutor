---
tags: [type/adr, domain/startup, startup/architecture]
status: accepted
date: 2026-07-16
landed: A.1 migration (20260716160000)
---
# ADR-012 — Authored content and derived state never share a table

**Decision:**
Learned item difficulty lives in **`item_state`**, not on `items.difficulty` as
[[Adaptive-Loop-Architecture]] §3.2 sketched. `items`, `knowledge_components` and
`kc_edges` are authored content; `item_state` and `student_kc_state` are derived
caches.

**Context:**
§3.2 put `difficulty real not null default 0` directly on `items`, updated online
per attempt. Writing the A.1 migration surfaced the collision.

**Reason:**
Two concrete failures, not aesthetics:
- **A.3's re-ingest would clobber learned difficulty.** `items.content_hash` is
  there for "idempotent re-ingestion". The moment that ingest is an upsert — or
  an item's stem is corrected, changing its hash — a curated-content operation
  silently destroys weeks of learned signal. Content ingest must not be able to
  touch state.
- **`rebuild()` would write to the content table.** [[ADR-006]] says derived
  state is rebuildable and safe to TRUNCATE. That is only a coherent statement
  if the derived state is separable from the content you'd be destroying with
  it.

**Consequences:**
- The policy joins `items` → `item_state`. One join on a PK; irrelevant next to
  the LLM call it avoids.
- `rebuild()` truncates and replays `item_state` + `student_kc_state` and never
  touches authored content. Content ingest (A.2/A.3) never touches state.
- An item with no attempts has **no `item_state` row** — not a row with rating 0.
  The policy must `left join` and treat a missing row as "unrated, needs
  calibration", which is a different thing from "difficulty is exactly average"
  and is arguably useful (it identifies items to probe).
- Same rule applies to any future authored/learned pair (e.g. hint quality).
