"""AgentRecheck as an MCP server.

Start it with ``agentrecheck mcp`` and add it to any MCP host (goose, Claude
Code, Cursor, VS Code). The coding agent can then list test cases, inspect
recorded traces, snapshot a trace into a case, and replay the whole suite after
it edits a prompt or a tool, without leaving the chat.

Needs the optional dependency: ``pip install "agentrecheck[mcp]"``.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Literal

from . import storage
from .config import DEFAULT_CONFIG_NAME, load_config
from .snapshot import snapshot_trace as build_case

INSTRUCTIONS = """\
AgentRecheck is a regression test suite for a tool-calling AI agent in this project.

Call run_cases after you change the agent's prompt, model, tools, or control flow, and
before you tell the user the change is done. A failed case means the agent now calls
different tools, gives a worse answer, or costs more than its recorded baseline. Read
the failed checks, fix the agent, and run again. Never edit a case file just to make
it pass unless the user says the new behavior is intended.
"""

RUN_TIMEOUT_SECONDS = 600


def _server_class() -> Any:
    try:
        from mcp.server.mcpserver import MCPServer  # mcp 2.x

        return MCPServer
    except ImportError:
        pass
    try:
        from mcp.server.fastmcp import FastMCP  # type: ignore[attr-defined]  # mcp 1.x

        return FastMCP
    except ImportError as exc:
        raise RuntimeError(
            'The MCP server needs the "mcp" package. Install it with: '
            'pip install "agentrecheck[mcp]"'
        ) from exc


class Project:
    """One AgentRecheck project on disk: its config, its cases, its traces."""

    def __init__(self, project_dir: Path | str = ".") -> None:
        self.root = Path(project_dir).expanduser().resolve()

    @property
    def config_path(self) -> Path:
        return self.root / DEFAULT_CONFIG_NAME

    @property
    def store(self) -> Path:
        """Trace and run storage. A relative AGENTRECHECK_DIR resolves against the project."""
        custom = Path(os.environ.get("AGENTRECHECK_DIR", storage.DEFAULT_DIR))
        return custom if custom.is_absolute() else self.root / custom

    # ------------------------------------------------------------------ read

    def list_cases(self) -> dict[str, Any]:
        cfg = load_config(self.config_path)
        cases = storage.load_cases(cfg.cases_path)
        return {
            "project": cfg.project,
            "entrypoint": cfg.entrypoint,
            "cases_dir": str(cfg.cases_path),
            "cases": [
                {
                    "id": c.id,
                    "name": c.name or c.id,
                    "input": c.input.model_dump(mode="json"),
                    "expected_tools": (
                        c.assertions.tools.sequence
                        if c.assertions.tools and c.assertions.tools.sequence is not None
                        else (c.baseline.tool_sequence if c.baseline else None)
                    ),
                    "tool_mode": c.assertions.tools.mode if c.assertions.tools else None,
                }
                for c in cases
            ],
        }

    def list_traces(self, limit: int = 10) -> dict[str, Any]:
        traces = storage.list_traces(self.store)[: max(1, limit)]
        return {
            "traces": [
                {
                    "id": t.id,
                    "name": t.name,
                    "started_at": t.started_at,
                    "steps": len(t.steps),
                    "tool_sequence": t.tool_sequence,
                    "cost_usd": t.total_cost_usd,
                    "latency_ms": t.latency_ms,
                    "error": t.error,
                }
                for t in traces
            ]
        }

    def show_trace(self, trace_id: str = "latest") -> dict[str, Any]:
        try:
            return storage.load_trace(trace_id, self.store).to_payload()
        except storage.NotFoundError as exc:
            return {"error": str(exc)}

    # ----------------------------------------------------------------- write

    def snapshot(
        self,
        trace_id: str = "latest",
        case_id: str | None = None,
        name: str | None = None,
        mode: Literal["exact", "subset"] = "exact",
        force: bool = False,
    ) -> dict[str, Any]:
        try:
            trace = storage.load_trace(trace_id, self.store)
        except storage.NotFoundError as exc:
            return {"error": str(exc)}
        cfg = load_config(self.config_path)
        case = build_case(trace, case_id=case_id, name=name, mode=mode)
        target = cfg.cases_path / f"{case.id}.yaml"
        if target.exists() and not force:
            return {"error": f"{target} already exists. Pass force=true to overwrite."}
        path = storage.save_case(case, cfg.cases_path)
        return {
            "case_id": case.id,
            "path": str(path),
            "tool_sequence": case.baseline.tool_sequence if case.baseline else [],
            "next": "Edit the file to add output checks, then call run_cases.",
        }

    def run_cases(
        self, case_ids: list[str] | None = None, timeout_seconds: int = RUN_TIMEOUT_SECONDS
    ) -> dict[str, Any]:
        """Replay the suite in a fresh process so edited agent code is always re-imported."""
        if not self.config_path.exists():
            return {"error": f"No {DEFAULT_CONFIG_NAME} in {self.root}. Run `agentrecheck init`."}
        with tempfile.TemporaryDirectory() as tmp:
            json_out = Path(tmp) / "result.json"
            md_out = Path(tmp) / "result.md"
            cmd = [sys.executable, "-m", "agentrecheck.cli", "run", "--no-upload"]
            cmd += ["--config", str(self.config_path)]
            cmd += ["--json-out", str(json_out), "--markdown-out", str(md_out)]
            for case_id in case_ids or []:
                cmd += ["--case", case_id]
            env = {**os.environ, "AGENTRECHECK_DIR": str(self.store), "COLUMNS": "200"}
            env.pop("GITHUB_STEP_SUMMARY", None)
            try:
                proc = subprocess.run(
                    cmd,
                    cwd=self.root,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                    stdin=subprocess.DEVNULL,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                return {"error": f"Run timed out after {timeout_seconds}s."}
            if not json_out.exists():
                detail = (proc.stderr or proc.stdout).strip()[-2000:]
                return {"error": detail or "Run failed.", "exit_code": proc.returncode}
            payload = json.loads(json_out.read_text())
            markdown = md_out.read_text() if md_out.exists() else ""
        return {
            "ok": proc.returncode == 0,
            "exit_code": proc.returncode,
            **{k: payload["summary"][k] for k in ("total", "passed", "failed")},
            "cases": [_case_summary(r) for r in payload["results"]],
            "report_markdown": markdown,
        }


def _case_summary(result: dict[str, Any]) -> dict[str, Any]:
    diff = result.get("diff") or {}
    item: dict[str, Any] = {"id": result["case_id"], "status": result["status"]}
    if result.get("error"):
        item["error"] = result["error"]
    failed = [c for c in result.get("checks", []) if c["status"] == "fail"]
    if failed:
        item["failed_checks"] = [{"check": c["name"], "message": c["message"]} for c in failed]
    if diff.get("tools_changed"):
        item["expected_tools"] = diff.get("baseline_tools")
        item["actual_tools"] = diff.get("actual_tools")
    return item


def build_server(project_dir: Path | str = ".") -> Any:
    """Create the MCP server for the AgentRecheck project in ``project_dir``."""
    project = Project(project_dir)
    server = _server_class()("agentrecheck", instructions=INSTRUCTIONS)

    @server.tool()
    def list_cases() -> dict[str, Any]:
        """List the regression test cases: id, input, and the tools each expects."""
        return project.list_cases()

    @server.tool()
    def list_traces(limit: int = 10) -> dict[str, Any]:
        """List recently recorded agent runs (traces), newest first."""
        return project.list_traces(limit)

    @server.tool()
    def show_trace(trace_id: str = "latest") -> dict[str, Any]:
        """Show one recorded run step by step: every LLM call and tool call.

        trace_id is a trace id, a unique prefix of one, or "latest".
        """
        return project.show_trace(trace_id)

    @server.tool()
    def snapshot_trace(
        trace_id: str = "latest",
        case_id: str | None = None,
        name: str | None = None,
        mode: Literal["exact", "subset"] = "exact",
        force: bool = False,
    ) -> dict[str, Any]:
        """Turn a recorded run into a test case file that pins its tool sequence.

        Use mode="subset" when extra tool calls are acceptable as long as the
        recorded ones still happen in order.
        """
        return project.snapshot(trace_id, case_id, name, mode, force)

    @server.tool()
    async def run_cases(case_ids: list[str] | None = None) -> dict[str, Any]:
        """Replay the test cases against the current agent code and compare to baseline.

        Call this after changing the agent's prompt, model, or tools. Returns
        pass/fail per case, the failed checks, and the tool-sequence diff.
        Omit case_ids to run every case.
        """
        import anyio

        return await anyio.to_thread.run_sync(project.run_cases, case_ids)

    return server


def serve(project_dir: Path | str = ".") -> None:
    """Run the server over stdio (blocks until the host disconnects)."""
    build_server(project_dir).run()
