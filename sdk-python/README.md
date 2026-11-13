# agentrecheck

**CI/CD for AI agents.** Record your agent's runs, snapshot them into test cases, and replay them
on every pull request. If a prompt, model, or tool change makes the agent worse, the build fails.

```bash
pip install agentrecheck
```

```python
from openai import OpenAI
from agentrecheck import trace, tool, wrap_openai

client = wrap_openai(OpenAI())     # records every LLM call

@tool                              # records every tool call
def lookup_order(order_id: str) -> dict:
    ...

@trace                             # records the whole run
def run_agent(message: str) -> str:
    ...
```

```bash
agentrecheck init --entrypoint agent:run_agent
python agent.py "Where is my order A1002?"
agentrecheck snapshot latest --id order_status   # trace -> YAML test case
agentrecheck run                                 # replay, diff vs baseline, exit 1 on regression
```

Assertions are plain YAML: tool sequence (exact or ordered subset), tool arguments (exact, regex,
JSON Schema), final output (contains, regex, optional LLM-as-judge on your own key), and budgets
for cost, latency, and steps.

- Works with the OpenAI and Anthropic SDKs, plus manual `record_llm_call` / `record_tool_call`.
- Runs entirely locally. Uploading to a dashboard is optional.
- Python 3.11+. MIT licensed.

Full documentation, the example agent, and the dashboard live in the project repository.

## Optional extras

```bash
pip install "agentrecheck[openai]"      # LLM-as-judge with OpenAI
pip install "agentrecheck[anthropic]"   # LLM-as-judge with Anthropic
```

## Development

```bash
uv venv --python 3.11 && uv pip install -e ".[dev]"
.venv/bin/pytest --cov=agentrecheck
.venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/mypy
```
