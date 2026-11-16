from __future__ import annotations

import asyncio
import sys
import textwrap
from types import SimpleNamespace as NS

import pytest
from typer.testing import CliRunner

import agentrecheck as ar
from agentrecheck import storage
from agentrecheck.adapters.mcp_adapter import result_to_jsonable
from agentrecheck.mcp_server import Project, build_server

mcp = pytest.importorskip("mcp")


# --------------------------------------------------------------------------- adapter


class FakeMCPClient:
    """Stands in for ``mcp.Client``: an async ``call_tool`` returning a CallToolResult shape."""

    def __init__(self, results: dict):
        self._results = results
        self.calls: list[tuple] = []

    async def call_tool(self, name, arguments=None, read_timeout_seconds=None):
        self.calls.append((name, arguments, read_timeout_seconds))
        item = self._results[name]
        if isinstance(item, Exception):
            raise item
        return item


def text_result(text, is_error=False):
    return NS(content=[NS(type="text", text=text)], structured_content=None, is_error=is_error)


def test_wrap_mcp_records_tool_steps():
    client = ar.wrap_mcp(
        FakeMCPClient(
            {
                "lookup_order": NS(content=[], structured_content={"status": "shipped"}),
                "search_kb": text_result('{"title": "Shipping"}'),
            }
        )
    )

    async def agent():
        with ar.start_trace("t", persist=False) as tr:
            await client.call_tool("lookup_order", {"order_id": "A1"})
            await client.call_tool("search_kb", {"query": "shipping"}, read_timeout_seconds=5)
        return tr

    tr = asyncio.run(agent())
    assert tr.tool_sequence == ["lookup_order", "search_kb"]
    first, second = tr.tool_steps
    assert first.args == {"order_id": "A1"}
    assert first.result == {"status": "shipped"}
    assert second.result == {"title": "Shipping"}  # JSON text is parsed
    assert first.error is None and first.latency_ms >= 0
    assert client.calls[1] == ("search_kb", {"query": "shipping"}, 5)  # extra args pass through


def test_wrap_mcp_records_errors_and_reraises():
    client = ar.wrap_mcp(
        FakeMCPClient(
            {
                "bad": text_result("order not found", is_error=True),
                "boom": RuntimeError("connection closed"),
            }
        )
    )

    async def agent():
        with ar.start_trace("t", persist=False) as tr:
            result = await client.call_tool("bad", {})
            assert result.is_error  # the caller still gets the real result
            with pytest.raises(RuntimeError):
                await client.call_tool("boom")
        return tr

    tr = asyncio.run(agent())
    assert tr.tool_steps[0].error == "MCPToolError: order not found"
    assert tr.tool_steps[1].error == "RuntimeError: connection closed"
    assert tr.tool_steps[1].args == {}


def test_wrap_mcp_prefix_idempotent_and_untraced():
    fake = FakeMCPClient({"lookup": text_result("ok")})
    client = ar.wrap_mcp(fake, prefix="orders.")
    patched = client.call_tool
    assert ar.wrap_mcp(client).call_tool is patched  # second wrap is a no-op

    async def agent():
        await client.call_tool("lookup")  # outside a trace: passthrough, nothing recorded
        with ar.start_trace("t", persist=False) as tr:
            await client.call_tool("lookup")
        return tr

    tr = asyncio.run(agent())
    assert tr.tool_sequence == ["orders.lookup"]
    assert len(fake.calls) == 2


def test_wrap_mcp_rejects_non_clients():
    with pytest.raises(TypeError, match="async call_tool"):
        ar.wrap_mcp(object())
    with pytest.raises(TypeError, match="async call_tool"):
        ar.wrap_mcp(NS(call_tool=lambda name: None))


def test_result_to_jsonable_shapes():
    assert result_to_jsonable(NS(content=[], structuredContent={"a": 1})) == {"a": 1}  # mcp 1.x
    mixed = NS(content=[NS(type="text", text="hello"), NS(type="image", data="...")])
    assert result_to_jsonable(mixed) == "hello\n[image]"
    assert result_to_jsonable("plain") == "plain"


def test_wrap_mcp_with_real_sdk_client():
    """End to end against the real SDK: an in-process server and ``mcp.Client``."""
    server_cls = pytest.importorskip("mcp.server.mcpserver").MCPServer
    server = server_cls("orders")

    @server.tool()
    def lookup_order(order_id: str) -> dict:
        """Look up an order."""
        return {"order_id": order_id, "status": "in transit"}

    @ar.trace
    async def agent(order_id: str) -> str:
        async with mcp.Client(server) as client:
            ar.wrap(client)  # auto-detected as an MCP client
            result = await client.call_tool("lookup_order", {"order_id": order_id})
            return result_to_jsonable(result)["status"]

    assert asyncio.run(agent("A1002")) == "in transit"
    tr = storage.load_trace("latest")
    assert tr.tool_sequence == ["lookup_order"]
    assert tr.tool_steps[0].args == {"order_id": "A1002"}
    assert tr.tool_steps[0].result == {"order_id": "A1002", "status": "in transit"}


# ---------------------------------------------------------------------------- server

AGENT = """
    import os
    import agentrecheck as ar

    @ar.tool
    def lookup(order_id: str) -> dict:
        return {"id": order_id}

    @ar.tool
    def refund(order_id: str) -> str:
        return "refunded"

    @ar.trace
    def run_agent(message: str) -> str:
        ar.record_llm_call(model="gpt-4o-mini", input_tokens=100, output_tokens=10)
        if os.environ.get("SKIP_LOOKUP") != "1":
            lookup("A1")
        refund("A1")
        return "Refund issued."
"""


@pytest.fixture
def project(tmp_path, monkeypatch):
    """A project directory with an agent, a config, and one recorded trace."""
    monkeypatch.delenv("AGENTRECHECK_DIR", raising=False)  # store under the project dir
    (tmp_path / "agent.py").write_text(textwrap.dedent(AGENT))
    (tmp_path / "agentrecheck.yaml").write_text("project: demo\nentrypoint: agent:run_agent\n")
    with ar.start_trace(
        "run_agent", input={"args": ["refund A1"], "kwargs": {}}, persist=False
    ) as t:
        ar.record_llm_call(model="gpt-4o-mini", input_tokens=100, output_tokens=10)
        ar.record_tool_call("lookup", {"order_id": "A1"}, {"id": "A1"})
        ar.record_tool_call("refund", {"order_id": "A1"}, "refunded")
        t.output = "Refund issued."
    proj = Project(tmp_path)
    storage.save_trace(t, proj.store)
    return proj


def test_project_read_tools(project):
    listed = project.list_traces()
    assert [t["tool_sequence"] for t in listed["traces"]] == [["lookup", "refund"]]
    shown = project.show_trace("latest")
    assert shown["tool_sequence"] == ["lookup", "refund"]
    assert "error" in project.show_trace("tr_missing")
    assert project.list_cases()["cases"] == []


def test_project_snapshot_then_run_catches_regression(project, monkeypatch):
    snap = project.snapshot("latest", case_id="refund")
    assert snap["tool_sequence"] == ["lookup", "refund"]
    assert "already exists" in project.snapshot("latest", case_id="refund")["error"]
    assert project.snapshot("latest", case_id="refund", force=True)["case_id"] == "refund"

    cases = project.list_cases()
    assert cases["entrypoint"] == "agent:run_agent"
    assert cases["cases"][0]["expected_tools"] == ["lookup", "refund"]

    good = project.run_cases()
    assert good["ok"] is True and good["passed"] == 1 and good["failed"] == 0
    assert good["cases"] == [{"id": "refund", "status": "pass"}]

    monkeypatch.setenv("SKIP_LOOKUP", "1")  # the agent now skips the lookup
    bad = project.run_cases(["refund"])
    assert bad["ok"] is False and bad["exit_code"] == 1 and bad["failed"] == 1
    case = bad["cases"][0]
    assert case["expected_tools"] == ["lookup", "refund"]
    assert case["actual_tools"] == ["refund"]
    assert any(c["check"].startswith("tools.sequence") for c in case["failed_checks"])
    assert "refund" in bad["report_markdown"]


def test_project_run_reports_config_errors(tmp_path, monkeypatch):
    monkeypatch.delenv("AGENTRECHECK_DIR", raising=False)
    assert "agentrecheck init" in Project(tmp_path).run_cases()["error"]
    (tmp_path / "agentrecheck.yaml").write_text("project: demo\nentrypoint: agent:run_agent\n")
    result = Project(tmp_path).run_cases()
    assert result["exit_code"] == 2 and "No test cases" in result["error"]


def test_server_exposes_tools_over_mcp(project):
    """The same thing an MCP host does: connect, list tools, call them."""
    project.snapshot("latest", case_id="refund")
    server = build_server(project.root)

    async def session():
        async with mcp.Client(server) as client:
            names = sorted(t.name for t in (await client.list_tools()).tools)
            cases = await client.call_tool("list_cases", {})
            run = await client.call_tool("run_cases", {})
            return names, result_to_jsonable(cases), result_to_jsonable(run)

    names, cases, run = asyncio.run(session())
    assert names == ["list_cases", "list_traces", "run_cases", "show_trace", "snapshot_trace"]
    assert cases["cases"][0]["id"] == "refund"
    assert run["ok"] is True and run["passed"] == 1


def test_cli_mcp_command_is_registered():
    from agentrecheck.cli import app

    result = CliRunner().invoke(app, ["mcp", "--help"])
    assert result.exit_code == 0
    assert "MCP server" in result.output


def test_server_needs_mcp_package(monkeypatch):
    from agentrecheck import mcp_server

    monkeypatch.setitem(sys.modules, "mcp.server.mcpserver", None)
    monkeypatch.setitem(sys.modules, "mcp.server.fastmcp", None)
    with pytest.raises(RuntimeError, match=r"agentrecheck\[mcp\]"):
        mcp_server.build_server(".")
