"""DeepSeek adapter (primary text Reasoner). Cache-friendly stable prefix; the
`stream_options.include_usage` gives us token/cost accounting."""

import json
from typing import AsyncIterator

import httpx

from app.config import settings
from app.models.base import Usage, cost

MODEL = "deepseek-chat"


async def stream(messages: list[dict]) -> AsyncIterator[str | Usage]:
    tokens_in = tokens_out = cached = 0
    async with httpx.AsyncClient(timeout=httpx.Timeout(120, connect=10)) as client:
        async with client.stream(
            "POST",
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {settings.deepseek_api_key}"},
            json={
                "model": MODEL,
                "messages": messages,
                "stream": True,
                "stream_options": {"include_usage": True},
                "temperature": 0.3,
            },
        ) as r:
            r.raise_for_status()
            async for line in r.aiter_lines():
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                chunk = json.loads(data)
                if chunk.get("usage"):
                    u = chunk["usage"]
                    tokens_in = u.get("prompt_tokens", 0)
                    tokens_out = u.get("completion_tokens", 0)
                    cached = u.get("prompt_cache_hit_tokens", 0)
                if chunk.get("choices"):
                    delta = chunk["choices"][0].get("delta", {}).get("content")
                    if delta:
                        yield delta
    yield Usage(MODEL, tokens_in, tokens_out, cost(MODEL, tokens_in, tokens_out, cached))
