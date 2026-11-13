"""OpenAI adapter: Chat Completions and Responses APIs (non-streaming)."""

from __future__ import annotations

import json
from typing import Any

from ..tracer import record_llm_call
from .base import get, patch_method, register_adapter


def _parse_args(raw: Any) -> Any:
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except ValueError:
            return raw
    return raw


def _error(exc: BaseException | None) -> str | None:
    return f"{type(exc).__name__}: {exc}" if exc else None


def _record_chat(
    kwargs: dict[str, Any],
    response: Any,
    error: BaseException | None,
    started_at: str,
    latency_ms: float,
) -> None:
    streaming = bool(kwargs.get("stream"))
    message = None
    usage = None
    if response is not None and not streaming:
        choices = get(response, "choices") or []
        message = get(choices[0], "message") if choices else None
        usage = get(response, "usage")
    tool_calls = []
    for tc in get(message, "tool_calls") or []:
        fn = get(tc, "function")
        tool_calls.append(
            {
                "id": get(tc, "id"),
                "name": get(fn, "name") or "unknown",
                "arguments": _parse_args(get(fn, "arguments")),
            }
        )
    record_llm_call(
        provider="openai",
        model=str(get(response, "model") or kwargs.get("model") or "unknown"),
        input=kwargs.get("messages"),
        output="<streamed response not captured>" if streaming else get(message, "content"),
        tool_calls=tool_calls,
        input_tokens=int(get(usage, "prompt_tokens") or 0),
        output_tokens=int(get(usage, "completion_tokens") or 0),
        latency_ms=latency_ms,
        error=_error(error),
        started_at=started_at,
    )


def _record_response(
    kwargs: dict[str, Any],
    response: Any,
    error: BaseException | None,
    started_at: str,
    latency_ms: float,
) -> None:
    streaming = bool(kwargs.get("stream"))
    usage = None if streaming else get(response, "usage")
    tool_calls = []
    if not streaming:
        for item in get(response, "output") or []:
            if get(item, "type") == "function_call":
                tool_calls.append(
                    {
                        "id": get(item, "call_id") or get(item, "id"),
                        "name": get(item, "name") or "unknown",
                        "arguments": _parse_args(get(item, "arguments")),
                    }
                )
    record_llm_call(
        provider="openai",
        model=str(get(response, "model") or kwargs.get("model") or "unknown"),
        input={"instructions": kwargs.get("instructions"), "input": kwargs.get("input")},
        output="<streamed response not captured>" if streaming else get(response, "output_text"),
        tool_calls=tool_calls,
        input_tokens=int(get(usage, "input_tokens") or 0),
        output_tokens=int(get(usage, "output_tokens") or 0),
        latency_ms=latency_ms,
        error=_error(error),
        started_at=started_at,
    )


def wrap_openai(client: Any) -> Any:
    """Instrument an ``openai.OpenAI`` / ``AsyncOpenAI`` client (or a compatible one)."""
    completions = getattr(getattr(client, "chat", None), "completions", None)
    if completions is not None and hasattr(completions, "create"):
        patch_method(completions, "create", _record_chat)
    responses = getattr(client, "responses", None)
    if responses is not None and hasattr(responses, "create"):
        patch_method(responses, "create", _record_response)
    return client


def _detect(client: Any) -> bool:
    if type(client).__module__.split(".")[0] == "openai":
        return True
    return hasattr(getattr(client, "chat", None), "completions")


register_adapter("openai", _detect, wrap_openai)
