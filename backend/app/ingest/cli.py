"""Offline content ingestion (admin-run):

    python -m app.ingest.cli notes/optics.md --subject PHY --chapter PHY::optics::12

Chunks a markdown file (~800 tokens each, paragraph-aligned, one-paragraph
overlap), embeds, and upserts into `chunks`. Idempotent via content_hash."""

import argparse
import asyncio
import hashlib
import sys
from pathlib import Path

import asyncpg

from app.config import settings
from app.core.embeddings import embed, to_pgvector
from app.ids import GRAMMAR, ChapterId, InvalidChapterId

TARGET_CHARS = 3200  # ~800 tokens at ~4 chars/token


def chunk_markdown(text: str, target_chars: int = TARGET_CHARS) -> list[str]:
    """Greedy paragraph packing with one-paragraph overlap between chunks.
    Never splits inside a paragraph (so worked examples stay intact)."""
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current: list[str] = []
    size = 0
    for p in paras:
        if current and size + len(p) > target_chars:
            chunks.append("\n\n".join(current))
            current = [current[-1]]  # overlap
            size = len(current[0])
        current.append(p)
        size += len(p)
    if current:
        chunks.append("\n\n".join(current))
    return chunks


async def ingest(path: Path, subject: str, chapter: str, source: str) -> None:
    text = path.read_text(encoding="utf-8")
    chunks = chunk_markdown(text)
    print(f"{path.name}: {len(chunks)} chunks")

    conn = await asyncpg.connect(settings.database_url)
    try:
        for i, content in enumerate(chunks):
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            vec = to_pgvector(await embed(content, task="RETRIEVAL_DOCUMENT"))
            await conn.execute(
                """
                insert into chunks
                  (subject, chapter, source_ref, content, content_hash, embedding)
                values ($1, $2, $3, $4, $5, $6::vector)
                on conflict (content_hash) do update
                  set subject = $1, chapter = $2, source_ref = $3, embedding = $6::vector
                """,
                subject, chapter, f"{source}#{i}", content, content_hash, vec,
            )
            print(f"  [{i + 1}/{len(chunks)}] upserted")
    finally:
        await conn.close()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("file", type=Path)
    p.add_argument("--subject", required=True, help="e.g. PHY")
    p.add_argument("--chapter", required=True,
                   help=f"{GRAMMAR}, e.g. PHY::optics::12")
    p.add_argument("--source", default=None, help="citation label; defaults to filename")
    args = p.parse_args()
    if not args.file.exists():
        sys.exit(f"No such file: {args.file}")

    # This was free text until A.3. It is the *other* end of the identifier the
    # KC graph writes, and retrieval joins them by exact string equality with no
    # FK to catch a mismatch — so a typo here produced chunks that no KC could
    # ever retrieve, silently. Both write boundaries now parse the same grammar.
    try:
        chapter = ChapterId.parse(args.chapter)
    except InvalidChapterId as e:
        sys.exit(str(e))
    if chapter.subject != args.subject:
        sys.exit(
            f"--subject {args.subject!r} does not match the chapter's subject "
            f"{chapter.subject!r} in {args.chapter!r}. chunks.subject and "
            "chunks.chapter must agree, or filtering by one contradicts the other."
        )

    asyncio.run(
        ingest(args.file, args.subject, str(chapter),
               args.source or args.file.stem)
    )


if __name__ == "__main__":
    main()
