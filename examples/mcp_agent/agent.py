"""A support agent whose tools live behind an MCP server, tested with AgentRecheck.

Run it:
    python agent.py "Where is my order A1002?"

The agent starts server.py as a subprocess, discovers its tools over MCP, and
lets the model call them. ``wrap_mcp`` records every MCP tool call on the
trace, so AgentRecheck can pin the tool sequence and catch regressions.

With OPENAI_API_KEY set it calls the real API. Without one (or with
SUPPORT_AGENT_MOCK=1) it uses a deterministic offline stand-in, so the example
and its test cases run anywhere, including CI, at zero cost.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import Client, StdioServerParameters

from agentrecheck import trace, wrap_mcp, wrap_openai
from agentrecheck.adapters.mcp_adapter import result_to_jsonable

HERE = Path(__file__).parent
MODEL = os.environ.get("SUPPORT_AGENT_MODEL", "gpt-4o-mini")
MAX_TURNS = 6

SERVER = StdioServerParameters(command=sys.executable, args=[str(HERE / "server.py")])


def load_prompt() -> str:
    """The system prompt. SUPPORT_AGENT_PROMPT picks the version (v1 or v2)."""
    version = os.environ.get("SUPPORT_AGENT_PROMPT", "v1")
    return (HERE / "prompts" / f"{version}.txt").read_text().strip()


def get_llm():
    if os.environ.get("OPENAI_API_KEY") and os.environ.get("SUPPORT_AGENT_MOCK") != "1":
        from openai import OpenAI

        return wrap_openai(OpenAI())
    from mock_llm import MockOpenAI

    return wrap_openai(MockOpenAI())


def to_openai_tools(mcp_tools: list) -> list[dict]:
    """MCP tool definitions -> the OpenAI function-calling format."""
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.input_schema,
            },
        }
        for tool in mcp_tools
    ]


@trace(name="mcp_support_agent")
async def run_agent(message: str) -> str:
    llm = get_llm()
    async with Client(SERVER) as mcp:
        wrap_mcp(mcp)  # every mcp.call_tool() below is now recorded as a tool step
        tools = to_openai_tools((await mcp.list_tools()).tools)

        messages: list[dict] = [
            {"role": "system", "content": load_prompt()},
            {"role": "user", "content": message},
        ]
        for _ in range(MAX_TURNS):
            response = llm.chat.completions.create(model=MODEL, messages=messages, tools=tools)
            reply = response.choices[0].message
            if not reply.tool_calls:
                return reply.content or ""

            messages.append(
                {
                    "role": "assistant",
                    "content": reply.content,
                    "tool_calls": [
                        {
                            "id": call.id,
                            "type": "function",
                            "function": {"name": call.function.name, "arguments": call.function.arguments},
                        }
                        for call in reply.tool_calls
                    ],
                }
            )
            for call in reply.tool_calls:
                try:
                    result = await mcp.call_tool(call.function.name, json.loads(call.function.arguments))
                    content = result_to_jsonable(result)
                except Exception as exc:  # report tool failures back to the model
                    content = {"error": f"{type(exc).__name__}: {exc}"}
                messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(content)})
    return "Sorry, I couldn't complete that request."


if __name__ == "__main__":
    print(asyncio.run(run_agent(" ".join(sys.argv[1:]) or "Where is my order A1002?")))
