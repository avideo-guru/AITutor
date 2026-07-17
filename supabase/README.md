# Database migrations

**Migrations are immutable.** Once a file here is merged, it is never edited —
not to fix a typo, not to add a column. You add a new file. The rules and the
reasoning are [[ADR-011]] (`docs/Decisions/ADR-011-migrations-are-immutable.md`);
this file is the how-to.

## The rules

1. **Never edit a merged migration.** A migration that has run somewhere is
   history. Fix forward with a new file.
2. **Never hand-edit the live schema.** If it isn't in a file here, it doesn't
   exist. A hotfix applied in the SQL editor is a landmine for whoever deploys
   next.
3. **`backend/schema.sql` is NOT the source of truth** and is no longer applied.
   It survives only as a pointer to this directory.
4. **New migrations do not rely on `if not exists`.** The baseline does, for the
   reason in its header. Yours shouldn't: a guard that silently no-ops turns
   "this ran but did nothing" into "this ran fine", which is how schema drift
   goes unnoticed. Let it fail loudly instead. (Exception: `create index
   concurrently if not exists` for a re-runnable long index build.)
5. **Additive-first**, like every phase so far. A destructive change (drop,
   rename, type change) needs a written note in the migration header saying what
   breaks and what the rollback is — the file is the record.

## Naming

`<UTC timestamp>_<snake_case_description>.sql` — e.g.
`20260716120000_baseline_p0_p1.sql`. This is the Supabase CLI's native
convention and the ledger's key.

**Why timestamps, not `0008_`-style sequence numbers:** this repo has two
accounts working two branches in parallel (see `CLAUDE.md`). With sequence
numbers, both branches pick `0008`, and — this is the part that bites — git
merges `0008_add_kc_tables.sql` and `0008_add_route_table.sql` **without a
conflict**, because they're different filenames. You get two `0008`s, an
undefined apply order, and no signal that anything went wrong. Timestamps don't
collide, and the ordering survives a merge.

Generate one with the CLI so the timestamp is right:

```sh
supabase migration new add_kc_tables      # creates supabase/migrations/<ts>_add_kc_tables.sql
```

## Applying

```sh
supabase link --project-ref <ref>   # one-time, needs a human-authenticated CLI
supabase db push                    # applies anything the ledger hasn't seen
supabase migration list             # local vs remote, side by side
```

Local round-trip before pushing anything (free, no cloud project touched):

```sh
supabase start                      # local Postgres in Docker
supabase db reset                   # replays EVERY migration from scratch
```

`db reset` is the real test: it proves the migration chain builds an empty
database into the current schema. A migration that only works against *your*
database isn't a migration.

## ⚠️ Reconciling the live project (one-time, infra account)

**Do not run `supabase db push` against the live project until this is settled.**

The live project (`xdszkwjkaamyycirfslz`) already has the P0 schema, applied
2026-07-12 via the Supabase MCP — which recorded its own entries in that
project's `supabase_migrations.schema_migrations` ledger. Those version strings
are not in this repo, so **the ledger and this directory currently disagree**.
The baseline here is idempotent, so a `db push` would probably be harmless — but
"probably harmless" is not a thing to find out on the only database that exists.

Steps, in this order:

1. `supabase link --project-ref xdszkwjkaamyycirfslz`
2. `supabase migration list` — read what the remote ledger actually contains.
   **Nobody in this repo currently knows.** Everything below depends on it.
3. If the remote lists versions this directory doesn't have (expected):
   `supabase migration repair --status reverted <version>` for each stale entry,
   then `supabase migration repair --status applied 20260716120000` to mark the
   baseline as already-present. `repair` edits the ledger only — it does not
   touch tables.
4. `supabase migration list` again — local and remote should now agree on the
   baseline and nothing else.
5. Only then is `supabase db push` safe for the next migration (A.1's).

Post the output of step 2 to `docs/Status.md` before doing step 3. This is the
one operation in the lane that can't be undone by editing a file.

## Connections
- Rules → [[ADR-011]] · Schema design → [[Adaptive-Loop-Architecture]] §3.2
- Board → [[Status]]
