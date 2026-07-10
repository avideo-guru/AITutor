from typing import AsyncIterator

from anthropic import AsyncAnthropic

from ..config import settings
from .base import LLMProvider, TutorAnswer

SYSTEM_PROMPT = (
    "You are AITutor, a step-by-step tutor for Indian competitive-exam students "
    "(JEE/NEET). Explain clearly and concisely for the subject at hand. Show "
    "worked steps for quantitative questions. If you are not confident an "
    "answer is correct, say so plainly instead of guessing."
)


class AnthropicProvider(LLMProvider):
    """Real model behind the same interface. Activated with LLM_PROVIDER=anthropic
    + ANTHROPIC_API_KEY in backend/.env; model defaults to claude-haiku-4-5."""

    def __init__(self) -> None:
        self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def stream_answer(self, subject: str, question: str) -> AsyncIterator[str]:
        async with self._client.messages.stream(
            model=settings.anthropic_model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": f"Subject: {subject}\n\n{question}"}],
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def verification(self, subject: str, question: str, answer: str) -> TutorAnswer:
        # Real answers are honestly unverified until the SymPy verifier lands (P2).
        return TutorAnswer(verified=None)
