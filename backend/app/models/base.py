"""Model plane — the stable contracts. Vendor adapters implement `Reasoner`;
the `Router` picks one. This is [[Target-Architecture]] §5 made real: the model
is rented, so every vendor-facing thing sits behind an interface we own, and a
model swap is a new adapter file + an eval run, never a pipeline rewrite."""

from dataclasses import dataclass
from typing import AsyncIterator, Protocol


@dataclass
class Usage:
    model: str
    tokens_in: int
    tokens_out: int
    cost_usd: float


class ImageRejected(Exception):
    """The question's image couldn't be used (too large, not an image, fetch
    failed). Raised before any answer token streams, so the pipeline refunds
    the quota claim and tells the student what to fix — not a generic LLM
    error."""


# Indicative mid-2026 list prices, USD per token — for metering, not billing.
PRICES = {
    "deepseek-chat": {"in": 0.28e-6, "in_cached": 0.028e-6, "out": 0.42e-6},
    "gemini-2.5-pro": {"in": 1.25e-6, "in_cached": 1.25e-6, "out": 10.0e-6},
    "gemini-2.5-flash": {"in": 0.30e-6, "in_cached": 0.30e-6, "out": 2.5e-6},
}


def cost(model: str, tokens_in: int, tokens_out: int, cached: int = 0) -> float:
    """Metering only. Unknown model -> 0.0 rather than crashing the stream's
    final Usage yield — a missing price row must never kill an answer."""
    p = PRICES.get(model)
    if p is None:
        return 0.0
    fresh = max(tokens_in - cached, 0)
    return round(fresh * p["in"] + cached * p["in_cached"] + tokens_out * p["out"], 6)


@dataclass
class ModelChoice:
    """What the Router resolves a request to. Today it carries just the model;
    temperature / max_retries / fallback join it when routing becomes
    policy-as-data (P4)."""
    model: str


class Reasoner(Protocol):
    """One implementation per vendor/model. Yields answer tokens (str) then
    exactly one final Usage. Vendor quirks (SSE framing, auth, cost fields) die
    inside the adapter — nothing above this line sees them."""

    def stream(
        self, messages: list[dict], image_url: str | None
    ) -> AsyncIterator[str | Usage]: ...


class Router(Protocol):
    """Picks a Reasoner (and, later, its params) from request features. v1 is
    hardcoded three-way logic + failover; P4 turns the policy into data."""

    def stream_answer(
        self, messages: list[dict], image_url: str | None
    ) -> AsyncIterator[str | Usage]: ...
