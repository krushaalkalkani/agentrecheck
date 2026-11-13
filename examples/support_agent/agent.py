"""A small OpenAI tool-calling support agent, instrumented with AgentRecheck.

Run it:
    python agent.py "Where is my order A1002?"

With OPENAI_API_KEY set it calls the real API. Without one (or with
SUPPORT_AGENT_MOCK=1) it uses a deterministic offline stand-in, so the example
and its test cases run anywhere, including CI, at zero cost.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from tools import TOOL_SCHEMAS, TOOLS

from agentrecheck import trace, wrap_openai

HERE = Path(__file__).parent
MODEL = os.environ.get("SUPPORT_AGENT_MODEL", "gpt-4o-mini")
MAX_TURNS = 6


def load_prompt() -> str:
    """The system prompt. SUPPORT_AGENT_PROMPT picks the version (v1 or v2)."""
    version = os.environ.get("SUPPORT_AGENT_PROMPT", "v1")
    return (HERE / "prompts" / f"{version}.txt").read_text().strip()


def get_client():
    if os.environ.get("OPENAI_API_KEY") and os.environ.get("SUPPORT_AGENT_MOCK") != "1":
        from openai import OpenAI

        return wrap_openai(OpenAI())
    from mock_llm import MockOpenAI

    return wrap_openai(MockOpenAI())


@trace(name="support_agent")
def run_agent(message: str) -> str:
    client = get_client()
    messages: list[dict] = [
        {"role": "system", "content": load_prompt()},
        {"role": "user", "content": message},
    ]
    for _ in range(MAX_TURNS):
        response = client.chat.completions.create(model=MODEL, messages=messages, tools=TOOL_SCHEMAS)
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
                result = TOOLS[call.function.name](**json.loads(call.function.arguments))
            except Exception as exc:  # report tool failures back to the model
                result = {"error": f"{type(exc).__name__}: {exc}"}
            messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result)})
    return "Sorry, I couldn't complete that request."


if __name__ == "__main__":
    print(run_agent(" ".join(sys.argv[1:]) or "Where is my order A1002?"))
