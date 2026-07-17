"""Behavioural tests for the P0.2 trace/persist/refund control flow in
routes/ask.py. No real DB — a FakePool records what the route *would* write, so
we can assert the happy path, the zero-token LLM failure (refund + error trace),
and the client-disconnect path (partial trace, disconnected=true, NO refund)."""

import asyncio
import uuid
from datetime import datetime

import pytest

import app.orchestrator.pipeline as pipeline
import app.routes.ask as ask_mod
import app.routes.sessions as sess_mod
from app.core.llm import Usage
from app.errors import ApiError
from app.routes.ask import AskRequest, ask
from app.routes.sessions import FeedbackBody, feedback, get_session


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
        self.session_row = None

    async def fetchrow(self, sql, *args):
        if "update profiles set" in sql and "questions_today = case" in sql:
            self.log.append(("quota_claim", args))
            return {"id": args[0]}  # claim succeeds
        if "update sessions" in sql and "feedback_rating" in sql:
            self.log.append(("feedback_update", args))
            return self.feedback_returns
        if "select" in sql and "from sessions" in sql and "where id = $1" in sql:
            self.log.append(("session_get", args))
            return self.session_row
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
    # ask.py claims quota with this pool, then hands it to pipeline.run; the
    # pipeline owns retrieval + the LLM stream, so those are patched there.
    ask_mod.get_pool = lambda: pool
    pipeline.stream_answer = monkey_stream
    if monkey_retrieve is None:
        async def monkey_retrieve(pool_, q, chapter):
            return []
    pipeline.vector.retrieve = monkey_retrieve
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


def test_sse_frames_are_byte_exact():
    # The byte-identical guard for the P1 refactor: the wire format the client
    # sees (token/meta/done framing) must be exactly what shipped pre-P1.
    async def fake_stream(messages, image_url):
        yield "AB"
        yield Usage("deepseek-chat", 5, 2, 0.0001)

    _setup(fake_stream)

    async def run():
        resp = await ask(AskRequest(text="q"), profile=_profile())
        return "".join(await _drain(resp))

    body = asyncio.run(run())
    assert body.startswith('event: token\ndata: {"t": "AB"}\n\n')
    assert body.endswith("event: done\ndata: {}\n\n")
    assert body.count("event: token") == 1
    assert '"thread_id":' in body and '"session_id":' in body   # meta payload


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
        if pipeline._pending:
            await asyncio.gather(*list(pipeline._pending))

    asyncio.run(run())
    kinds = [k for k, _ in pool.log]
    assert kinds.count("session_insert") == 1
    assert kinds.count("trace_insert") == 1
    assert "refund" not in kinds                   # never refund on disconnect
    trace_args = next(a for k, a in pool.log if k == "trace_insert")
    assert "disconnected" in trace_args and trace_args[-1] is True


# --- SSRF guard (review finding, fixed on P1) ---

ALLOWED_BASE = "https://proj.supabase.co"
ALLOWED_IMG = ALLOWED_BASE + "/storage/v1/object/public/question-images/x.jpg"


def test_bad_image_url_rejected_before_quota():
    # No SUPABASE_URL configured in tests -> fail closed; and the reject must
    # happen BEFORE the quota claim (a bad image never burns a question).
    pool = _setup(_capture_stream({}))

    async def run():
        await ask(AskRequest(image_url="https://evil.example/pwn.png"),
                  profile=_profile())

    with pytest.raises(ApiError) as ei:
        asyncio.run(run())
    assert ei.value.status == 400 and ei.value.code == "INVALID_IMAGE_URL"
    assert "quota_claim" not in [k for k, _ in pool.log]


def test_allowed_image_url_passes(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "supabase_url", ALLOWED_BASE)
    captured = {}
    pool = _setup(_capture_stream(captured))

    async def run():
        resp = await ask(AskRequest(image_url=ALLOWED_IMG), profile=_profile())
        return "".join(await _drain(resp))

    body = asyncio.run(run())
    assert "quota_claim" in [k for k, _ in pool.log]
    assert "event: done" in body


def test_image_rejected_refunds_and_emits_specific_code(monkeypatch):
    from app.config import settings
    from app.models.base import ImageRejected
    monkeypatch.setattr(settings, "supabase_url", ALLOWED_BASE)

    async def fake_stream(messages, image_url):
        raise ImageRejected("too large")
        yield  # unreachable; makes this an async generator

    pool = _setup(fake_stream)

    async def run():
        resp = await ask(AskRequest(image_url=ALLOWED_IMG), profile=_profile())
        return "".join(await _drain(resp))

    body = asyncio.run(run())
    kinds = [k for k, _ in pool.log]
    assert "refund" in kinds                     # zero tokens -> claim reversed
    assert "IMAGE_REJECTED" in body              # specific, actionable error
    assert "LLM_UNAVAILABLE" not in body


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
    out = pipeline._truncate_history_answer(long_answer)
    assert len(out) < 1200
    assert "\\boxed{v = 3" in out


def test_get_session_owned_returns_row_with_string_ids():
    pool = FakePool()
    sid, tid = uuid.uuid4(), uuid.uuid4()
    pool.session_row = {
        "id": sid, "thread_id": tid, "question": "q", "image_url": None,
        "answer": "a", "model": "m", "cost_usd": 0.0,
        "feedback_rating": None, "created_at": datetime.now(),
    }
    sess_mod.get_pool = lambda: pool

    out = asyncio.run(get_session(sid, profile=_profile()))
    assert out["id"] == str(sid)
    assert out["thread_id"] == str(tid)
    assert "session_get" in [k for k, _ in pool.log]


def test_get_session_foreign_or_missing_404():
    pool = FakePool()
    pool.session_row = None                                   # not the caller's row
    sess_mod.get_pool = lambda: pool

    with pytest.raises(ApiError) as ei:
        asyncio.run(get_session(uuid.uuid4(), profile=_profile()))
    assert ei.value.status == 404


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
