"""The ``agentrecheck`` command line interface."""

from __future__ import annotations

import json
import os
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from . import __version__, storage
from .client import CloudClient, CloudError
from .config import CONFIG_TEMPLATE, DEFAULT_CONFIG_NAME, load_config
from .judge import JudgeError, judge_from_env
from .report import fmt_cost, fmt_ms, render_markdown, render_run, render_trace
from .runner import EntrypointError, resolve_entrypoint, run_cases
from .snapshot import snapshot_trace

app = typer.Typer(
    help="CI/CD for AI agents: record runs, snapshot them into tests, catch regressions.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()
err = Console(stderr=True)


def _die(message: str, code: int = 2) -> typer.Exit:
    err.print(f"[red]error:[/red] {message}")
    return typer.Exit(code)


@app.command()
def version() -> None:
    """Print the installed version."""
    console.print(__version__)


@app.command()
def init(
    entrypoint: str = typer.Option("agent:run_agent", help="module:function to test."),
    project: str = typer.Option("my-agent", help="Project name."),
) -> None:
    """Create agentrecheck.yaml and the cases directory."""
    path = Path(DEFAULT_CONFIG_NAME)
    if path.exists():
        raise _die(f"{path} already exists.")
    path.write_text(CONFIG_TEMPLATE.format(project=project, entrypoint=entrypoint))
    Path("agentrecheck_cases").mkdir(exist_ok=True)
    console.print(f"Created [bold]{path}[/bold] and [bold]agentrecheck_cases/[/bold]")
    console.print("Next: run your agent once, then `agentrecheck snapshot latest`.")


@app.command()
def traces(limit: int = typer.Option(20, help="How many traces to show.")) -> None:
    """List locally recorded traces, newest first."""
    items = storage.list_traces()[:limit]
    if not items:
        console.print(f"No traces in {storage.traces_dir()}. Run your @trace-decorated agent.")
        return
    table = Table()
    for column in ("ID", "Name", "Started", "Steps", "Tools", "Cost", "Latency"):
        table.add_column(column)
    for t in items:
        table.add_row(
            t.id,
            t.name,
            t.started_at[:19].replace("T", " "),
            str(len(t.steps)),
            " → ".join(t.tool_sequence) or "-",
            fmt_cost(t.total_cost_usd),
            fmt_ms(t.latency_ms),
        )
    console.print(table)


@app.command()
def show(trace_id: str = typer.Argument(..., help="Trace id, prefix, or 'latest'.")) -> None:
    """Print the step-by-step timeline of a trace."""
    try:
        render_trace(storage.load_trace(trace_id), console)
    except storage.NotFoundError as exc:
        raise _die(str(exc)) from exc


@app.command()
def snapshot(
    trace_id: str = typer.Argument(..., help="Trace id, prefix, or 'latest'."),
    case_id: str | None = typer.Option(None, "--id", help="Case id (also the file name)."),
    name: str | None = typer.Option(None, help="Human-readable case name."),
    mode: str = typer.Option("exact", help="Tool sequence mode: exact or subset."),
    config: Path = typer.Option(Path(DEFAULT_CONFIG_NAME), help="Config file."),
    force: bool = typer.Option(False, help="Overwrite an existing case."),
) -> None:
    """Turn a recorded trace into a test case."""
    if mode not in ("exact", "subset"):
        raise _die("--mode must be 'exact' or 'subset'.")
    try:
        trace = storage.load_trace(trace_id)
    except storage.NotFoundError as exc:
        raise _die(str(exc)) from exc
    cfg = load_config(config)
    case = snapshot_trace(trace, case_id=case_id, name=name, mode=mode)  # type: ignore[arg-type]
    target = cfg.cases_path / f"{case.id}.yaml"
    if target.exists() and not force:
        raise _die(f"{target} already exists. Use --force to overwrite.")
    path = storage.save_case(case, cfg.cases_path)
    console.print(f"Wrote [bold]{path}[/bold]")
    console.print(f"  tools:  {' → '.join(case.baseline.tool_sequence) or '(none)'}")  # type: ignore[union-attr]
    console.print("Edit the file to add output checks, then run `agentrecheck run`.")


@app.command()
def run(
    config: Path = typer.Option(Path(DEFAULT_CONFIG_NAME), help="Config file."),
    case: list[str] | None = typer.Option(None, "--case", "-c", help="Only run these case ids."),
    entrypoint: str | None = typer.Option(None, help="Override the entrypoint (module:function)."),
    upload: bool = typer.Option(True, "--upload/--no-upload", help="Upload results if configured."),
    json_out: Path | None = typer.Option(None, help="Write the full result as JSON."),
    markdown_out: Path | None = typer.Option(None, help="Write a markdown summary."),
) -> None:
    """Replay every test case against the current agent and compare to baseline."""
    cfg = load_config(config)
    spec = entrypoint or cfg.entrypoint
    if not spec:
        raise _die(f"No entrypoint. Set `entrypoint` in {config} or pass --entrypoint.")

    cases = storage.load_cases(cfg.cases_path)
    if case:
        wanted = set(case)
        cases = [c for c in cases if c.id in wanted]
    if not cases:
        raise _die(f"No test cases found in {cfg.cases_path}.")

    try:
        fn = resolve_entrypoint(spec, cfg.root)
        judge = judge_from_env(cfg.judge_model)
    except (EntrypointError, JudgeError) as exc:
        raise _die(str(exc)) from exc

    # Traces produced while replaying belong to the run, not the local trace log.
    result = run_cases(cases, fn, config=cfg, judge=judge)
    render_run(result, console)
    storage.save_run(result)

    if json_out:
        json_out.write_text(json.dumps(result.to_payload(), indent=2, default=str))
    markdown = render_markdown(result)
    if markdown_out:
        markdown_out.write_text(markdown)
    summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_file:
        with open(summary_file, "a") as handle:
            handle.write(markdown)

    client = CloudClient.from_env() if upload else None
    if client is not None:
        try:
            response = client.upload_run(result)
            console.print(f"Uploaded run → {response.get('url', client.api_url)}")
        except CloudError as exc:
            err.print(f"[yellow]warning:[/yellow] upload failed: {exc}")

    raise typer.Exit(1 if result.failed else 0)


@app.command(name="upload")
def upload_traces(
    trace_id: str = typer.Argument("latest", help="Trace id, prefix, 'latest' or 'all'."),
) -> None:
    """Upload locally recorded traces to the dashboard."""
    client = CloudClient.from_env()
    if client is None:
        raise _die("Set AGENTRECHECK_API_KEY and AGENTRECHECK_API_URL to upload.")
    try:
        items = storage.list_traces() if trace_id == "all" else [storage.load_trace(trace_id)]
    except storage.NotFoundError as exc:
        raise _die(str(exc)) from exc
    try:
        for trace in items:
            client.upload_trace(trace)
    except CloudError as exc:
        raise _die(str(exc), code=1) from exc
    console.print(f"Uploaded {len(items)} trace(s) to {client.api_url}")


if __name__ == "__main__":
    app()
