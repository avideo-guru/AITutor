"""Gemini adapter (vision + failover Reasoner). Handles photographed problems
(inline image) and stands in when DeepSeek fails before its first token.

The model name comes from settings (GEMINI_MODEL env): 2.5-pro on paid tier,
2.5-flash during the zero-spend phase (2.5-pro has no free tier)."""

import base64
import json
from typing import AsyncIterator

import httpx

from app.config import settings
from app.models.base import ImageRejected, Usage, cost

# Kept for callers/tests that reference the paid-tier default by name.
MODEL = "gemini-2.5-pro"


async def _fetch_image(image_url: str) -> tuple[str, bytes]:
    """Fetch the student's photo with SSRF-conscious transport rules: the URL
    prefix was already allowlisted at the route; here we refuse redirects (no
    bouncing to internal hosts), require an image content-type, and cap the
    download at settings.max_image_bytes with a hard mid-stream abort (plan
    edge case #5). Any failure -> ImageRejected, refunded upstream."""
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=False) as client:
            async with client.stream("GET", image_url) as r:
                if r.status_code != 200:
                    raise ImageRejected(f"image fetch returned {r.status_code}")
                ctype = r.headers.get("content-type", "")
                if not ctype.startswith("image/"):
                    raise ImageRejected(f"not an image: {ctype or 'unknown type'}")
                declared = r.headers.get("content-length")
                if declared and int(declared) > settings.max_image_bytes:
                    raise ImageRejected("image exceeds size limit")
                buf = bytearray()
                async for chunk in r.aiter_bytes():
                    buf.extend(chunk)
                    if len(buf) > settings.max_image_bytes:
                        raise ImageRejected("image exceeds size limit")
        return ctype, bytes(buf)
    except ImageRejected:
        raise
    except httpx.HTTPError as e:
        raise ImageRejected(f"image fetch failed: {e!r}") from e


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
        mime_type, data = await _fetch_image(image_url)
        contents[-1]["parts"].append({
            "inline_data": {
                "mime_type": mime_type,
                "data": base64.b64encode(data).decode(),
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
