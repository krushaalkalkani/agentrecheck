from __future__ import annotations

import json
import sys
import textwrap

import httpx
import pytest
from rich.console import Console
from typer.testing import CliRunner

import agentrecheck as ar
from agentrecheck import storage
from agentrecheck.cli import app
from agentrecheck.config import Config, RegressionConfig, load_config
from agentrecheck.models import Case
from agentrecheck.report import fmt_delta, fmt_ms, render_markdown, render_run, sequence_diff
from agentrecheck.runner import EntrypointError, resolve_entrypoint, run_case, run_cases

runner = CliRunner()


@ar.tool
def lookup(order_id: str) -> dict:
    return {"id": order_id, "status": "shipped"}


@ar.tool
def refund(order_id: str) -> str:
    return "refunded"


def good_agent(message: str) -> str:
    ar.record_llm_call(model="gpt-4o-mini", input_tokens=1000, output_tokens=100)
    lookup("A1")
    refund("A1")
    return "Refund issued for A1."


def regressed_agent(message: str) -> str:
    # Skips the lookup and burns far more tokens.
    ar.record_llm_call(model="gpt-4o-mini", input_tokens=9000, output_tokens=900)
    refund("A1")
    return "Done."


def make_case() -> Case:
    return Case.model_validate(
        {
            "id": "refund",
            "name": "Refund flow",
            "input": {"args": ["refund A1"]},
            "baseline": {
                "tool_sequence": ["lookup", "refund"],
                "cost_usd": 0.00021,
                "latency_ms": 1.0,
                "steps": 3,
            },
            "assertions": {
                "tools": {"sequence": ["lookup", "refund"]},
                "output": {"contains": ["refund issued"]},
            },
        }
    )


def test_run_case_pass():
    result = run_case(make_case(), good_agent)
    assert result.status == "pass"
    assert result.diff.tools_changed is False
    assert result.diff.cost_delta == pytest.approx(0.0)
    assert result.trace.output == "Refund issued for A1."
    assert storage.list_traces() == []  # replays are not written to the trace log


def test_run_case_detects_regression():
    result = run_case(make_case(), regressed_agent)
    assert result.status == "fail"
    failed = {c.name for c in result.failed_checks}
    assert failed == {"tools.sequence (exact)", "output.contains['refund issued']", "baseline.cost"}
    assert result.diff.tools_changed and result.diff.actual_tools == ["refund"]
    assert result.diff.cost_delta > 0 and result.diff.latency_delta is not None


def test_run_case_latency_regression_and_agent_error():
    cfg = RegressionConfig(max_cost_increase_pct=None, max_latency_increase_pct=0.0)
    case = make_case()
    case.baseline.latency_ms = 0.000001
    result = run_case(case, good_agent, regression=cfg)
    assert [c.name for c in result.failed_checks] == ["baseline.latency"]

    def crashing(message):
        raise KeyError("boom")

    crashed = run_case(make_case(), crashing)
    assert crashed.status == "error" and "KeyError" in crashed.error


def test_run_case_async_agent_and_no_baseline():
    async def agent(message: str) -> str:
        lookup("A1")
        return "ok"

    case = Case(id="plain")
    case.input.args = ["hi"]
    result = run_case(case, agent)
    assert result.status == "pass" and result.trace.tool_sequence == ["lookup"]
    assert result.diff.baseline_tools is None and result.diff.cost_delta is None


def test_run_cases_summary_and_payload():
    run = run_cases([make_case(), make_case()], good_agent, config=Config(project="demo"))
    assert (run.total, run.passed, run.failed) == (2, 2, 0)
    payload = run.to_payload()
    assert payload["summary"]["total_cost_usd"] == pytest.approx(0.00042)
    assert payload["results"][0]["trace"]["tool_sequence"] == ["lookup", "refund"]
    assert payload["project"] == "demo"


def test_resolve_entrypoint_errors(tmp_path):
    with pytest.raises(EntrypointError, match="module:function"):
        resolve_entrypoint("nocolon")
    with pytest.raises(EntrypointError, match="Could not import"):
        resolve_entrypoint("definitely_missing_mod:fn", tmp_path)
    (tmp_path / "emptymod_arc.py").write_text("x = 1\n")
    with pytest.raises(EntrypointError, match="no callable"):
        resolve_entrypoint("emptymod_arc:fn", tmp_path)


def test_report_helpers_and_rendering():
    assert sequence_diff(["a", "b", "c"], ["a", "c", "d"]) == [
        (" ", "a"),
        ("-", "b"),
        (" ", "c"),
        ("+", "d"),
    ]
    assert fmt_ms(1500) == "1.50s" and fmt_ms(20) == "20ms"
    assert fmt_delta(0.002, 0.001, "cost") == "+$0.00100 (+100%)"
    assert fmt_delta(5, 0, "latency") == "+5ms" and fmt_delta(1, None, "cost") == ""

    run = run_cases([make_case()], regressed_agent)
    console = Console(record=True, width=200)
    render_run(run, console)
    text = console.export_text()
    assert "FAIL" in text and "- lookup" in text and "1 regression(s) detected" in text
    md = render_markdown(run)
    assert "0/1 passed" in md and "```diff" in md and "- lookup" in md


AGENT_SOURCE = textwrap.dedent(
    """
    import os
    import agentrecheck as ar

    @ar.tool
    def lookup(order_id):
        return {"id": order_id}

    @ar.tool
    def refund(order_id):
        return "ok"

    @ar.trace
    def run_agent(message):
        ar.record_llm_call(model="gpt-4o-mini", input_tokens=1000, output_tokens=100)
        if os.environ.get("BREAK") != "1":
            lookup("A1")
        refund("A1")
        return "Refund issued."
    """
)


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "cli_agent_mod.py").write_text(AGENT_SOURCE)
    sys.modules.pop("cli_agent_mod", None)
    yield tmp_path
    sys.modules.pop("cli_agent_mod", None)
    if str(tmp_path) in sys.path:
        sys.path.remove(str(tmp_path))


def test_cli_full_workflow(project, monkeypatch):
    assert runner.invoke(app, ["version"]).output.strip() == ar.__version__

    result = runner.invoke(app, ["init", "--entrypoint", "cli_agent_mod:run_agent"])
    assert result.exit_code == 0 and (project / "agentrecheck.yaml").exists()
    assert runner.invoke(app, ["init"]).exit_code == 2  # already exists
    assert load_config().entrypoint == "cli_agent_mod:run_agent"

    assert "No traces" in runner.invoke(app, ["traces"]).output
    assert runner.invoke(app, ["snapshot", "latest"]).exit_code == 2
    assert runner.invoke(app, ["run"]).exit_code == 2  # no cases yet

    fn = resolve_entrypoint("cli_agent_mod:run_agent", project)
    fn("refund A1")
    assert "lookup → refund" in runner.invoke(app, ["traces"]).output
    assert "tool" in runner.invoke(app, ["show", "latest"]).output
    assert runner.invoke(app, ["show", "nope"]).exit_code == 2

    snap = runner.invoke(app, ["snapshot", "latest", "--id", "refund", "--name", "Refund"])
    assert snap.exit_code == 0, snap.output
    assert (project / "agentrecheck_cases" / "refund.yaml").exists()
    assert runner.invoke(app, ["snapshot", "latest", "--id", "refund"]).exit_code == 2
    assert runner.invoke(app, ["snapshot", "latest", "--id", "refund", "--force"]).exit_code == 0
    assert runner.invoke(app, ["snapshot", "latest", "--mode", "fuzzy"]).exit_code == 2

    summary = project / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    ok = runner.invoke(app, ["run", "--json-out", "out.json", "--markdown-out", "out.md"])
    assert ok.exit_code == 0, ok.output
    assert "1/1 passed" in ok.output
    assert json.loads((project / "out.json").read_text())["summary"]["passed"] == 1
    assert "1/1 passed" in summary.read_text() and (project / "out.md").exists()

    monkeypatch.setenv("BREAK", "1")
    broken = runner.invoke(app, ["run"])
    assert broken.exit_code == 1
    assert "regression(s) detected" in broken.output and "- lookup" in broken.output

    assert runner.invoke(app, ["run", "--case", "missing"]).exit_code == 2
    assert runner.invoke(app, ["run", "--entrypoint", "bad"]).exit_code == 2


def test_cli_run_requires_entrypoint(project):
    assert runner.invoke(app, ["run"]).exit_code == 2


def test_cli_upload(project, monkeypatch):
    assert runner.invoke(app, ["upload"]).exit_code == 2  # not configured

    uploaded = []
    real_client = httpx.Client

    def handler(request):
        uploaded.append(request.url.path)
        return httpx.Response(200, json={"ids": [], "url": "http://dash/runs/1"})

    def fake_client(**kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client(**kwargs)

    monkeypatch.setattr(httpx, "Client", fake_client)
    monkeypatch.setenv("AGENTRECHECK_API_KEY", "ark_test")
    monkeypatch.setenv("AGENTRECHECK_API_URL", "http://dash")

    assert runner.invoke(app, ["upload"]).exit_code == 2  # nothing recorded yet
    runner.invoke(app, ["init", "--entrypoint", "cli_agent_mod:run_agent"])
    resolve_entrypoint("cli_agent_mod:run_agent", project)("hi")  # auto-uploads on finish
    assert uploaded == ["/api/traces"]
    assert "Uploaded 1 trace(s)" in runner.invoke(app, ["upload", "all"]).output

    runner.invoke(app, ["snapshot", "latest", "--id", "c1"])
    out = runner.invoke(app, ["run"])
    assert out.exit_code == 0 and "Uploaded run → http://dash/runs/1" in out.output
    assert uploaded[-1] == "/api/runs"
    runner.invoke(app, ["run", "--no-upload"])
    assert uploaded.count("/api/runs") == 1
