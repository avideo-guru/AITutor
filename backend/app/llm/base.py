from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator


@dataclass
class TutorAnswer:
    """Metadata resolved before/after streaming; verified=None means 'could not verify'."""

    verified: bool | None


class LLMProvider(ABC):
    """One interface for every model backend: mock now, Anthropic when a key
    exists, a local/own fine-tuned model later. The chat route only knows
    this contract."""

    @abstractmethod
    def stream_answer(self, subject: str, question: str) -> AsyncIterator[str]:
        """Yield the tutor's answer as text chunks."""

    @abstractmethod
    async def verification(self, subject: str, question: str, answer: str) -> TutorAnswer:
        """Return the verification verdict for the completed answer.

        P1: providers give a best-effort/simulated verdict. P2 replaces this
        with the real SymPy verifier operating on structured steps.
        """
