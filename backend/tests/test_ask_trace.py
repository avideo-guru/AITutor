"""Behavioural tests for the P0.2 trace/persist/refund control flow in
routes/ask.py. No real DB — a FakePool records what the route *would* write, so
we can assert the happy path, the zero-token LLM failure (refund + error trace),
and the client-disconnect path (partial trace, disconnected=true, NO refund)."""

import asyncio
import os
import uuid
from datetime import datetime

import pytest

# deps.py builds a PyJWKClient at import time and rejects an empty URL, so the
# app package can't be imported without this set (pre-existing, not P0.2).
os.environ.setdefault("SUPABASE_URL", "https://example.test")

import app.routes.ask as ask_mod
import app.routes.sessions as sess_mod
from app.core.llm import Usage
from app.errors import ApiError
from app.routes.ask import AskRequest, ask
from app.routes.sessions import FeedbackBody, feedback


class FakeConn:
    def __init__(self, log):
        self.log = log

    def transaction(self):
        conn = self

        class _Tx:
            async def __aenter__(self_):
                return conn

            async def __aexit__(self_, *a):
                return False

        return _Tx()

    async def fetchrow(self, sql, *args):
        if "insert into sessions" in sql:
            self.log.append(("session_insert", args))
            return {"id": uuid.uuid4(), "created_at": datetime.now()}
        return None

    async def execute(self, sql, *args):
        if "insert into traces" in sql:
            self.log.append(("trace_insert", args))


class FakePool:
    def __init__(self):
        self.log = []
        self.history_rows: list[dict] = []
        self.feedback_returns = {"id": uuid.uuid4()}

    async def fetchrow(self, sql, *args):
        if "update profiles set" in sql and "questions_today = case" in sql:
            self.log.append(("quota_claim", args))
            return {"id": args[0]}  # claim succeeds
        if "update sessions" in sql and "feedback_rating" in sql:
            self.log.append(("feedback_update", args))
            return self.feedback_returns
        return None

    async def fetch(self, sql, *args):
        if "from sessions" in sql and "thread_id" in sql:
            self.log.append(("history_load", args))
            return self.history_rows
        return []

    async def execute(self, sql, *args):
        if "greatest(questions_today" in sql:
            self.log.append(("refund", args))

    def acquire(self):
        pool = self

        class _Acq:
            async def __aenter__(self_):
                return FakeConn(pool.log)

            async def __aexit__(self_, *a):
                return False

        return _Acq()


def _profile(plan="free"):
    return {"id": uuid.uuid4(), "plan": plan}


def _setup(monkey_stream, monkey_retrieve=None):
    pool = FakePool()
    ask_mod.get_pool = lambda: pool
    ask_mod.stream_answer = monkey_stream
    if monkey_retrieve is None:
        async def monkey_retrieve(pool_, q, chapter):
            return []
    ask_mod.rag.retrieve = monkey_retrieve
    return pool


async def _drain(resp):
    return [chunk async for chunk in resp.body_iterator]


def test_happy_path_persists_session_and_trace_once():
    async def fake_stream(messages, image_url):
        yield "Hello"
        yield " world"
        yield Usage("deepseek-chat", 100, 20, 0.001)

    pool = _setup(fake_stream)

    async def run():
        resp = await ask(AskRequest(text="q"), profile=_profile())
        return "".join(await _drain(resp))

    body = asyncio.run(run())
    kinds = [k for k, _ in pool.log]
    assert kinds.count("session_insert") == 1
    assert kinds.count("trace_insert") == 1
    assert "refund" not in kinds
    assert "event: meta" in body and "event: done" in body
    # gate_outcome=show, disconnected=false on the trace insert
    trace_args = next(a for k, a in pool.log if k == "trace_insert")
    assert "show" in trace_args and trace_args[-1] is False


def test_zero_token_llm_failure_refunds_and_traces_error():
    async def fake_stream(messages, image_url):
        raise RuntimeError("deepseek down")
        yield  # unreachable; makes this an async generator

    pool = _setup(fake_stream)

    async def run():
        resp = await ask(AskRequest(text="q"), profile=_profile())
        return "".join(await _drain(resp))

    body = asyncio.run(run())
    kinds = [k for k, _ in pool.log]
    assert "refund" in kinds                       # edge #2: student got nothing
    assert kinds.count("trace_insert") == 1        # failure still recorded
    assert "event: error" in body
    trace_args = next(a for k, a in pool.log if k == "trace_insert")
    assert "error" in trace_args


def test_disconnect_persists_partial_trace_without_refund():
    async def fake_stream(messages, image_url):
        yield "partial"
        await asyncio.sleep(0.05)   # client disconnects during this gap
        yield " more"
        yield Usage("deepseek-chat", 10, 2, 0.0001)

    pool = _setup(fake_stream)

    async def run():
        resp = await ask(AskRequest(text="q"), profile=_profile())
        agen = resp.body_iterator
        await agen.__anext__()      # receive first token
        await agen.aclose()         # simulate mid-stream client disconnect
        # let the detached persist task finish
        if ask_mod._pending:
            await asyncio.gather(*list(ask_mod._pending))

    asyncio.run(run())
    kinds = [k for k, _ in pool.log]
    assert kinds.count("session_insert") == 1
    assert kinds.count("trace_insert") == 1
    assert "refund" not in kinds                   # never refund on disconnect
    trace_args = next(a for k, a in pool.log if k == "trace_insert")
    assert "disconnected" in trace_args and trace_args[-1] is True


# --- P0.3: history + feedback ---

def _capture_stream(captured):
    async def fake_stream(messages, image_url):
        captured["messages"] = messages
        yield "ok"
        yield Usage("deepseek-chat", 1, 1, 0.0)
    return fake_stream


def test_history_loaded_when_thread_id_present():
    captured = {}
    pool = _setup(_capture_stream(captured))
    pool.history_rows = [{"question": "prev q", "answer": "prev a $$\\boxed{42}$$"}]
    tid = uuid.uuid4()

    async def run():
        resp = await ask(AskRequest(text="follow up", thread_id=tid), profile=_profile())
        await _drain(resp)

    asyncio.run(run())
    roles = [m["role"] for m in captured["messages"]]
    assert roles == ["system", "user", "assistant", "user"]   # + 1 history pair
    assert captured["messages"][1]["content"] == "prev q"
    assert "history_load" in [k for k, _ in pool.log]


def test_no_history_loaded_without_thread_id():
    captured = {}
    pool = _setup(_capture_stream(captured))
    pool.history_rows = [{"question": "prev q", "answer": "prev a"}]

    async def run():
        resp = await ask(AskRequest(text="q"), profile=_profile())
        await _drain(resp)

    asyncio.run(run())
    roles = [m["role"] for m in captured["messages"]]
    assert roles == ["system", "user"]                        # no history injected
    assert "history_load" not in [k for k, _ in pool.log]


def test_long_history_answer_keeps_boxed_line():
    long_answer = ("x" * 5000) + "\n$$\\boxed{v = 3\\,\\text{m/s}}$$"
    out = ask_mod._truncate_history_answer(long_answer)
    assert len(out) < 1200
    assert "\\boxed{v = 3" in out


def test_feedback_owned_session_ok():
    pool = FakePool()
    pool.feedback_returns = {"id": uuid.uuid4()}
    sess_mod.get_pool = lambda: pool

    async def run():
        await feedback(uuid.uuid4(), FeedbackBody(rating="up"), profile=_profile())

    asyncio.run(run())
    assert "feedback_update" in [k for k, _ in pool.log]


def test_feedback_foreign_session_404():
    pool = FakePool()
    pool.feedback_returns = None                              # not the caller's row
    sess_mod.get_pool = lambda: pool

    async def run():
        await feedback(uuid.uuid4(), FeedbackBody(rating="down", reason="wrong step"),
                       profile=_profile())

    with pytest.raises(ApiError) as ei:
        asyncio.run(run())
    assert ei.value.status == 404
