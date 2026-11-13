"""Turn a recorded trace into a test case."""

from __future__ import annotations

import re
from typing import Literal

from .models import (
    Assertions,
    Baseline,
    Budgets,
    Case,
    CaseInput,
    ToolAssertions,
    Trace,
)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_") or "case"


def case_input_from_trace(trace: Trace) -> CaseInput:
    raw = trace.input
    if isinstance(raw, dict) and set(raw) <= {"args", "kwargs"} and raw:
        return CaseInput(args=list(raw.get("args") or []), kwargs=dict(raw.get("kwargs") or {}))
    if raw is None:
        return CaseInput()
    return CaseInput(args=[raw])


def snapshot_trace(
    trace: Trace,
    *,
    case_id: str | None = None,
    name: str | None = None,
    mode: Literal["exact", "subset"] = "exact",
) -> Case:
    """Build a case whose baseline and default assertions come from ``trace``.

    The generated assertions pin the tool sequence and set generous budgets
    (2x the recorded cost and steps). Edit the YAML to tighten or extend them.
    """
    sequence = trace.tool_sequence
    steps = len(trace.steps)
    cost = trace.total_cost_usd
    budgets = Budgets(
        max_steps=max(steps * 2, steps + 2),
        max_cost_usd=round(cost * 2, 6) if cost > 0 else None,
    )
    return Case(
        id=case_id or _slug(f"{trace.name}_{trace.id[-6:]}"),
        name=name or f"{trace.name} ({trace.id})",
        trace_id=trace.id,
        input=case_input_from_trace(trace),
        baseline=Baseline(
            tool_sequence=sequence,
            cost_usd=cost,
            latency_ms=trace.latency_ms,
            steps=steps,
            output=trace.output,
        ),
        assertions=Assertions(
            tools=ToolAssertions(sequence=sequence, mode=mode),
            budgets=budgets,
        ),
    )
