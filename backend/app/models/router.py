"""The Router — model selection + failover policy. This is the seam the
directive calls out: failover lives HERE, not inside any adapter, so adding a
third model (or a local one) is a routing change, not an edit to every vendor
file. v1 is hardcoded; P4 turns it into policy-as-data.

Routing:
  - image present         -> Gemini (vision)
  - plain text            -> DeepSeek (primary, cache-friendly prefix)
  - DeepSeek fails early   -> Gemini (failover)

Failover subtlety (load-bearing — moved intact from the old core/llm.py):
failover fires ONLY before DeepSeek's first token. Once any answer token has
been shown, a mid-stream death cannot be restarted — we surface the error
instead (handled upstream in the pipeline, which also owns the refund).
"""

from typing import AsyncIterator

import httpx

from app.models import deepseek, gemini
from app.models.base import Usage


async def stream_answer(
    messages: list[dict], image_url: str | None
) -> AsyncIterator[str | Usage]:
    if image_url:
        async for item in gemini.stream(messages, image_url):
            yield item
        return
    try:
        stream = deepseek.stream(messages)
        first = await anext(stream)
    except (httpx.HTTPError, StopAsyncIteration):
        # Failover only if DeepSeek died before producing anything.
        async for item in gemini.stream(messages, None):
            yield item
        return
    yield first
    async for item in stream:
        yield item
