"""Data models shared by the tracer, the runner and the cloud API."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# --------------------------------------------------------------------------- traces


class RequestedToolCall(BaseModel):
    """A tool call the model asked for (not necessarily executed)."""

    id: str | None = None
    name: str
    arguments: Any = None


class LLMStep(BaseModel):
    type: Literal["llm"] = "llm"
    index: int = 0
    provider: str = "unknown"
    model: str = "unknown"
    input: Any = None
    output: Any = None
    tool_calls: list[RequestedToolCall] = Field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    started_at: str = Field(default_factory=now_iso)
    error: str | None = None


class ToolStep(BaseModel):
    type: Literal["tool"] = "tool"
    index: int = 0
    name: str
    args: dict[str, Any] = Field(default_factory=dict)
    result: Any = None
    error: str | None = None
    latency_ms: float = 0.0
    started_at: str = Field(default_factory=now_iso)


Step = Annotated[LLMStep | ToolStep, Field(discriminator="type")]


class Trace(BaseModel):
    id: str = Field(default_factory=lambda: new_id("tr"))
    name: str = "agent"
    input: Any = None
    output: Any = None
    error: str | None = None
    started_at: str = Field(default_factory=now_iso)
    ended_at: str | None = None
    latency_ms: float = 0.0
    steps: list[Step] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def add(self, step: LLMStep | ToolStep) -> LLMStep | ToolStep:
        step.index = len(self.steps)
        self.steps.append(step)
        return step

    @property
    def llm_steps(self) -> list[LLMStep]:
        return [s for s in self.steps if isinstance(s, LLMStep)]

    @property
    def tool_steps(self) -> list[ToolStep]:
        return [s for s in self.steps if isinstance(s, ToolStep)]

    @property
    def tool_sequence(self) -> list[str]:
        """Names of executed tools, in order.

        Falls back to the tool calls the model requested when no tool was
        recorded with ``@tool`` / ``record_tool_call``.
        """
        executed = [s.name for s in self.tool_steps]
        if executed:
            return executed
        return [tc.name for s in self.llm_steps for tc in s.tool_calls]

    @property
    def total_cost_usd(self) -> float:
        return round(sum(s.cost_usd for s in self.llm_steps), 8)

    @property
    def total_tokens(self) -> int:
        return sum(s.input_tokens + s.output_tokens for s in self.llm_steps)

    def to_payload(self) -> dict[str, Any]:
        """JSON-ready dict including computed totals (the wire format)."""
        data = self.model_dump(mode="json")
        data.update(
            total_cost_usd=self.total_cost_usd,
            total_tokens=self.total_tokens,
            llm_calls=len(self.llm_steps),
            tool_calls=len(self.tool_steps),
            tool_sequence=self.tool_sequence,
        )
        return data


# --------------------------------------------------------------------------- cases


class ToolArgAssertion(BaseModel):
    tool: str
    index: int = 0  # which call of that tool (0 = first)
    exact: dict[str, Any] | None = None
    regex: dict[str, str] | None = None
    json_schema: dict[str, Any] | None = None


class ToolAssertions(BaseModel):
    sequence: list[str] | None = None
    mode: Literal["exact", "subset"] = "exact"
    args: list[ToolArgAssertion] = Field(default_factory=list)


class JudgeAssertion(BaseModel):
    rubric: str
    min_score: float = 0.7


class OutputAssertions(BaseModel):
    contains: list[str] = Field(default_factory=list)
    not_contains: list[str] = Field(default_factory=list)
    regex: str | None = None
    judge: JudgeAssertion | None = None


class Budgets(BaseModel):
    max_cost_usd: float | None = None
    max_latency_ms: float | None = None
    max_steps: int | None = None


class Assertions(BaseModel):
    tools: ToolAssertions | None = None
    output: OutputAssertions | None = None
    budgets: Budgets | None = None


class Baseline(BaseModel):
    tool_sequence: list[str] = Field(default_factory=list)
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    steps: int = 0
    output: Any = None


class CaseInput(BaseModel):
    args: list[Any] = Field(default_factory=list)
    kwargs: dict[str, Any] = Field(default_factory=dict)


class Case(BaseModel):
    id: str
    name: str = ""
    description: str | None = None
    trace_id: str | None = None
    input: CaseInput = Field(default_factory=CaseInput)
    baseline: Baseline | None = None
    assertions: Assertions = Field(default_factory=Assertions)


# --------------------------------------------------------------------------- results


class CheckResult(BaseModel):
    name: str
    status: Literal["pass", "fail", "skip"]
    message: str = ""


class Diff(BaseModel):
    baseline_tools: list[str] | None = None
    actual_tools: list[str] = Field(default_factory=list)
    tools_changed: bool = False
    baseline_cost_usd: float | None = None
    cost_usd: float = 0.0
    baseline_latency_ms: float | None = None
    latency_ms: float = 0.0
    baseline_steps: int | None = None
    steps: int = 0
    judge_score: float | None = None

    @property
    def cost_delta(self) -> float | None:
        if self.baseline_cost_usd is None:
            return None
        return self.cost_usd - self.baseline_cost_usd

    @property
    def latency_delta(self) -> float | None:
        if self.baseline_latency_ms is None:
            return None
        return self.latency_ms - self.baseline_latency_ms


class CaseResult(BaseModel):
    case_id: str
    name: str = ""
    status: Literal["pass", "fail", "error"] = "pass"
    error: str | None = None
    checks: list[CheckResult] = Field(default_factory=list)
    diff: Diff = Field(default_factory=Diff)
    trace: Trace | None = None

    @property
    def failed_checks(self) -> list[CheckResult]:
        return [c for c in self.checks if c.status == "fail"]


class RunResult(BaseModel):
    id: str = Field(default_factory=lambda: new_id("run"))
    project: str | None = None
    started_at: str = Field(default_factory=now_iso)
    duration_ms: float = 0.0
    git_sha: str | None = None
    git_branch: str | None = None
    results: list[CaseResult] = Field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.status == "pass")

    @property
    def failed(self) -> int:
        return self.total - self.passed

    @property
    def total_cost_usd(self) -> float:
        return round(sum(r.diff.cost_usd for r in self.results), 8)

    @property
    def avg_latency_ms(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.diff.latency_ms for r in self.results) / len(self.results)

    def to_payload(self) -> dict[str, Any]:
        data = self.model_dump(mode="json", exclude={"results"})
        data["summary"] = {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "total_cost_usd": self.total_cost_usd,
            "avg_latency_ms": round(self.avg_latency_ms, 3),
        }
        results = []
        for r in self.results:
            item = r.model_dump(mode="json", exclude={"trace"})
            item["trace"] = r.trace.to_payload() if r.trace else None
            results.append(item)
        data["results"] = results
        return data
