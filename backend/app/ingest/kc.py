"""Knowledge-graph ingest (admin-run):

    python -m app.ingest.kc ../content/kc/phy_mechanics.yaml --check
    python -m app.ingest.kc ../content/kc/phy_mechanics.yaml
    python -m app.ingest.kc ../content/kc/phy_mechanics.yaml --dot kc.dot

Validates a chapter spec and upserts it into `knowledge_components` / `kc_edges`.
Graph logic lives in `kc_graph.py` (pure, testable without a DB); this file is
only the DB and the terminal.

Two properties this tool owes its callers:

**It never partially ingests.** Validation runs to completion before a single
row is written, and the write is one transaction. A graph that fails validation
leaves the database exactly as it was — because a half-written knowledge graph
is worse than no knowledge graph: it looks like it worked.

**It is idempotent.** Re-running the same spec tomorrow produces identical
tables: ids are authored (not generated), `created_at` is preserved on
conflict, and edges are synced rather than appended. The printed graph hash is
the cheap way to see that nothing changed.
"""

import argparse
import asyncio
import sys
from pathlib import Path

import asyncpg

from app.config import settings
from app.ingest.kc_graph import (
    GraphError,
    graph_hash,
    load,
    metrics,
    to_dot,
    topo_order,
    validate,
)


async def upsert(chapter, dsn: str) -> dict:
    """Write the graph in ONE transaction, prereqs before dependents.

    Insert order follows topo_order() — not required by the schema (kc_edges FKs
    point at knowledge_components, not at an ordering), but it means a partial
    failure mid-statement can never leave an edge pointing at a KC that doesn't
    exist yet, and it makes the emitted SQL reviewable in the order a human
    reasons about it.
    """
    order = topo_order(chapter)
    by_id = chapter.by_id
    conn = await asyncpg.connect(dsn)
    try:
        async with conn.transaction():
            for kc_id in order:
                k = by_id[kc_id]
                await conn.execute(
                    """
                    insert into knowledge_components (id, subject, chapter, name, depth)
                    values ($1, $2, $3, $4, 3)
                    on conflict (id) do update
                      set subject = excluded.subject,
                          chapter = excluded.chapter,
                          name    = excluded.name,
                          depth   = excluded.depth
                    """,
                    # created_at is deliberately NOT in the update list: an
                    # upsert must not rewrite when a KC first appeared.
                    k.id, chapter.subject, chapter.chapter, k.name,
                )

            # Sync edges rather than append, so a prereq REMOVED from the YAML
            # actually disappears — otherwise re-running a corrected spec leaves
            # the bad edge behind and the file stops describing the database.
            # Scoped to edges whose postreq is in THIS chapter: a cross-chapter
            # prereq (optics needing phy.mech.vectors) is owned by the chapter
            # that declares it, and must not be collateral damage here.
            ids = list(by_id)
            deleted = await conn.fetchval(
                "with gone as (delete from kc_edges where postreq = any($1::text[]) "
                "returning 1) select count(*) from gone",
                ids,
            )
            for prereq, postreq in chapter.edges:
                await conn.execute(
                    "insert into kc_edges (prereq, postreq) values ($1, $2)",
                    prereq, postreq,
                )

            # Reported, never deleted: a KC in the DB but no longer in the YAML
            # may already have items and attempts hanging off it. Dropping it is
            # a content decision with data consequences, not something an ingest
            # should decide at 2am.
            stale = await conn.fetch(
                "select id, name from knowledge_components "
                "where chapter = $1 and not (id = any($2::text[])) order by id",
                chapter.chapter, ids,
            )
        return {"edges_replaced": deleted, "stale": [dict(r) for r in stale]}
    finally:
        await conn.close()


def _utf8_stdio() -> None:
    """Windows consoles default to cp1252, which cannot encode the cycle
    report's '↓' — so without this the tool CRASHES with UnicodeEncodeError
    exactly when it has found the problem it exists to find. (Observed, not
    theoretical: this repo is developed on Windows.) `errors="replace"` is the
    belt: a mangled arrow beats a traceback swallowing the diagnosis.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):    # not a reconfigurable stream
            pass


def main(argv=None) -> int:
    _utf8_stdio()
    p = argparse.ArgumentParser(prog="python -m app.ingest.kc")
    p.add_argument("spec", type=Path, help="chapter YAML, e.g. content/kc/phy_mechanics.yaml")
    p.add_argument("--check", action="store_true",
                   help="validate and report; touch no database")
    p.add_argument("--dot", type=Path, metavar="FILE",
                   help="write a Graphviz .dot (dot -Tpng FILE -o kc.png)")
    args = p.parse_args(argv)

    try:
        chapter = load(args.spec)
        validate(chapter)
    except GraphError as e:
        print(str(e), file=sys.stderr)
        return 1
    except FileNotFoundError:
        print(f"Ingest failed.\n\nNo such spec: {args.spec}", file=sys.stderr)
        return 1

    m = metrics(chapter)
    print(f"{chapter.chapter}  ({chapter.subject})")
    print(m.render())
    print(f"  Graph hash:            {graph_hash(chapter)}")

    if args.dot:
        args.dot.write_text(to_dot(chapter), encoding="utf-8")
        print(f"\nWrote {args.dot} - render with: dot -Tpng {args.dot} -o kc.png")

    if args.check:
        print("\nOK: valid (--check: nothing written)")
        return 0

    result = asyncio.run(upsert(chapter, settings.database_url))
    print(f"\nOK: ingested {m.nodes} KCs, {m.edges} edges "
          f"({result['edges_replaced']} edge rows replaced)")
    if result["stale"]:
        print("\nWARNING: in the database but no longer in this spec - NOT deleted "
              "(they may have items/attempts):")
        for row in result["stale"]:
            print(f"    {row['id']}  {row['name']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
