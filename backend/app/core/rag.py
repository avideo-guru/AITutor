"""Back-compat shim. Vector retrieval moved to `app/retrieval/vector.py` in P1
(pipeline seams). Kept as a re-export for one release so existing imports don't
break; new code imports from `app.retrieval.*`."""

from app.retrieval.vector import (  # noqa: F401  (re-exported)
    CANDIDATES,
    KEEP,
    SIMILARITY_FLOOR,
    VectorRetriever,
    retrieve,
)
