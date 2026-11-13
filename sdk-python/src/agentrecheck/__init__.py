"""AgentRecheck: CI/CD for AI agents."""

__version__ = "0.1.0"

from .adapters import register_adapter, wrap, wrap_anthropic, wrap_openai  # noqa: E402
from .models import Case, CaseResult, LLMStep, RunResult, ToolStep, Trace  # noqa: E402
from .pricing import register_price  # noqa: E402
from .tracer import (  # noqa: E402
    current_trace,
    record_llm_call,
    record_tool_call,
    start_trace,
    tool,
    trace,
)

__all__ = [
    "Case",
    "CaseResult",
    "LLMStep",
    "RunResult",
    "ToolStep",
    "Trace",
    "__version__",
    "current_trace",
    "record_llm_call",
    "record_tool_call",
    "register_adapter",
    "register_price",
    "start_trace",
    "tool",
    "trace",
    "wrap",
    "wrap_anthropic",
    "wrap_openai",
]
