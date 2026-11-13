"""Render run results: a terminal table with diffs, and markdown for CI summaries."""

from __future__ import annotations

from difflib import SequenceMatcher

from rich.console import Console
from rich.table import Table

from .models import CaseResult, RunResult, Trace

STATUS_STYLE = {"pass": "green", "fail": "red", "error": "red", "skip": "yellow"}
STATUS_LABEL = {"pass": "PASS", "fail": "FAIL", "error": "ERROR", "skip": "SKIP"}


def sequence_diff(baseline: list[str], actual: list[str]) -> list[tuple[str, str]]:
    """Diff two tool sequences into ``(marker, tool)`` rows; marker is ' ', '-' or '+'."""
    rows: list[tuple[str, str]] = []
    matcher = SequenceMatcher(a=baseline, b=actual, autojunk=False)
    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op == "equal":
            rows.extend((" ", t) for t in baseline[i1:i2])
        else:
            rows.extend(("-", t) for t in baseline[i1:i2])
            rows.extend(("+", t) for t in actual[j1:j2])
    return rows


def fmt_cost(value: float) -> str:
    return f"${value:.5f}"


def fmt_ms(value: float) -> str:
    return f"{value / 1000:.2f}s" if value >= 1000 else f"{value:.0f}ms"


def fmt_delta(actual: float, baseline: float | None, kind: str) -> str:
    """Human-readable delta such as '+$0.00012 (+18%)'."""
    if baseline is None:
        return ""
    delta = actual - baseline
    sign = "+" if delta >= 0 else "-"
    amount = fmt_cost(abs(delta)) if kind == "cost" else fmt_ms(abs(delta))
    if baseline > 0:
        return f"{sign}{amount} ({delta / baseline * 100:+.0f}%)"
    return f"{sign}{amount}"


def _tools_cell(result: CaseResult) -> str:
    if not result.diff.tools_changed:
        return "same" if result.diff.baseline_tools is not None else "-"
    return "changed"


def _with_pct(text: str, actual: float, baseline: float | None) -> str:
    """Append a compact percentage delta: '$0.00012 (+18%)'."""
    if baseline is None or baseline <= 0:
        return text
    return f"{text} ({(actual - baseline) / baseline * 100:+.0f}%)"


def render_run(run: RunResult, console: Console | None = None) -> None:
    console = console or Console()
    table = Table(title=f"AgentRecheck run {run.id}", title_justify="left", expand=False)
    table.add_column("Case", style="bold", no_wrap=True)
    table.add_column("Result", no_wrap=True)
    table.add_column("Tools", no_wrap=True)
    table.add_column("Cost (vs base)", justify="right", no_wrap=True)
    table.add_column("Latency (vs base)", justify="right", no_wrap=True)
    judged = any(r.diff.judge_score is not None for r in run.results)
    if judged:
        table.add_column("Judge", justify="right")

    for r in run.results:
        d = r.diff
        style = STATUS_STYLE[r.status]
        tools = _tools_cell(r)
        row = [
            r.case_id,
            f"[{style}]{STATUS_LABEL[r.status]}[/{style}]",
            f"[yellow]{tools}[/yellow]" if tools == "changed" else tools,
            _with_pct(fmt_cost(d.cost_usd), d.cost_usd, d.baseline_cost_usd),
            _with_pct(fmt_ms(d.latency_ms), d.latency_ms, d.baseline_latency_ms),
        ]
        if judged:
            row.append(f"{d.judge_score:.2f}" if d.judge_score is not None else "-")
        table.add_row(*row)
    console.print(table)

    for r in run.results:
        if r.status == "pass":
            continue
        console.print(f"\n[bold red]✗ {r.case_id}[/bold red]  {r.name}")
        if r.error:
            console.print(f"  [red]agent raised:[/red] {r.error}")
        for check in r.failed_checks:
            console.print(f"  [red]✗[/red] {check.name}: {check.message}", highlight=False)
        if r.diff.tools_changed and r.diff.baseline_tools is not None:
            console.print("  tool sequence (baseline → current):")
            for marker, tool in sequence_diff(r.diff.baseline_tools, r.diff.actual_tools):
                color = {"-": "red", "+": "green"}.get(marker)
                line = f"    {marker} {tool}"
                console.print(f"[{color}]{line}[/{color}]" if color else line, highlight=False)

    skipped = [c for r in run.results for c in r.checks if c.status == "skip"]
    if skipped:
        console.print(f"\n[yellow]{len(skipped)} check(s) skipped:[/yellow] {skipped[0].message}")

    color = "green" if run.failed == 0 else "red"
    console.print(
        f"\n[bold {color}]{run.passed}/{run.total} passed[/bold {color}]"
        f" · total cost {fmt_cost(run.total_cost_usd)}"
        f" · avg latency {fmt_ms(run.avg_latency_ms)}"
    )
    if run.failed:
        console.print(f"[bold red]{run.failed} regression(s) detected.[/bold red]")


def render_markdown(run: RunResult) -> str:
    """Markdown summary, suitable for ``$GITHUB_STEP_SUMMARY`` or a PR comment."""
    icon = "✅" if run.failed == 0 else "❌"
    lines = [
        f"## {icon} AgentRecheck: {run.passed}/{run.total} passed",
        "",
        "| Case | Result | Tools | Cost | Cost Δ | Latency | Latency Δ | Judge |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for r in run.results:
        d = r.diff
        judge = f"{d.judge_score:.2f}" if d.judge_score is not None else "-"
        lines.append(
            f"| `{r.case_id}` | {STATUS_LABEL[r.status]} | {_tools_cell(r)} "
            f"| {fmt_cost(d.cost_usd)} | {fmt_delta(d.cost_usd, d.baseline_cost_usd, 'cost')} "
            f"| {fmt_ms(d.latency_ms)} "
            f"| {fmt_delta(d.latency_ms, d.baseline_latency_ms, 'latency')} | {judge} |"
        )
    for r in run.results:
        if r.status == "pass":
            continue
        lines += ["", f"### ❌ `{r.case_id}`"]
        if r.error:
            lines.append(f"- agent raised: `{r.error}`")
        lines += [f"- **{c.name}**: {c.message}" for c in r.failed_checks]
        if r.diff.tools_changed and r.diff.baseline_tools is not None:
            lines += ["", "```diff"]
            lines += [
                f"{m} {t}" for m, t in sequence_diff(r.diff.baseline_tools, r.diff.actual_tools)
            ]
            lines.append("```")
    return "\n".join(lines) + "\n"


def render_trace(trace: Trace, console: Console | None = None) -> None:
    console = console or Console()
    console.print(
        f"[bold]{trace.name}[/bold] {trace.id} · {fmt_ms(trace.latency_ms)}"
        f" · {fmt_cost(trace.total_cost_usd)} · {len(trace.steps)} steps"
    )
    for step in trace.steps:
        if step.type == "llm":
            calls = ", ".join(tc.name for tc in step.tool_calls)
            detail = f"→ calls {calls}" if calls else str(step.output or "")[:80]
            console.print(
                f"  {step.index:>2} [cyan]llm [/cyan] {step.model} "
                f"({step.input_tokens}+{step.output_tokens} tok, {fmt_ms(step.latency_ms)}) "
                f"{detail}",
                highlight=False,
            )
        else:
            status = f"[red]error: {step.error}[/red]" if step.error else str(step.result)[:80]
            console.print(
                f"  {step.index:>2} [magenta]tool[/magenta] {step.name}({step.args}) → {status}",
                highlight=False,
            )
    if trace.error:
        console.print(f"  [red]error:[/red] {trace.error}")
