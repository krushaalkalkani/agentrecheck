# Quickstart and concepts

AgentRecheck has three ideas: **traces**, **cases**, and **runs**.

- A **trace** is a recording of one agent run: input, every LLM call, every tool call, final output.
- A **case** is a trace turned into a test: the input to replay, a baseline, and assertions.
- A **run** replays every case against your current code and compares each one to its baseline.

## 1. Install

```bash
pip install agentrecheck
```

Python 3.11 or newer.

## 2. Record traces

```python
from openai import OpenAI
from agentrecheck import trace, tool, wrap_openai

client = wrap_openai(OpenAI())

@tool
def lookup_order(order_id: str) -> dict:
    return {"order_id": order_id, "status": "in transit"}

@trace
def run_agent(message: str) -> str:
    response = client.chat.completions.create(model="gpt-4o-mini", messages=[...], tools=[...])
    ...
```

Each call to `run_agent` writes `.agentrecheck/traces/<trace_id>.json`. Add `.agentrecheck/` to
your `.gitignore`.

### Recording API

| API | Use |
| --- | --- |
| `@trace`, `@trace(name="...", metadata={...})` | Record each call of a sync or async function |
| `with start_trace("name", input=...) as tr:` | Context-manager form; set `tr.output` yourself |
| `@tool`, `@tool(name="...")` | Record a function call as a tool step |
| `wrap_openai(client)` | OpenAI Chat Completions and Responses, sync and async |
| `wrap_anthropic(client)` | Anthropic Messages, sync and async |
| `wrap(client)` | Auto-detect the provider |
| `record_llm_call(model=..., input=..., output=..., input_tokens=..., output_tokens=...)` | Any other LLM |
| `record_tool_call(name, args, result)` | Tools you can't decorate |
| `register_adapter(name, detect, wrap)` | Add your own client adapter |
| `register_price(model, input_per_million, output_per_million)` | Set prices used for cost |

Notes:

- Nested `@trace` calls join the outer trace instead of starting a new one.
- If no tool is recorded with `@tool`, the tool sequence falls back to the tool calls the model
  requested.
- Streaming responses pass through untouched and are noted on the step; their content is not
  captured yet.
- Cost comes from a built-in price table (`agentrecheck/pricing.py`). Unknown models cost `0`.
  Prices change, so override with `register_price` for anything your budgets depend on.
- `AGENTRECHECK_DISABLED=1` turns recording off. `AGENTRECHECK_DIR` moves the `.agentrecheck` folder.

## 3. Snapshot a trace into a case

```bash
agentrecheck init --entrypoint agent:run_agent   # writes agentrecheck.yaml
agentrecheck traces                              # list recorded traces
agentrecheck snapshot latest --id order_status   # or a trace id / unique prefix
```

This writes `agentrecheck_cases/order_status.yaml` with the replay input, a baseline, an exact
tool-sequence assertion, and generous budgets. Commit the file, then edit it: see
[assertions.md](assertions.md).

## 4. Run

```bash
agentrecheck run
```

For each case the runner calls your entrypoint with the recorded input, records a fresh trace,
evaluates the assertions, and compares cost, latency, and tool sequence to the baseline.

A case **fails** when:

- any assertion fails,
- the agent raises an exception, or
- cost rises more than `regression.max_cost_increase_pct` over baseline (default 25%).

Latency regression is off by default (CI timing is noisy). Turn it on with
`regression.max_latency_increase_pct`.

## 5. Configuration

`agentrecheck.yaml`:

```yaml
project: support-agent
entrypoint: agent:run_agent      # module:function, imported relative to this file
cases_dir: agentrecheck_cases

regression:
  max_cost_increase_pct: 25      # null disables
  max_latency_increase_pct: null

# judge_model: openai:gpt-4o-mini
```

Environment variables:

| Variable | Purpose |
| --- | --- |
| `AGENTRECHECK_API_KEY` + `AGENTRECHECK_API_URL` | Upload traces and runs to a dashboard. Both are required; there is no default URL. |
| `AGENTRECHECK_JUDGE_MODEL` | `openai:<model>` or `anthropic:<model>` for LLM-as-judge |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | Your own key, used only by judge checks |
| `AGENTRECHECK_DIR` | Where traces and run results are stored (default `.agentrecheck`) |
| `AGENTRECHECK_DISABLED` | `1` disables recording |

## 6. CI

Copy [`examples/github-action/agentrecheck.yml`](../examples/github-action/agentrecheck.yml) into
`.github/workflows/`. On GitHub Actions the result table and diffs are also written to the job
summary. Anywhere else, run `agentrecheck run` and let its exit code decide the build.
