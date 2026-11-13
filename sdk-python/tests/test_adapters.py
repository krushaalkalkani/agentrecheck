from __future__ import annotations

import asyncio
from types import SimpleNamespace as NS

import pytest

import agentrecheck as ar
from tests.conftest import chat_response, fake_openai


def test_openai_chat_records_tool_calls_tokens_and_cost():
    client = ar.wrap_openai(
        fake_openai(
            [
                chat_response(tool_calls=[("lookup", {"id": "A1"})], usage=(1000, 100)),
                chat_response(content="done", usage=(1200, 50)),
            ]
        )
    )
    with ar.start_trace("t", persist=False) as tr:
        client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user"}])
        client.chat.completions.create(model="gpt-4o-mini", messages=[])

    first, second = tr.llm_steps
    assert first.provider == "openai" and first.model == "gpt-4o-mini"
    assert first.tool_calls[0].name == "lookup"
    assert first.tool_calls[0].arguments == {"id": "A1"}
    assert (first.input_tokens, first.output_tokens) == (1000, 100)
    assert first.cost_usd == pytest.approx((1000 * 0.15 + 100 * 0.60) / 1e6)
    assert second.output == "done"
    assert tr.tool_sequence == ["lookup"]


def test_openai_wrap_is_idempotent_and_passthrough_outside_trace():
    client = fake_openai([chat_response(content="a")])
    ar.wrap_openai(client)
    wrapped = client.chat.completions.create
    ar.wrap_openai(client)
    assert client.chat.completions.create is wrapped
    assert client.chat.completions.create(model="m", messages=[]).choices[0].message.content == "a"


def test_openai_error_is_recorded_and_reraised():
    client = ar.wrap(fake_openai([RuntimeError("rate limited")]))
    with ar.start_trace("t", persist=False) as tr:
        with pytest.raises(RuntimeError):
            client.chat.completions.create(model="gpt-4o", messages=[])
    assert tr.llm_steps[0].error == "RuntimeError: rate limited"
    assert tr.llm_steps[0].model == "gpt-4o"


def test_openai_streaming_is_noted_not_consumed():
    stream = object()
    client = ar.wrap_openai(fake_openai([stream]))
    with ar.start_trace("t", persist=False) as tr:
        assert client.chat.completions.create(model="gpt-4o", messages=[], stream=True) is stream
    assert "streamed" in tr.llm_steps[0].output


def test_openai_responses_api():
    response = NS(
        model="gpt-4.1",
        output_text="hello",
        output=[NS(type="function_call", call_id="c1", name="search", arguments='{"q": "x"}')],
        usage=NS(input_tokens=10, output_tokens=5),
    )
    client = NS(responses=NS(create=lambda **kw: response))
    ar.wrap_openai(client)
    with ar.start_trace("t", persist=False) as tr:
        client.responses.create(model="gpt-4.1", input="hi")
    step = tr.llm_steps[0]
    assert step.output == "hello" and step.tool_calls[0].arguments == {"q": "x"}
    assert step.input_tokens == 10


def test_openai_async_client():
    async def create(**kwargs):
        return chat_response(content="async")

    client = ar.wrap_openai(NS(chat=NS(completions=NS(create=create))))

    async def main():
        with ar.start_trace("t", persist=False) as tr:
            await client.chat.completions.create(model="gpt-4o", messages=[])
        return tr

    assert asyncio.run(main()).llm_steps[0].output == "async"


def test_anthropic_messages_records_text_and_tool_use():
    response = NS(
        model="claude-opus-5-5",
        stop_reason="tool_use",
        content=[
            NS(type="text", text="Let me check."),
            NS(type="tool_use", id="tu_1", name="get_weather", input={"city": "Paris"}),
        ],
        usage=NS(input_tokens=500, output_tokens=100, cache_read_input_tokens=50),
    )
    client = NS(messages=NS(create=lambda **kw: response))
    assert ar.wrap(client) is client  # auto-detected as anthropic
    with ar.start_trace("t", persist=False) as tr:
        client.messages.create(model="claude-opus-5-5", system="s", messages=[], max_tokens=10)
    step = tr.llm_steps[0]
    assert step.provider == "anthropic"
    assert step.output == "Let me check."
    assert step.tool_calls[0].name == "get_weather"
    assert step.input_tokens == 550
    assert step.cost_usd == pytest.approx((550 * 4 + 100 * 20) / 1e6)
    assert step.input["system"] == "s"


def test_wrap_unknown_client_and_custom_adapter():
    with pytest.raises(TypeError, match="No agentrecheck adapter"):
        ar.wrap(object())

    class Mine:
        pass

    ar.register_adapter("mine", lambda c: isinstance(c, Mine), lambda c: "wrapped")
    assert ar.wrap(Mine()) == "wrapped"
