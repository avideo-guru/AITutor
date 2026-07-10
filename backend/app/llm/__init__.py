from functools import lru_cache

from ..config import settings
from .base import LLMProvider
from .mock import MockProvider


@lru_cache
def get_provider() -> LLMProvider:
    if settings.llm_provider == "anthropic":
        from .anthropic_provider import AnthropicProvider

        return AnthropicProvider()
    return MockProvider()
