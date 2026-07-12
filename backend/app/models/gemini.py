"""Gemini adapter (vision + failover Reasoner). Handles photographed problems
(inline image) and stands in when DeepSeek fails before its first token.

The model name comes from settings (GEMINI_MODEL env): 2.5-pro on paid tier,
2.5-flash during the zero-spend phase (2.5-pro has no free tier)."""

import base64
import json
from typing import AsyncIterator

import httpx

from app.config import settings
from app.models.base import Usage, cost

# Kept for callers/tests that reference the paid-tier default by name.
MODEL = "gemini-2.5-pro"


async def stream(
    messages: list[dict], image_url: str | None
) -> AsyncIterator[str | Usage]:
    model = settings.gemini_model  # read at call time, not import time
    system = next((m["content"] for m in messages if m["role"] == "system"), "")
    contents = []
    for m in messages:
        if m["role"] == "system":
            continue
        contents.append(
            {"role": "user" if m["role"] == "user" else "model",
             "parts": [{"text": m["content"]}]}
        )
    if image_url and contents:
        async with httpx.AsyncClient(timeout=30) as client:
            img = await client.get(image_url)
            img.raise_for_status()
        contents[-1]["parts"].append({
            "inline_data": {
                "mime_type": img.headers.get("content-type", "image/jpeg"),
                "data": base64.b64encode(img.content).decode(),
            }
        })

    tokens_in = tokens_out = 0
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:streamGenerateContent"
    )
    async with httpx.AsyncClient(timeout=httpx.Timeout(120, connect=10)) as client:
        async with client.stream(
            "POST",
            url,
            params={"alt": "sse", "key": settings.gemini_api_key},
            json={
                "system_instruction": {"parts": [{"text": system}]},
                "contents": contents,
                "generationConfig": {"temperature": 0.3},
            },
        ) as r:
            r.raise_for_status()
            async for line in r.aiter_lines():
                if not line.startswith("data:"):
                    continue
                chunk = json.loads(line[5:].strip())
                meta = chunk.get("usageMetadata")
                if meta:
                    tokens_in = meta.get("promptTokenCount", 0)
                    tokens_out = meta.get("candidatesTokenCount", 0)
                for cand in chunk.get("candidates", []):
                    for part in cand.get("content", {}).get("parts", []):
                        if part.get("text"):
                            yield part["text"]
    yield Usage(model, tokens_in, tokens_out, cost(model, tokens_in, tokens_out))
