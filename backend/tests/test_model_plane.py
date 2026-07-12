"""P1 seams: prove the model-plane split preserves behaviour and that the
failover policy moved into the Router intact (failover ONLY before the first
token). Also locks the two contract decisions from the directive."""

import asyncio

import httpx
import pytest

from app.models import deepseek, gemini, router
from app.models.base import Usage


# --- seam wiring / contracts ---

def test_core_llm_reexports_the_model_plane():
    # Old imports must resolve to the new homes (back-compat shim, one release).
    from app.core import llm
    assert llm.stream_answer is router.stream_answer
    assert llm.Usage is Usage


def test_verdict_carries_optional_confidence():
    from app.verify.base import Outcome, Verdict
    assert Verdict(Outcome.PASS).confidence is None          # deterministic checker
    assert Verdict(Outcome.FAIL, reason="bad step", confidence=0.87).confidence == 0.87
    assert Outcome.INAPPLICABLE.value == "inapplicable"


# --- zero-spend phase: configurable Gemini model ---

def test_gemini_model_is_configurable_and_cost_tolerant():
    from app.config import settings
    from app.models.base import PRICES, cost
    assert settings.gemini_model == "gemini-2.5-pro"       # default unchanged
    assert "gemini-2.5-flash" in PRICES                     # flash meters properly
    assert cost("some-future-model", 1000, 1000) == 0.0     # unknown -> 0, no crash


def test_gemini_adapter_reads_model_from_settings(monkeypatch):
    from app.config import settings
    captured = {}

    class FakeResp:
        def raise_for_status(self): ...
        async def aiter_lines(self):
            return
            yield  # empty stream; adapter still yields final Usage

    class FakeStreamCtx:
        def __init__(self, url):
            captured["url"] = url
        async def __aenter__(self):
            return FakeResp()
        async def __aexit__(self, *a):
            return False

    class FakeClient:
        def __init__(self, *a, **k): ...
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            return False
        def stream(self, method, url, **kw):
            return FakeStreamCtx(url)

    monkeypatch.setattr(gemini.httpx, "AsyncClient", FakeClient)
    monkeypatch.setattr(settings, "gemini_model", "gemini-2.5-flash")

    async def run():
        return [item async for item in gemini.stream(
            [{"role": "user", "content": "q"}], None)]

    out = asyncio.run(run())
    assert "gemini-2.5-flash:streamGenerateContent" in captured["url"]
    assert out[-1].model == "gemini-2.5-flash"              # Usage carries it


# --- routing + failover (the load-bearing subtlety) ---

def _collect(messages, image_url):
    async def run():
        out = []
        async for item in router.stream_answer(messages, image_url):
            out.append(item)
        return out
    return asyncio.run(run())


def _fake_ds(tokens=("d1", "d2"), fail_first=False, fail_after=False):
    async def gen(messages):
        if fail_first:
            raise httpx.HTTPError("deepseek down")
            yield  # unreachable
        for i, t in enumerate(tokens):
            yield t
            if fail_after and i == 0:
                raise RuntimeError("died mid-stream")
        yield Usage(deepseek.MODEL, 1, 1, 0.0)
    return gen


def _fake_gm(marker="g1"):
    calls = []

    async def gen(messages, image_url):
        calls.append(image_url)
        yield marker
        yield Usage(gemini.MODEL, 1, 1, 0.0)
    return gen, calls


def test_text_routes_to_deepseek(monkeypatch):
    monkeypatch.setattr(deepseek, "stream", _fake_ds())
    gm, gm_calls = _fake_gm()
    monkeypatch.setattr(gemini, "stream", gm)
    out = _collect([{"role": "user", "content": "q"}], None)
    assert "d1" in out and "d2" in out
    assert gm_calls == []                       # gemini never touched


def test_image_routes_to_gemini(monkeypatch):
    ds = _fake_ds()
    monkeypatch.setattr(deepseek, "stream", ds)
    gm, gm_calls = _fake_gm()
    monkeypatch.setattr(gemini, "stream", gm)
    out = _collect([{"role": "user", "content": "q"}], "http://img")
    assert "g1" in out
    assert gm_calls == ["http://img"]           # image passed through to gemini


def test_failover_when_deepseek_dies_before_first_token(monkeypatch):
    monkeypatch.setattr(deepseek, "stream", _fake_ds(fail_first=True))
    gm, gm_calls = _fake_gm()
    monkeypatch.setattr(gemini, "stream", gm)
    out = _collect([{"role": "user", "content": "q"}], None)
    assert "g1" in out                          # failed over to gemini
    assert gm_calls == [None]                   # failover call carries no image


def test_no_failover_after_first_token(monkeypatch):
    # DeepSeek yields one token then dies — must NOT restart on gemini.
    monkeypatch.setattr(deepseek, "stream", _fake_ds(fail_after=True))
    gm, gm_calls = _fake_gm()
    monkeypatch.setattr(gemini, "stream", gm)

    async def run():
        out = []
        with pytest.raises(RuntimeError):
            async for item in router.stream_answer([{"role": "user", "content": "q"}], None):
                out.append(item)
        return out

    out = asyncio.run(run())
    assert out == ["d1"]                         # the one shown token, then the error
    assert gm_calls == []                        # gemini never used mid-stream
