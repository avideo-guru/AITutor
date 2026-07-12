"""Knowledge plane contract. Retrieval is several engines merged
([[Retrieval-Knowledge-Layer]]); each engine implements this one method. v1 ships
VectorRetriever (pgvector, exists in core/rag.py); KeywordRetriever (FTS) and a
merge step arrive in P2 behind this same interface."""

from typing import Protocol


class Retriever(Protocol):
    """Returns chunks most relevant to `question`, optionally scoped to a
    chapter. A chunk is a dict with at least id, content, source_ref, and a
    similarity/score the merge step can rank on."""

    async def retrieve(
        self, pool, question: str, chapter: str | None
    ) -> list[dict]: ...
