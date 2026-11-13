"""Evaluate a case's assertions against a fresh trace."""

from __future__ import annotations

import json
import re
from typing import Any

import jsonschema

from .judge import Judge
from .models import Case, CheckResult, ToolArgAssertion, Trace


def _ok(name: str, message: str = "") -> CheckResult:
    return CheckResult(name=name, status="pass", message=message)


def _fail(name: str, message: str) -> CheckResult:
    return CheckResult(name=name, status="fail", message=message)


def output_text(output: Any) -> str:
    if output is None:
        return ""
    return output if isinstance(output, str) else json.dumps(output, default=str)


def is_subsequence(expected: list[str], actual: list[str]) -> bool:
    it = iter(actual)
    return all(item in it for item in expected)


def _check_sequence(expected: list[str], mode: str, actual: list[str]) -> CheckResult:
    name = f"tools.sequence ({mode})"
    if mode == "exact":
        if actual == expected:
            return _ok(name)
        return _fail(name, f"expected {expected}, got {actual}")
    if is_subsequence(expected, actual):
        return _ok(name)
    return _fail(name, f"expected {expected} to appear in order within {actual}")


def _check_args(spec: ToolArgAssertion, trace: Trace) -> list[CheckResult]:
    label = f"tools.args[{spec.tool}#{spec.index}]"
    calls = [s for s in trace.tool_steps if s.name == spec.tool]
    if spec.index >= len(calls):
        return [_fail(label, f"tool '{spec.tool}' was called {len(calls)} time(s)")]
    args = calls[spec.index].args
    results: list[CheckResult] = []

    if spec.exact is not None:
        if args == spec.exact:
            results.append(_ok(f"{label}.exact"))
        else:
            results.append(_fail(f"{label}.exact", f"expected {spec.exact}, got {args}"))

    if spec.regex is not None:
        problems = []
        for key, pattern in spec.regex.items():
            if key not in args:
                problems.append(f"missing arg '{key}'")
            elif not re.search(pattern, str(args[key])):
                problems.append(f"{key}={args[key]!r} does not match /{pattern}/")
        if problems:
            results.append(_fail(f"{label}.regex", "; ".join(problems)))
        else:
            results.append(_ok(f"{label}.regex"))

    if spec.json_schema is not None:
        try:
            jsonschema.validate(args, spec.json_schema)
            results.append(_ok(f"{label}.json_schema"))
        except jsonschema.ValidationError as exc:
            results.append(_fail(f"{label}.json_schema", exc.message))
        except jsonschema.SchemaError as exc:
            results.append(_fail(f"{label}.json_schema", f"invalid schema: {exc.message}"))

    return results


def evaluate(case: Case, trace: Trace, judge: Judge | None = None) -> list[CheckResult]:
    """Run every assertion in ``case`` against ``trace``."""
    checks: list[CheckResult] = []
    a = case.assertions

    if a.tools is not None:
        if a.tools.sequence is not None:
            checks.append(_check_sequence(a.tools.sequence, a.tools.mode, trace.tool_sequence))
        for spec in a.tools.args:
            checks.extend(_check_args(spec, trace))

    if a.output is not None:
        text = output_text(trace.output)
        lowered = text.lower()
        for needle in a.output.contains:
            name = f"output.contains[{needle!r}]"
            if needle.lower() in lowered:
                checks.append(_ok(name))
            else:
                checks.append(_fail(name, "not found in output"))
        for needle in a.output.not_contains:
            name = f"output.not_contains[{needle!r}]"
            if needle.lower() in lowered:
                checks.append(_fail(name, "found in output"))
            else:
                checks.append(_ok(name))
        if a.output.regex is not None:
            name = f"output.regex[/{a.output.regex}/]"
            if re.search(a.output.regex, text):
                checks.append(_ok(name))
            else:
                checks.append(_fail(name, "no match in output"))
        if a.output.judge is not None:
            checks.append(_check_judge(case, trace, judge))

    if a.budgets is not None:
        b = a.budgets
        if b.max_cost_usd is not None:
            cost = trace.total_cost_usd
            name = "budgets.max_cost_usd"
            if cost <= b.max_cost_usd:
                checks.append(_ok(name))
            else:
                checks.append(_fail(name, f"${cost:.6f} > ${b.max_cost_usd:.6f}"))
        if b.max_latency_ms is not None:
            name = "budgets.max_latency_ms"
            if trace.latency_ms <= b.max_latency_ms:
                checks.append(_ok(name))
            else:
                checks.append(_fail(name, f"{trace.latency_ms:.0f}ms > {b.max_latency_ms:.0f}ms"))
        if b.max_steps is not None:
            name = "budgets.max_steps"
            steps = len(trace.steps)
            if steps <= b.max_steps:
                checks.append(_ok(name))
            else:
                checks.append(_fail(name, f"{steps} steps > {b.max_steps}"))

    return checks


def _check_judge(case: Case, trace: Trace, judge: Judge | None) -> CheckResult:
    assert case.assertions.output is not None and case.assertions.output.judge is not None
    spec = case.assertions.output.judge
    name = "output.judge"
    if judge is None:
        return CheckResult(
            name=name,
            status="skip",
            message="no judge configured (set OPENAI_API_KEY or ANTHROPIC_API_KEY)",
        )
    try:
        verdict = judge.score(rubric=spec.rubric, input=trace.input, output=trace.output)
    except Exception as exc:
        return _fail(name, f"judge error: {exc}")
    message = f"score={verdict.score:.2f} (min {spec.min_score:.2f}) {verdict.reasoning}".strip()
    if verdict.score >= spec.min_score:
        return _ok(name, message)
    return _fail(name, message)


def judge_score(checks: list[CheckResult]) -> float | None:
    """Extract the judge score from a list of checks, if a judge ran."""
    for check in checks:
        if check.name == "output.judge":
            match = re.match(r"score=([0-9.]+)", check.message)
            if match:
                return float(match.group(1))
    return None
