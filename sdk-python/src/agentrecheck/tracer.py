"""Recording agent runs: ``@trace``, ``start_trace``, ``@tool`` and manual recorders."""

from __future__ import annotations

import dataclasses
import functools
import inspect
import os
import time
import warnings
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, TypeVar, overload

from pydantic import BaseModel

from . import storage
from .client import CloudClient
from .models import LLMStep, RequestedToolCall, ToolStep, Trace, now_iso
from .pricing import cost_for

F = TypeVar("F", bound=Callable[..., Any])

_current: ContextVar[Trace | None] = ContextVar("agentrecheck_trace", default=None)


def current_trace() -> Trace | None:
    """The trace being recorded in this context, if any."""
    return _current.get()


def to_jsonable(value: Any, _depth: int = 0) -> Any:
    """Best-effort conversion of arbitrary Python values to JSON-safe data."""
    if _depth > 8:
        return repr(value)
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, BaseModel):
        return to_jsonable(value.model_dump(mode="json"), _depth + 1)
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return to_jsonable(dataclasses.asdict(value), _depth + 1)
    if isinstance(value, dict):
        return {str(k): to_jsonable(v, _depth + 1) for k, v in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        return [to_jsonable(v, _depth + 1) for v in value]
    if hasattr(value, "model_dump"):
        try:
            return to_jsonable(value.model_dump(), _depth + 1)
        except Exception:
            pass
    if hasattr(value, "__dict__") and not callable(value):
        public = {k: v for k, v in vars(value).items() if not k.startswith("_")}
        if public:
            return to_jsonable(public, _depth + 1)
    return repr(value)


def _persist(tr: Trace) -> None:
    if os.environ.get("AGENTRECHECK_DISABLED") == "1":
        return
    try:
        storage.save_trace(tr)
    except OSError as exc:
        warnings.warn(f"agentrecheck: could not save trace locally: {exc}", stacklevel=3)
    client = CloudClient.from_env()
    if client is not None:
        try:
            client.upload_trace(tr)
        except Exception as exc:  # uploading must never break the agent
            warnings.warn(f"agentrecheck: trace upload failed: {exc}", stacklevel=3)


@contextmanager
def start_trace(
    name: str = "agent",
    *,
    input: Any = None,
    metadata: dict[str, Any] | None = None,
    persist: bool = True,
) -> Iterator[Trace]:
    """Record everything inside the block as one agent run.

    Nested calls join the outer trace instead of starting a new one, so a
    ``@trace``-decorated agent can be replayed by the runner transparently.
    """
    existing = _current.get()
    if existing is not None:
        yield existing
        return

    tr = Trace(name=name, input=to_jsonable(input), metadata=metadata or {})
    token = _current.set(tr)
    started = time.perf_counter()
    try:
        yield tr
    except BaseException as exc:
        tr.error = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        tr.latency_ms = round((time.perf_counter() - started) * 1000, 3)
        tr.ended_at = now_iso()
        _current.reset(token)
        if persist:
            _persist(tr)


@overload
def trace(fn: F) -> F: ...
@overload
def trace(
    *, name: str | None = None, metadata: dict[str, Any] | None = None
) -> Callable[[F], F]: ...
def trace(
    fn: Callable[..., Any] | None = None,
    *,
    name: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> Any:
    """Decorator that records each call of an agent function as a trace."""

    def decorate(func: Callable[..., Any]) -> Callable[..., Any]:
        trace_name = name or func.__name__

        def _input(args: tuple[Any, ...], kwargs: dict[str, Any]) -> dict[str, Any]:
            return {"args": list(args), "kwargs": kwargs}

        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                nested = _current.get() is not None
                with start_trace(trace_name, input=_input(args, kwargs), metadata=metadata) as tr:
                    result = await func(*args, **kwargs)
                    if not nested:
                        tr.output = to_jsonable(result)
                    return result

            return async_wrapper

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            nested = _current.get() is not None
            with start_trace(trace_name, input=_input(args, kwargs), metadata=metadata) as tr:
                result = func(*args, **kwargs)
                if not nested:
                    tr.output = to_jsonable(result)
                return result

        return wrapper

    return decorate(fn) if fn is not None else decorate


def record_tool_call(
    name: str,
    args: dict[str, Any] | None = None,
    result: Any = None,
    *,
    error: str | None = None,
    latency_ms: float = 0.0,
    started_at: str | None = None,
) -> ToolStep | None:
    """Manually record a tool call on the current trace (no-op outside a trace)."""
    tr = _current.get()
    if tr is None:
        return None
    step = ToolStep(
        name=name,
        args=to_jsonable(args or {}),
        result=to_jsonable(result),
        error=error,
        latency_ms=round(latency_ms, 3),
        started_at=started_at or now_iso(),
    )
    tr.add(step)
    return step


def record_llm_call(
    *,
    model: str,
    provider: str = "custom",
    input: Any = None,
    output: Any = None,
    tool_calls: list[dict[str, Any]] | None = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cost_usd: float | None = None,
    latency_ms: float = 0.0,
    error: str | None = None,
    started_at: str | None = None,
) -> LLMStep | None:
    """Manually record an LLM call on the current trace (no-op outside a trace)."""
    tr = _current.get()
    if tr is None:
        return None
    step = LLMStep(
        provider=provider,
        model=model,
        input=to_jsonable(input),
        output=to_jsonable(output),
        tool_calls=[RequestedToolCall.model_validate(tc) for tc in (tool_calls or [])],
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost_usd if cost_usd is not None else cost_for(model, input_tokens, output_tokens),
        latency_ms=round(latency_ms, 3),
        error=error,
        started_at=started_at or now_iso(),
    )
    tr.add(step)
    return step


def _bound_args(func: Callable[..., Any], args: tuple[Any, ...], kwargs: dict[str, Any]) -> dict:
    try:
        bound = inspect.signature(func).bind(*args, **kwargs)
        bound.apply_defaults()
        return {k: v for k, v in bound.arguments.items() if k not in ("self", "cls")}
    except (TypeError, ValueError):
        return {"args": list(args), "kwargs": kwargs}


@overload
def tool(fn: F) -> F: ...
@overload
def tool(*, name: str | None = None) -> Callable[[F], F]: ...
def tool(fn: Callable[..., Any] | None = None, *, name: str | None = None) -> Any:
    """Decorator that records each call of a function as a tool step."""

    def decorate(func: Callable[..., Any]) -> Callable[..., Any]:
        tool_name = name or func.__name__

        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                if _current.get() is None:
                    return await func(*args, **kwargs)
                started_at, t0 = now_iso(), time.perf_counter()
                call_args = _bound_args(func, args, kwargs)
                try:
                    result = await func(*args, **kwargs)
                except Exception as exc:
                    ms = (time.perf_counter() - t0) * 1000
                    record_tool_call(
                        tool_name,
                        call_args,
                        error=f"{type(exc).__name__}: {exc}",
                        latency_ms=ms,
                        started_at=started_at,
                    )
                    raise
                ms = (time.perf_counter() - t0) * 1000
                record_tool_call(tool_name, call_args, result, latency_ms=ms, started_at=started_at)
                return result

            return async_wrapper

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if _current.get() is None:
                return func(*args, **kwargs)
            started_at, t0 = now_iso(), time.perf_counter()
            call_args = _bound_args(func, args, kwargs)
            try:
                result = func(*args, **kwargs)
            except Exception as exc:
                ms = (time.perf_counter() - t0) * 1000
                record_tool_call(
                    tool_name,
                    call_args,
                    error=f"{type(exc).__name__}: {exc}",
                    latency_ms=ms,
                    started_at=started_at,
                )
                raise
            ms = (time.perf_counter() - t0) * 1000
            record_tool_call(tool_name, call_args, result, latency_ms=ms, started_at=started_at)
            return result

        return wrapper

    return decorate(fn) if fn is not None else decorate
