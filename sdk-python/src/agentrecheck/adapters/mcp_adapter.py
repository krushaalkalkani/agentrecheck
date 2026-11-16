"""MCP adapter: record every tool call an agent makes through an MCP client.

Works with the official ``mcp`` Python SDK: ``mcp.Client`` (2.x) and
``mcp.ClientSession`` (1.x and 2.x). Anything else with an async
``call_tool(name, arguments)`` method works too.

    from mcp import Client
    from agentrecheck import wrap_mcp

    async with Client(server_params) as client:
        wrap_mcp(client)
        await client.call_tool("lookup_order", {"order_id": "A1002"})

Each call becomes a tool step on the active trace, so tool-sequence and
tool-argument assertions work the same as for ``@tool`` functions.
"""

from __future__ import annotations

import inspect
import json
import time
import warnings
from typing import Any

from ..models import now_iso
from ..tracer import current_trace, record_tool_call
from .base import get, register_adapter


def result_to_jsonable(result: Any) -> Any:
    """Reduce a ``CallToolResult`` to plain data worth storing in a trace.

    Structured content wins. Otherwise the text blocks are joined, and parsed
    as JSON when they hold JSON (the common case for servers that return dicts).
    Non-text blocks are kept as a short ``[type]`` marker.
    """
    structured = get(result, "structured_content", get(result, "structuredContent"))
    if structured is not None:
        return structured
    content = get(result, "content")
    if content is None:
        return result if isinstance(result, str | int | float | bool | dict | list) else None
    parts: list[str] = []
    for block in content:
        text = get(block, "text")
        parts.append(text if isinstance(text, str) else f"[{get(block, 'type', 'content')}]")
    joined = "\n".join(parts)
    try:
        return json.loads(joined)
    except ValueError:
        return joined


def _is_error(result: Any) -> bool:
    return bool(get(result, "is_error", get(result, "isError", False)))


def _error_text(result: Any) -> str:
    data = result_to_jsonable(result)
    text = data if isinstance(data, str) else json.dumps(data, default=str)
    return f"MCPToolError: {text}" if text else "MCPToolError"


def wrap_mcp(client: Any, *, prefix: str | None = None) -> Any:
    """Patch ``client.call_tool`` so each call is recorded as a tool step.

    ``prefix`` is prepended to the recorded tool name (``"orders."`` turns
    ``lookup`` into ``orders.lookup``). Use it when an agent talks to several
    MCP servers that expose tools with the same name.

    The client is patched in place and returned. Wrapping twice is a no-op.
    Outside a trace the original method runs untouched.
    """
    original = getattr(client, "call_tool", None)
    if original is None or not inspect.iscoroutinefunction(original):
        raise TypeError(
            f"wrap_mcp() needs an object with an async call_tool() method, "
            f"got {type(client).__module__}.{type(client).__name__}."
        )
    if getattr(original, "__agentrecheck_wrapped__", False):
        return client

    async def call_tool(name: str, arguments: dict[str, Any] | None = None, *args: Any, **kw: Any):
        if current_trace() is None:
            return await original(name, arguments, *args, **kw)
        recorded = f"{prefix}{name}" if prefix else name
        started_at, t0 = now_iso(), time.perf_counter()
        try:
            result = await original(name, arguments, *args, **kw)
        except Exception as exc:
            ms = (time.perf_counter() - t0) * 1000
            _safe_record(recorded, arguments, None, f"{type(exc).__name__}: {exc}", ms, started_at)
            raise
        ms = (time.perf_counter() - t0) * 1000
        if _is_error(result):
            _safe_record(recorded, arguments, None, _error_text(result), ms, started_at)
        else:
            _safe_record(recorded, arguments, result_to_jsonable(result), None, ms, started_at)
        return result

    call_tool.__agentrecheck_wrapped__ = True  # type: ignore[attr-defined]
    client.call_tool = call_tool
    return client


def _safe_record(
    name: str,
    arguments: dict[str, Any] | None,
    result: Any,
    error: str | None,
    latency_ms: float,
    started_at: str,
) -> None:
    try:
        record_tool_call(
            name, arguments, result, error=error, latency_ms=latency_ms, started_at=started_at
        )
    except Exception as exc:  # instrumentation must never break the agent
        warnings.warn(f"agentrecheck: failed to record MCP tool call: {exc}", stacklevel=3)


def _detect(client: Any) -> bool:
    module = type(client).__module__ or ""
    return (module == "mcp" or module.startswith("mcp.")) and hasattr(client, "call_tool")


register_adapter("mcp", _detect, wrap_mcp)
