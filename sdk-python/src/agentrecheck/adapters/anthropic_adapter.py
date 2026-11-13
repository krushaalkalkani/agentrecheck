"""Anthropic adapter: Messages API (non-streaming)."""

from __future__ import annotations

from typing import Any

from ..tracer import record_llm_call
from .base import get, patch_method, register_adapter


def _record_message(
    kwargs: dict[str, Any],
    response: Any,
    error: BaseException | None,
    started_at: str,
    latency_ms: float,
) -> None:
    streaming = bool(kwargs.get("stream"))
    text_parts: list[str] = []
    tool_calls = []
    usage = None
    if response is not None and not streaming:
        usage = get(response, "usage")
        for block in get(response, "content") or []:
            kind = get(block, "type")
            if kind == "text":
                text_parts.append(str(get(block, "text") or ""))
            elif kind == "tool_use":
                tool_calls.append(
                    {
                        "id": get(block, "id"),
                        "name": get(block, "name") or "unknown",
                        "arguments": get(block, "input"),
                    }
                )
    # Cached tokens are billed at different rates; count them as input for a
    # conservative (slightly high) estimate.
    input_tokens = (
        int(get(usage, "input_tokens") or 0)
        + int(get(usage, "cache_creation_input_tokens") or 0)
        + int(get(usage, "cache_read_input_tokens") or 0)
    )
    record_llm_call(
        provider="anthropic",
        model=str(get(response, "model") or kwargs.get("model") or "unknown"),
        input={"system": kwargs.get("system"), "messages": kwargs.get("messages")},
        output="<streamed response not captured>" if streaming else "".join(text_parts) or None,
        tool_calls=tool_calls,
        input_tokens=input_tokens,
        output_tokens=int(get(usage, "output_tokens") or 0),
        latency_ms=latency_ms,
        error=f"{type(error).__name__}: {error}" if error else None,
        started_at=started_at,
    )


def wrap_anthropic(client: Any) -> Any:
    """Instrument an ``anthropic.Anthropic`` / ``AsyncAnthropic`` client."""
    messages = getattr(client, "messages", None)
    if messages is not None and hasattr(messages, "create"):
        patch_method(messages, "create", _record_message)
    return client


def _detect(client: Any) -> bool:
    if type(client).__module__.split(".")[0] == "anthropic":
        return True
    return hasattr(getattr(client, "messages", None), "create") and not hasattr(client, "chat")


register_adapter("anthropic", _detect, wrap_anthropic)
