from __future__ import annotations

import asyncio
import dataclasses

import httpx
import pytest
from pydantic import BaseModel

import agentrecheck as ar
from agentrecheck import storage
from agentrecheck.client import CloudClient, CloudError
from agentrecheck.pricing import cost_for, price_for, register_price
from agentrecheck.tracer import to_jsonable


def test_trace_decorator_records_input_output_and_saves():
    @ar.tool
    def add(a: int, b: int = 2) -> int:
        return a + b

    @ar.trace
    def agent(question: str, *, flag: bool = False) -> str:
        return f"{question}={add(1)}"

    assert agent("sum", flag=True) == "sum=3"

    [saved] = storage.list_traces()
    assert saved.name == "agent"
    assert saved.input == {"args": ["sum"], "kwargs": {"flag": True}}
    assert saved.output == "sum=3"
    assert saved.tool_sequence == ["add"]
    assert saved.tool_steps[0].args == {"a": 1, "b": 2}
    assert saved.tool_steps[0].result == 3
    assert saved.latency_ms >= 0 and saved.ended_at


def test_trace_with_name_and_error_is_recorded():
    @ar.trace(name="boom", metadata={"env": "test"})
    def agent():
        raise ValueError("nope")

    with pytest.raises(ValueError):
        agent()
    [saved] = storage.list_traces()
    assert saved.name == "boom"
    assert saved.error == "ValueError: nope"
    assert saved.metadata == {"env": "test"}


def test_nested_trace_joins_outer_and_does_not_persist():
    @ar.trace
    def inner():
        return ar.current_trace().id

    with ar.start_trace("outer", persist=False) as outer:
        assert inner() == outer.id
    assert storage.list_traces() == []
    assert ar.current_trace() is None


def test_tool_error_and_passthrough_outside_trace():
    @ar.tool(name="flaky")
    def flaky(x):
        if x:
            raise RuntimeError("down")
        return "ok"

    assert flaky(0) == "ok"  # no trace active: plain call
    with ar.start_trace("t", persist=False) as tr:
        with pytest.raises(RuntimeError):
            flaky(1)
    assert tr.tool_steps[0].name == "flaky"
    assert tr.tool_steps[0].error == "RuntimeError: down"


def test_async_trace_and_tool():
    @ar.tool
    async def fetch(url: str) -> dict:
        return {"url": url}

    @ar.trace
    async def agent(url: str):
        return await fetch(url)

    assert asyncio.run(agent("x")) == {"url": "x"}
    [saved] = storage.list_traces()
    assert saved.tool_sequence == ["fetch"] and saved.output == {"url": "x"}


def test_manual_recorders_and_totals():
    assert ar.record_llm_call(model="gpt-4o") is None  # no-op outside a trace
    assert ar.record_tool_call("x") is None
    with ar.start_trace("manual", persist=False) as tr:
        ar.record_llm_call(
            model="gpt-4o",
            input=[{"role": "user", "content": "hi"}],
            output=None,
            tool_calls=[{"name": "search", "arguments": {"q": "hi"}}],
            input_tokens=1000,
            output_tokens=1000,
        )
    assert tr.total_tokens == 2000
    assert tr.total_cost_usd == pytest.approx(0.0125)
    # No executed tool steps: fall back to what the model requested.
    assert tr.tool_sequence == ["search"]
    payload = tr.to_payload()
    assert payload["llm_calls"] == 1 and payload["tool_calls"] == 0


def test_disabled_env_skips_saving(monkeypatch):
    monkeypatch.setenv("AGENTRECHECK_DISABLED", "1")
    with ar.start_trace("x"):
        pass
    assert storage.list_traces() == []


def test_to_jsonable_handles_common_types():
    class M(BaseModel):
        a: int = 1

    @dataclasses.dataclass
    class D:
        b: int = 2

    class Plain:
        def __init__(self):
            self.c = 3
            self._hidden = 4

    assert to_jsonable({"m": M(), "d": D(), "p": Plain(), "t": (1, 2)}) == {
        "m": {"a": 1},
        "d": {"b": 2},
        "p": {"c": 3},
        "t": [1, 2],
    }
    assert isinstance(to_jsonable(object()), str)


def test_pricing_prefix_match_and_override():
    assert price_for("gpt-4o-mini-2024-07-18") == (0.15, 0.60)
    assert price_for("gpt-4o-2024-08-06") == (2.50, 10.00)
    assert cost_for("unknown-model", 1000, 1000) == 0.0
    register_price("my-model", 1.0, 2.0)
    assert cost_for("my-model-v2", 1_000_000, 500_000) == pytest.approx(2.0)


def test_cloud_client_upload_and_errors():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers["authorization"]
        seen["path"] = request.url.path
        if request.url.path == "/api/runs":
            return httpx.Response(401, json={"error": "bad key"})
        return httpx.Response(200, json={"ids": ["tr_1"]})

    client = CloudClient("http://x.test/", "ark_k", transport=httpx.MockTransport(handler))
    assert client.upload_trace(ar.Trace(name="t")) == {"ids": ["tr_1"]}
    assert seen == {"auth": "Bearer ark_k", "path": "/api/traces"}
    with pytest.raises(CloudError, match="401"):
        client.upload_run(ar.RunResult())


def test_cloud_client_from_env_requires_both(monkeypatch):
    assert CloudClient.from_env() is None
    monkeypatch.setenv("AGENTRECHECK_API_KEY", "k")
    assert CloudClient.from_env() is None
    monkeypatch.setenv("AGENTRECHECK_API_URL", "http://localhost:3000")
    assert CloudClient.from_env() is not None


def test_upload_failure_never_breaks_agent(monkeypatch):
    monkeypatch.setenv("AGENTRECHECK_API_KEY", "k")
    monkeypatch.setenv("AGENTRECHECK_API_URL", "http://127.0.0.1:9")

    @ar.trace
    def agent():
        return "fine"

    with pytest.warns(UserWarning, match="upload failed"):
        assert agent() == "fine"
