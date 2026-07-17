"""Back-compat shim. The model plane moved to `app/models/` in P1 (pipeline
seams): vendor adapters in `models/deepseek.py` + `models/gemini.py`, selection
and failover in `models/router.py`. This module is kept as a thin re-export for
one release so existing imports (`from app.core.llm import Usage, stream_answer`)
don't break. New code should import from `app.models.*` directly.
"""

from app.models.base import PRICES, Usage  # noqa: F401  (re-exported)
from app.models.router import stream_answer  # noqa: F401  (re-exported)
