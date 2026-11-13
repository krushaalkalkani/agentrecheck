"""Adapter plumbing: patch an SDK method so every call is recorded as an LLM step.

An adapter is two functions:

* ``detect(client) -> bool`` — does this adapter know how to wrap the client?
* ``wrap(client) -> client`` — patch it in place and return it.

Register your own with ``register_adapter`` to support another provider.
"""

from __future__ import annotations

import inspect
import time
import warnings
from collections.abc import Callable
from typing import Any

from ..models import now_iso
from ..tracer import current_trace

# (kwargs, response, error, started_at, latency_ms) -> None
Recorder = Callable[[dict[str, Any], Any, BaseException | None, str, float], None]

_ADAPTERS: dict[str, tuple[Callable[[Any], bool], Callable[[Any], Any]]] = {}


def register_adapter(name: str, detect: Callable[[Any], bool], wrap: Callable[[Any], Any]) -> None:
    _ADAPTERS[name] = (detect, wrap)


def wrap(client: Any) -> Any:
    """Auto-detect the client's provider and instrument it."""
    for detect, wrap_fn in _ADAPTERS.values():
        if detect(client):
            return wrap_fn(client)
    raise TypeError(
        f"No agentrecheck adapter for {type(client).__module__}.{type(client).__name__}. "
        "Use record_llm_call() or register_adapter()."
    )


def get(obj: Any, key: str, default: Any = None) -> Any:
    """Read ``key`` from a dict or an attribute, whichever the SDK returned."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _safe_record(recorder: Recorder, *args: Any) -> None:
    try:
        recorder(*args)
    except Exception as exc:  # instrumentation must never break the agent
        warnings.warn(f"agentrecheck: failed to record LLM call: {exc}", stacklevel=3)


def patch_method(obj: Any, attr: str, recorder: Recorder) -> None:
    """Replace ``obj.attr`` with a wrapper that records each call (sync or async)."""
    original = getattr(obj, attr)
    if getattr(original, "__agentrecheck_wrapped__", False):
        return

    if inspect.iscoroutinefunction(original):

        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            if current_trace() is None:
                return await original(*args, **kwargs)
            started_at, t0 = now_iso(), time.perf_counter()
            try:
                response = await original(*args, **kwargs)
            except Exception as exc:
                ms = (time.perf_counter() - t0) * 1000
                _safe_record(recorder, kwargs, None, exc, started_at, ms)
                raise
            ms = (time.perf_counter() - t0) * 1000
            _safe_record(recorder, kwargs, response, None, started_at, ms)
            return response

        wrapper: Callable[..., Any] = async_wrapper
    else:

        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            if current_trace() is None:
                return original(*args, **kwargs)
            started_at, t0 = now_iso(), time.perf_counter()
            try:
                response = original(*args, **kwargs)
            except Exception as exc:
                ms = (time.perf_counter() - t0) * 1000
                _safe_record(recorder, kwargs, None, exc, started_at, ms)
                raise
            ms = (time.perf_counter() - t0) * 1000
            _safe_record(recorder, kwargs, response, None, started_at, ms)
            return response

        wrapper = sync_wrapper

    wrapper.__agentrecheck_wrapped__ = True  # type: ignore[attr-defined]
    setattr(obj, attr, wrapper)
