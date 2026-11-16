# AGENTS.md

Instructions for coding agents working in this repository.

## Layout

| Path | What it is |
| --- | --- |
| `sdk-python/` | The `agentrecheck` Python package and CLI. Source in `src/agentrecheck/`, tests in `tests/` |
| `sdk-python/src/agentrecheck/adapters/` | Provider adapters: OpenAI, Anthropic, MCP client |
| `sdk-python/src/agentrecheck/mcp_server.py` | `agentrecheck mcp`, the MCP server |
| `examples/support_agent/` | OpenAI tool-calling agent with 5 cases, offline by default |
| `examples/mcp_agent/` | Same agent, tools behind an MCP server, 4 cases, offline by default |
| `web/` | Next.js landing page, docs, dashboard, REST API |
| `docs/` | Reference docs (also served at `/docs` in the web app) |

## Setup

```bash
cd sdk-python
uv venv --python 3.11
uv pip install -e ".[dev]"
```

## Checks to run before you finish

```bash
cd sdk-python
.venv/bin/pytest                      # all tests must pass
.venv/bin/ruff check src tests
.venv/bin/ruff format --check src tests
.venv/bin/python -m mypy
```

Then make sure both examples still behave:

```bash
cd examples/support_agent && ../../sdk-python/.venv/bin/agentrecheck run   # 5/5, exit 0
SUPPORT_AGENT_PROMPT=v2 ../../sdk-python/.venv/bin/agentrecheck run        # 1 regression, exit 1
cd ../mcp_agent && ../../sdk-python/.venv/bin/agentrecheck run             # 4/4, exit 0
SUPPORT_AGENT_PROMPT=v2 ../../sdk-python/.venv/bin/agentrecheck run        # 1 regression, exit 1
```

For the web app: `cd web && npm run lint && npm run typecheck && npm test && npm run build`.

## Rules

- Instrumentation must never break the user's agent. Recording failures become warnings, never
  exceptions, and wrapped calls must return the original result unchanged.
- Python 3.11+, line length 100, type hints on public functions.
- Tests must not call real model APIs or spend money. Use the fakes in `tests/conftest.py` or an
  in-process MCP server.
- Do not edit a test case YAML just to make it pass. A failing case is the product working.
- Update `CHANGELOG.md` under `[Unreleased]` and the matching file in `docs/` for any user-facing
  change.
