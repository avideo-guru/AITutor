import asyncpg

from app.core.embeddings import embed, to_pgvector

SIMILARITY_FLOOR = 0.75
CANDIDATES = 8
KEEP = 4


async def retrieve(
    pool: asyncpg.Pool, question: str, chapter: str | None
) -> list[dict]:
    """Top-k cosine retrieval from `chunks`, optionally scoped to a chapter."""
    qvec = to_pgvector(await embed(question, task="RETRIEVAL_QUERY"))
    rows = await pool.fetch(
        """
        select id, content, source_ref, 1 - (embedding <=> $1::vector) as similarity
        from chunks
        where ($2::text is null or chapter = $2)
        order by embedding <=> $1::vector
        limit $3
        """,
        qvec,
        chapter,
        CANDIDATES,
    )
    kept = [dict(r) for r in rows if r["similarity"] >= SIMILARITY_FLOOR]
    return kept[:KEEP]
