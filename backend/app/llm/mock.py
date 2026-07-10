import asyncio
import random
from typing import AsyncIterator

from .base import LLMProvider, TutorAnswer

# Canned answer bank ported from the frontend's simulated AiTutorService,
# so the demo behaves identically with zero API cost.
RESPONSES: dict[str, list[dict]] = {
    "math": [
        {
            "keywords": ["calculus", "derivative", "integral", "math"],
            "reply": "Calculus is the mathematical study of continuous change. Derivatives measure the rate of change (like speed), while integrals compute accumulation (like distance or area under a curve). For example, the derivative of f(x) = x^2 is f'(x) = 2x.",
        },
        {
            "keywords": ["algebra", "equation", "solve"],
            "reply": "To solve any algebraic equation, the main goal is to isolate the variable (usually 'x'). Perform the same operation on both sides of the equal sign to keep it balanced. E.g., if 2x + 5 = 15, subtract 5 from both sides (2x = 10) then divide by 2 (x = 5).",
        },
    ],
    "science": [
        {
            "keywords": ["gravity", "black hole", "physics", "science"],
            "reply": "Gravity is a fundamental force of attraction between masses. Einstein's General Relativity describes gravity not as a force, but as the bending of spacetime caused by mass and energy. A black hole is where gravity is so strong that even light cannot escape.",
        },
        {
            "keywords": ["quantum", "atom", "particle"],
            "reply": "Quantum physics is the study of matter and energy at the nanoscopic scale. At this level, particles exhibit wave-particle duality (acting as both waves and particles) and can exist in multiple states at once (superposition) until measured.",
        },
    ],
    "history": [
        {
            "keywords": ["space", "moon", "apollo", "history"],
            "reply": "The Space Race was a 20th-century competition between the Soviet Union and the United States for dominance in spaceflight capability. It culminated on July 20, 1969, when Apollo 11 landed astronauts Neil Armstrong and Buzz Aldrin on the Moon.",
        },
        {
            "keywords": ["civilization", "egypt", "rome"],
            "reply": "Ancient Egypt thrived along the Nile River, famous for its pyramids and hieroglyphs. Meanwhile, Rome grew from a small republic into a colossal empire spanning the Mediterranean, leaving legacies in law, architecture, and governance.",
        },
    ],
    "coding": [
        {
            "keywords": ["angular", "signals", "framework", "coding", "programming"],
            "reply": "Angular 18 introduces Signals for fine-grained reactivity, deferrable views (@defer) for rendering performance, and the new built-in control flow (@if/@for). It enables robust, scalable single-page apps.",
        },
        {
            "keywords": ["javascript", "promise", "async"],
            "reply": "Promises in JavaScript represent the eventual completion (or failure) of an asynchronous operation. Using async/await syntax makes asynchronous code look and behave like synchronous code, making it much easier to read and maintain.",
        },
    ],
}

ABSTENTIONS = [
    "Honest answer: I can't verify a solution to this one yet, and I'd rather tell you that than guess. Try one of the quick prompts to see a machine-checked explanation.",
    "I don't have a verified solution for this question in my bank. Rather than risk teaching you a wrong step, I'm flagging it as unverified — ask a math or science question to see verification in action.",
    "This falls outside what I can machine-check right now. A confident wrong answer is worse than an honest 'I'm not sure' — that's the whole point of AITutor.",
]


def _lookup(subject: str, question: str) -> tuple[str, bool]:
    q = question.lower()
    for item in RESPONSES.get(subject.lower(), []):
        if any(kw in q for kw in item["keywords"]):
            return item["reply"], True
    for sub, items in RESPONSES.items():
        for item in items:
            if any(kw in q for kw in item["keywords"]):
                return f"[Related to {sub.upper()}]: {item['reply']}", True
    return random.choice(ABSTENTIONS), False


class MockProvider(LLMProvider):
    async def stream_answer(self, subject: str, question: str) -> AsyncIterator[str]:
        reply, _ = _lookup(subject, question)
        words = reply.split(" ")
        for i, word in enumerate(words):
            yield word + ("" if i == len(words) - 1 else " ")
            await asyncio.sleep(0.05 + random.random() * 0.03)

    async def verification(self, subject: str, question: str, answer: str) -> TutorAnswer:
        _, found = _lookup(subject, question)
        return TutorAnswer(verified=True if found else False)
