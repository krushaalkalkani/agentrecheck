# MCP

AgentRecheck works with the [Model Context Protocol](https://modelcontextprotocol.io) in two
directions:

| | What it does |
| --- | --- |
| `wrap_mcp(client)` | Records every tool call your agent makes **through an MCP client**, so you can test agents whose tools live in MCP servers |
| `agentrecheck mcp` | Runs AgentRecheck **as an MCP server**, so a coding agent (goose, Claude Code, Cursor) can replay your tests after it edits your agent |

Install the extra: `pip install "agentrecheck[mcp]"`. Both mcp 1.x and 2.x are supported.

## Testing an agent that uses MCP tools

```python
from mcp import Client, StdioServerParameters
from agentrecheck import trace, wrap_mcp

SERVER = StdioServerParameters(command="python", args=["server.py"])

@trace
async def run_agent(message: str) -> str:
    async with Client(SERVER) as mcp:
        wrap_mcp(mcp)
        ...  # your loop: list_tools(), ask the model, mcp.call_tool(name, args)
```

Each `call_tool` becomes a tool step with its name, arguments, result, latency, and error. Tool
results are stored as structured content when the server returns it, otherwise as the text
content (parsed as JSON when possible). A result with `isError: true` is recorded as an error.

From there everything works as for `@tool` functions: `agentrecheck snapshot latest`, tool
sequence and argument assertions, `agentrecheck run`.

| Option | |
| --- | --- |
| `wrap_mcp(client, prefix="orders.")` | Record `lookup` as `orders.lookup`. Use it when the agent talks to several servers with overlapping tool names |
| `wrap(client)` | Auto-detects `mcp.Client` and `mcp.ClientSession` |

Any object with an async `call_tool(name, arguments)` method can be wrapped. Async `@trace`
entrypoints are supported by `agentrecheck run`.

Full working example: [`examples/mcp_agent`](../examples/mcp_agent).

## AgentRecheck as an MCP server

```bash
agentrecheck mcp --project-dir path/to/your/agent
```

It speaks MCP over stdio and exposes five tools:

| Tool | What it does |
| --- | --- |
| `list_cases` | The test cases: id, input, expected tools |
| `list_traces` | Recent recorded runs, newest first |
| `show_trace` | One run, step by step |
| `snapshot_trace` | Turn a run into a test case |
| `run_cases` | Replay the suite and return pass/fail, failed checks, and tool-sequence diffs |

The server also sends instructions telling the coding agent to call `run_cases` after it changes
the agent's prompt, model, or tools, and not to edit a case just to make it pass.

`run_cases` runs the suite in a fresh process, so it always tests the code as it is on disk.

### goose

Add it as a command-line extension (`goose configure` → Add Extension → Command-line Extension)
with the command:

```
agentrecheck mcp --project-dir /absolute/path/to/your/agent
```

Or for a single session:

```bash
goose session --with-extension "agentrecheck mcp --project-dir /absolute/path/to/your/agent"
```

### Claude Code

```bash
claude mcp add agentrecheck -- agentrecheck mcp --project-dir /absolute/path/to/your/agent
```

### Cursor, VS Code, and other hosts

```json
{
  "mcpServers": {
    "agentrecheck": {
      "command": "agentrecheck",
      "args": ["mcp", "--project-dir", "/absolute/path/to/your/agent"]
    }
  }
}
```

If `agentrecheck` is inside a virtualenv, use the full path to that environment's
`agentrecheck` binary as the command.
