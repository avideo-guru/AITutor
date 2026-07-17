"""Item ingest (admin-run):

    python -m app.ingest.items ../content/items/phy_mechanics.yaml \
        --kc ../content/kc/phy_mechanics.yaml --check
    python -m app.ingest.items ../content/items/phy_mechanics.yaml \
        --kc ../content/kc/phy_mechanics.yaml

Lints an item spec against the KC graph and upserts into `items`. Lint logic is
in `item_spec.py` (pure); this file is the DB and the terminal.

Same two properties as the KC ingest ([[ADR-014]]): **never partially ingests**
(lint runs to completion first; the write is one transaction), and **idempotent**
(slug is authored identity, `id = uuid5(ns, slug)`, `created_at` preserved on
conflict).

`--check` needs no database and is what CI runs: content validates against
content ([[ADR-016]]).
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

import asyncpg

from app.config import settings
from app.ingest.item_spec import ItemError, coverage, lint, load
from app.ingest.kc_graph import GraphError
from app.ingest.kc_graph import load as load_kc


def _utf8_stdio() -> None:
    """See kc.py — a cp1252 console crashes on the report we most need to read."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


async def upsert(items, dsn: str) -> dict:
    conn = await asyncpg.connect(dsn)
    try:
        async with conn.transaction():
            # Fail fast and in our own words if the graph isn't seeded: the FK
            # would say 'violates foreign key constraint items_kc_id_fkey', which
            # is true and unhelpful.
            kc_rows = await conn.fetch("select id from knowledge_components")
            known = {r["id"] for r in kc_rows}
            missing = sorted({i.kc for i in items.items} - known)
            if missing:
                raise ItemError(
                    "Ingest failed.\n\nThese KCs are not in the database — seed the "
                    "graph first (python -m app.ingest.kc ...):\n"
                    + "\n".join(f"  - {m}" for m in missing)
                )

            for item in items.items:
                await conn.execute(
                    """
                    insert into items
                      (id, slug, kc_id, stem, answer_gold, hints, source_ref, content_hash)
                    values ($1, $2, $3, $4, $5::jsonb, $6::jsonb, $7, $8)
                    on conflict (id) do update
                      set kc_id        = excluded.kc_id,
                          stem         = excluded.stem,
                          answer_gold  = excluded.answer_gold,
                          hints        = excluded.hints,
                          source_ref   = excluded.source_ref,
                          content_hash = excluded.content_hash
                    """,
                    # slug is NOT in the update list: it is the identity we
                    # conflicted on. created_at likewise — an upsert must not
                    # rewrite when an item first appeared.
                    item.uuid, item.slug, item.kc, item.stem,
                    json.dumps(item.answer), json.dumps(list(item.hints)),
                    item.source, item.content_hash,
                )

            stale = await conn.fetch(
                """
                select i.slug, i.id from items i
                join knowledge_components k on k.id = i.kc_id
                where k.chapter = $1 and not (i.slug = any($2::text[]))
                order by i.slug
                """,
                items.chapter, [i.slug for i in items.items],
            )
        return {"stale": [dict(r) for r in stale]}
    finally:
        await conn.close()


def main(argv=None) -> int:
    _utf8_stdio()
    p = argparse.ArgumentParser(prog="python -m app.ingest.items")
    p.add_argument("spec", type=Path, help="item YAML, e.g. content/items/phy_mechanics.yaml")
    p.add_argument("--kc", type=Path, required=True,
                   help="the chapter's KC spec — items are linted against the graph FILE, "
                        "not the database, so this runs in CI")
    p.add_argument("--check", action="store_true", help="lint and report; touch no database")
    args = p.parse_args(argv)

    try:
        kc_spec = load_kc(args.kc)
        items = load(args.spec)
        lint(items, {k.id for k in kc_spec.kcs}, kc_chapter=kc_spec.chapter)
    except (ItemError, GraphError) as e:
        print(str(e), file=sys.stderr)
        return 1
    except FileNotFoundError as e:
        print(f"Lint failed.\n\nNo such file: {e.filename}", file=sys.stderr)
        return 1

    cov = coverage(items, {k.id for k in kc_spec.kcs})
    print(f"{items.chapter}  ({items.subject})")
    print("Item bank")
    print(f"  Items:                 {cov['items']}")
    print(f"  KCs covered:           {cov['kcs_covered']} / {cov['kcs_total']}")
    print(f"  KCs with no items:     {len(cov['kcs_uncovered'])}")
    print(f"  KCs with <5 items:     {len(cov['thin'])}   "
          f"(a KC below ~5 has no difficulty ladder to adapt over)")

    if args.check:
        print("\nOK: valid (--check: nothing written)")
        return 0

    try:
        result = asyncio.run(upsert(items, settings.database_url))
    except ItemError as e:
        print(str(e), file=sys.stderr)
        return 1
    print(f"\nOK: ingested {cov['items']} items")
    if result["stale"]:
        print("\nWARNING: in the database but no longer in this spec - NOT deleted "
              "(they may already have attempts):")
        for row in result["stale"]:
            print(f"    {row['slug']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
