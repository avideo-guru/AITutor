---
tags: [type/adr, domain/startup, startup/architecture, startup/content]
status: accepted
date: 2026-07-17
landed: A.3 (items.slug migration, item_spec.py)
---
# ADR-015 — Content ids are authored, immutable, and never reused

**Decision:**
Every content entity has an **authored** id: `knowledge_components.id`
(`phy.mech.vectors_basics`) and `items.slug` (`phy.mech.projectile_ground.q001`).
Ids are **never derived from mutable content** and **never reused for a different
meaning**. `items.id = uuid5(namespace, slug)`, so the uuid is reproducible from
the YAML without a database. Splitting or redefining a concept creates **new**
ids; the old one stays.

**Context:**
Two forces arrived together. A.1 gave `items` only a uuid PK and
`content_hash unique` "for idempotent re-ingestion" — so fixing a typo in a stem
changes the hash, and the re-ingest reads as a *brand-new item*, orphaning the
original and its attempts. **Proofreading would destroy identity.** Separately:
what happens in six months when `vectors_basics` is split into `vectors_2d` and
`vectors_3d`, and historical attempts point at a KC that no longer means what it
meant?

**Reason:**
Both are the same bug — *identity derived from meaning*. The fix is the standard
one: identity is **declared**, meaning is **versioned by new identity**.
- Content hash answers "did this change?" — a real and useful question. It is not
  an identity, and conflating the two is what makes an edit look like a birth.
- If `vectors_basics` is never reused for a narrower concept, every historical
  attempt still resolves to a KC that still means exactly what it meant when the
  attempt was recorded. **No ontology version is needed to interpret it,** because
  the identifier never lied.

**Consequences:**
- **A split is: add `vectors_2d` + `vectors_3d`, keep `vectors_basics`.** Old
  attempts stay interpretable; new items point at the new KCs. Nothing is
  rewritten, so nothing is lost.
- **A redefinition is a split.** If a KC's *meaning* changes — same name, broader
  scope — that is a new id and a deprecated old one, not an edit. This is the one
  rule discipline must carry, because nothing mechanical can detect it (the graph
  hash detects that *something* changed, not that meaning drifted — see below).
- **Deprecation, not deletion** — a KC/item removed from a spec is *reported and
  left in place* by both ingests, because it may already carry attempts. A
  `status` column (`active | deprecated | archived`) is the natural home for that
  and should land **when the first split happens**, not before: today nothing is
  deprecated, and a column with one value is a column that rots.
- **On stamping `graph_hash` onto attempts (considered, rejected for now):**
  the graph hash is chapter-scoped, so a typo fix in one KC's *name* invalidates
  the stamp for every unrelated attempt in the chapter — high churn, low signal,
  and 16 bytes × every row forever. Immutable ids make it unnecessary for
  *correctness*; it remains genuinely useful for *provenance* ("which graph
  produced this experiment?"), which is a property of an experiment or a rebuild,
  not of an attempt. Put it on `student_kc_state` (one row per student-KC, next
  to `estimator`) or on a training-run record when Phase C needs it. Revisit then.
