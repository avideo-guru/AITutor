-- 20260717090000_items_slug — an authored, stable key for items (A.3).
--
-- A.1 gave `items` a uuid PK and `content_hash unique` for "idempotent
-- re-ingestion". Writing the importer showed that isn't enough to make an item's
-- identity stable: content_hash is a hash of the CONTENT, so fixing a typo in a
-- stem changes the hash, which makes the re-ingest look like a brand-new item —
-- and the original (with its attempts hanging off it) is orphaned. Identity
-- would have been destroyed by proofreading.
--
-- So items get an authored slug, exactly like knowledge_components.id and for
-- exactly the same reason ([[ADR-015]]): identity is declared by a human and
-- never derived from mutable content. content_hash keeps its real job — change
-- detection and duplicate-content detection — and stops pretending to be a key.
--
-- The importer sets `id = uuid5(AITUTOR_NS, slug)`, so the uuid is derivable
-- from the YAML alone, without the database. Both columns are stable across
-- edits; the slug is the one a human greps for.
--
-- NOT NULL without a default is safe here and deliberate: nothing has ever
-- inserted into `items` (there was no ingest path before this migration), so the
-- table is empty everywhere. If this fails, someone hand-inserted a row — which
-- is exactly the case that should fail loudly rather than acquire an empty slug.

alter table items add column slug text not null;
alter table items add constraint items_slug_key unique (slug);

-- Content ops greps by prefix constantly ("show me every projectile item").
create index items_slug_prefix_idx on items (slug text_pattern_ops);

comment on column items.slug is
  'Authored stable identity (phy.mech.projectile_ground.q001). Never derived '
  'from content; never reused. id = uuid5(namespace, slug). See ADR-015.';
comment on column items.content_hash is
  'Change/duplicate detection ONLY — not an identity. Editing a stem changes '
  'this and must NOT create a new item; the slug is the key.';
