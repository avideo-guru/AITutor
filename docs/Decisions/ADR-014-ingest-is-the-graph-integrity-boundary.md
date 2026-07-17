---
tags: [type/adr, domain/startup, startup/architecture]
status: accepted
date: 2026-07-16
landed: A.2 (app/ingest/kc_graph.py, app/ingest/kc.py)
---
# ADR-014 — The ingest tool is the knowledge graph's integrity boundary

**Decision:**
KC graphs are authored as **YAML**, validated by the ingest tool, and written by
it. Validation failures are **fatal and pre-write**: the tool never partially
ingests. Humans do not write SQL INSERTs for content.

**Context:**
The prerequisite graph must be a DAG. Postgres enforces some of that — `check
(prereq <> postreq)` catches self-loops, FKs catch dangling references — but it
**cannot express acyclicity**. `A→B→A` inserts cleanly and leaves a graph whose
frontier query never unlocks any of those KCs. The database cannot defend itself
here, so something else must.

**Reason:**
- If the DB can't hold the invariant, the writer must — and then there must only
  be **one** writer. A hand-written INSERT bypasses every check in this ADR, so
  the tool has to be the only way in.
- **Partial ingest is worse than no ingest**: a half-written graph looks like it
  worked. Hence validate-everything-then-write, in one transaction.
- **YAML over SQL** because the graph is content and content gets reviewed. A
  wrong prerequisite is visible in a YAML diff and invisible in a wall of
  INSERTs. (Cost: one dependency, PyYAML, used with `safe_load` only.)

**Consequences:**
- `kc_graph.py` is pure (no DB) so every rule is unit-testable; `kc.py` owns the
  transaction. Rules enforced: no self-loops · no duplicate edges · acyclic ·
  every prereq exists · no isolated nodes unless `root: true` · ids well-formed ·
  **`chapter` matches the `chunks.chapter` convention** (retrieval filters on
  exact equality — a mismatch silently retrieves nothing).
- **Determinism is part of the contract:** authored ids, file-order tie-breaking
  in the topological sort, `created_at` preserved on conflict, edges synced not
  appended. Re-running a spec is a no-op, and the printed graph hash proves it.
- Edges are synced **scoped to the chapter's own KCs** — a cross-chapter prereq
  is owned by the chapter that declares it, and must not be collateral damage.
- A KC that disappears from the YAML is **reported, never deleted**: it may
  already carry items and attempts. That is a content decision with data
  consequences, not something an ingest decides at 2am.
- Graph metrics print on every run so a broken import is loud ("Nodes: 57,
  Edges: 2" and 51 components) rather than silent.
- Anything that later writes KCs (an admin UI, an LLM-assisted tagger for A.3)
  goes **through this validator**, or this ADR is void.
