# Example: MCP agent

The same support agent as [`support_agent/`](../support_agent), except its three tools
(`lookup_order`, `issue_refund`, `search_kb`) live in an **MCP server** (`server.py`).
The agent starts the server as a subprocess, discovers the tools over the Model Context
Protocol, and calls them with `mcp.Client`.

One line makes those calls testable:

```python
async with Client(SERVER) as mcp:
    wrap_mcp(mcp)   # every mcp.call_tool() is now recorded as a tool step
```

It runs **offline by default**: without `OPENAI_API_KEY` the agent uses a deterministic
stand-in for the model (`mock_llm.py`). The MCP server is real either way.

```bash
pip install -r requirements.txt        # or: pip install -e "../../sdk-python[mcp]"
python agent.py "Where is my order A1002?"
agentrecheck traces                     # the run you just recorded, with its MCP tool calls
agentrecheck run                        # 4/4 pass
```

## See a regression get caught

`prompts/v2.txt` is a "simplified" system prompt that drops the rule to look an order up
before refunding it.

```bash
SUPPORT_AGENT_PROMPT=v2 agentrecheck run
```

```
✗ refund_outside_window  Refund request outside the 30-day window
  ✗ tools.sequence (exact): expected ['lookup_order'], got ['issue_refund']
  ✗ output.contains['30-day']: not found in output
  ✗ output.not_contains['has been issued']: found in output
  tool sequence (baseline → current):
    - lookup_order
    + issue_refund

3/4 passed · 1 regression(s) detected.        (exit code 1)
```

The agent refunded a 92-day-old order over MCP without checking it.

## Let your coding agent run the tests

AgentRecheck is also an MCP server. Point goose, Claude Code, or Cursor at it and the coding
agent can replay this suite itself after it edits the prompt. See [docs/mcp.md](../../docs/mcp.md).

```bash
agentrecheck mcp --project-dir .
```

## Files

| File | What it is |
| --- | --- |
| `server.py` | MCP server with the three tools |
| `agent.py` | The agent loop: MCP client + `wrap_mcp`, decorated with `@trace` |
| `mock_llm.py` | Offline stand-in for the OpenAI client |
| `prompts/` | `v1.txt` (good) and `v2.txt` (regressed) |
| `agentrecheck.yaml` | Config: entrypoint and thresholds |
| `agentrecheck_cases/` | The four test cases |
