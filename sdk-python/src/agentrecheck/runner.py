"""Replay test cases against the current agent code and compare to baseline."""

from __future__ import annotations

import asyncio
import importlib
import inspect
import os
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .assertions import evaluate, judge_score
from .config import Config, RegressionConfig
from .judge import Judge
from .models import Case, CaseResult, CheckResult, Diff, RunResult, Trace
from .tracer import start_trace, to_jsonable


class EntrypointError(Exception):
    pass


def resolve_entrypoint(spec: str, root: Path | None = None) -> Callable[..., Any]:
    """Import ``module:function`` relative to ``root`` (default: cwd)."""
    module_name, sep, attr = spec.partition(":")
    if not sep or not module_name or not attr:
        raise EntrypointError(f"Entrypoint must look like 'module:function', got '{spec}'")
    root_str = str((root or Path.cwd()).resolve())
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:
        raise EntrypointError(f"Could not import '{module_name}': {exc}") from exc
    fn = getattr(module, attr, None)
    if not callable(fn):
        raise EntrypointError(f"'{module_name}' has no callable '{attr}'")
    return fn


def _pct_increase(actual: float, baseline: float) -> float:
    return (actual - baseline) / baseline * 100


def compute_diff(case: Case, trace: Trace, checks: list[CheckResult]) -> Diff:
    base = case.baseline
    actual_tools = trace.tool_sequence
    return Diff(
        baseline_tools=base.tool_sequence if base else None,
        actual_tools=actual_tools,
        tools_changed=bool(base) and base.tool_sequence != actual_tools,  # type: ignore[union-attr]
        baseline_cost_usd=base.cost_usd if base else None,
        cost_usd=trace.total_cost_usd,
        baseline_latency_ms=base.latency_ms if base else None,
        latency_ms=trace.latency_ms,
        baseline_steps=base.steps if base else None,
        steps=len(trace.steps),
        judge_score=judge_score(checks),
    )


def regression_checks(case: Case, trace: Trace, cfg: RegressionConfig) -> list[CheckResult]:
    """Baseline comparisons that fail the case when a threshold is exceeded."""
    base = case.baseline
    checks: list[CheckResult] = []
    if base is None:
        return checks
    if cfg.max_cost_increase_pct is not None and base.cost_usd > 0:
        pct = _pct_increase(trace.total_cost_usd, base.cost_usd)
        status = "fail" if pct > cfg.max_cost_increase_pct else "pass"
        checks.append(
            CheckResult(
                name="baseline.cost",
                status=status,  # type: ignore[arg-type]
                message=f"{pct:+.1f}% vs baseline (limit +{cfg.max_cost_increase_pct:g}%)",
            )
        )
    if cfg.max_latency_increase_pct is not None and base.latency_ms > 0:
        pct = _pct_increase(trace.latency_ms, base.latency_ms)
        status = "fail" if pct > cfg.max_latency_increase_pct else "pass"
        checks.append(
            CheckResult(
                name="baseline.latency",
                status=status,  # type: ignore[arg-type]
                message=f"{pct:+.1f}% vs baseline (limit +{cfg.max_latency_increase_pct:g}%)",
            )
        )
    return checks


def run_case(
    case: Case,
    fn: Callable[..., Any],
    *,
    judge: Judge | None = None,
    regression: RegressionConfig | None = None,
) -> CaseResult:
    regression = regression or RegressionConfig()
    error: str | None = None
    trace: Trace | None = None
    try:
        with start_trace(
            case.id,
            input={"args": case.input.args, "kwargs": case.input.kwargs},
            metadata={"case_id": case.id, "source": "agentrecheck run"},
            persist=False,
        ) as trace:
            result = fn(*case.input.args, **case.input.kwargs)
            if inspect.isawaitable(result):
                result = asyncio.run(_await(result))
            trace.output = to_jsonable(result)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"

    assert trace is not None
    checks = evaluate(case, trace, judge) + regression_checks(case, trace, regression)
    diff = compute_diff(case, trace, checks)
    if error is not None:
        status = "error"
    elif any(c.status == "fail" for c in checks):
        status = "fail"
    else:
        status = "pass"
    return CaseResult(
        case_id=case.id,
        name=case.name or case.id,
        status=status,  # type: ignore[arg-type]
        error=error,
        checks=checks,
        diff=diff,
        trace=trace,
    )


async def _await(awaitable: Any) -> Any:
    return await awaitable


def git_info() -> tuple[str | None, str | None]:
    """Commit sha and branch, from CI env vars or the local repo."""
    sha = os.environ.get("GITHUB_SHA")
    branch = os.environ.get("GITHUB_HEAD_REF") or os.environ.get("GITHUB_REF_NAME")

    def git(*args: str) -> str | None:
        try:
            out = subprocess.run(
                ["git", *args], capture_output=True, text=True, timeout=5, check=False
            )
        except (OSError, subprocess.SubprocessError):
            return None
        return out.stdout.strip() or None if out.returncode == 0 else None

    return sha or git("rev-parse", "HEAD"), branch or git("rev-parse", "--abbrev-ref", "HEAD")


def run_cases(
    cases: list[Case],
    fn: Callable[..., Any],
    *,
    config: Config | None = None,
    judge: Judge | None = None,
) -> RunResult:
    config = config or Config()
    sha, branch = git_info()
    run = RunResult(project=config.project, git_sha=sha, git_branch=branch)
    started = time.perf_counter()
    for case in cases:
        run.results.append(run_case(case, fn, judge=judge, regression=config.regression))
    run.duration_ms = round((time.perf_counter() - started) * 1000, 3)
    return run
