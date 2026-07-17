"""The borrow-a-feature slot. Competitor capabilities we want (graphing,
formula lookup, OCR, sympy_eval) enter HERE as Tools or Retrievers — never as a
pipeline rewrite. Empty in P1; the eval harness (P3) is the gate for whether any
tool actually moves a metric before it ships."""

from typing import Any, Protocol


class Tool(Protocol):
    async def run(self, args: dict) -> Any: ...
