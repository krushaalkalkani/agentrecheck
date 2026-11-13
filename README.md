# AgentRecheck

**CI/CD for AI agents.** Catch regressions in tool-using AI agents before they ship.

You change a prompt, swap a model, or edit a tool. Did the agent get worse? AgentRecheck records
real agent runs, turns them into test cases, and replays them on every pull request. If the agent
starts calling the wrong tools, giving worse answers, or costing more, the build fails.

```
$ agentrecheck run
┏━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┓
┃ Case                  ┃ Result ┃ Tools   ┃  Cost (vs base) ┃ Latency (vs base) ┃
┡━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━┩
│ order_status          │ PASS   │ same    │  $0.00011 (-5%) │        52ms (+7%) │
│ refund_eligible       │ PASS   │ changed │ $0.00011 (-42%) │       51ms (-29%) │
│ refund_outside_window │ FAIL   │ changed │  $0.00011 (-8%) │        51ms (+6%) │
└───────────────────────┴────────┴─────────┴─────────────────┴───────────────────┘

✗ refund_outside_window  Refund request outside the 30-day window
  ✗ tools.sequence (exact): expected ['lookup_order'], got ['issue_refund']
  ✗ output.not_contains['has been issued']: found in output
  tool sequence (baseline → current):
    - lookup_order
    + issue_refund

4/5 passed · 1 regression(s) detected.        (exit code 1)
```

## What's in this repo

| Path | What it is |
| --- | --- |
| [`sdk-python/`](sdk-python) | The `agentrecheck` Python SDK and CLI (MIT) |
| [`web/`](web) | Landing page, docs, and dashboard (Next.js, Postgres, Supabase Auth) |
| [`examples/support_agent/`](examples/support_agent) | An OpenAI tool-calling agent with 5 test cases; runs offline |
| [`examples/github-action/`](examples/github-action) | Ready-to-copy GitHub Actions workflow |
| [`docs/`](docs) | Reference docs |

## 5-minute quickstart

Requires Python 3.11+.

**1. Install**

```bash
pip install agentrecheck            # once published; from this repo: pip install -e sdk-python
```

**2. Instrument your agent**

```python
from openai import OpenAI
from agentrecheck import trace, tool, wrap_openai

client = wrap_openai(OpenAI())     # records every LLM call: model, prompt, output, tokens, cost

@tool                              # records every tool call: name, args, result, error
def lookup_order(order_id: str) -> dict:
    ...

@trace                             # records the whole run: input, steps, final output
def run_agent(message: str) -> str:
    ...                            # your existing agent loop, unchanged
```

Anthropic works the same way with `wrap_anthropic(Anthropic())`. For anything else, call
`record_llm_call(...)` and `record_tool_call(...)` yourself.

**3. Record a run and snapshot it into a test**

```bash
agentrecheck init --entrypoint agent:run_agent
python agent.py "Where is my order A1002?"
agentrecheck traces                              # what was recorded
agentrecheck snapshot latest --id order_status   # writes agentrecheck_cases/order_status.yaml
```

**4. Add assertions** (the snapshot already pins the tool sequence and sets budgets)

```yaml
assertions:
  tools:
    sequence: [lookup_order]
    mode: exact                    # or "subset": listed tools must appear, in order
    args:
      - tool: lookup_order
        exact: { order_id: A1002 } # also: regex, json_schema
  output:
    contains: ["in transit"]
    regex: "A1002"
    judge:                         # optional LLM-as-judge, runs on your own key
      rubric: Tells the customer when the order will arrive.
      min_score: 0.7
  budgets:
    max_cost_usd: 0.01
    max_latency_ms: 20000
    max_steps: 4
```

**5. Replay**

```bash
agentrecheck run     # exit 0 = all good, exit 1 = regression, exit 2 = config error
```

**6. Run it in CI** — copy [`examples/github-action/agentrecheck.yml`](examples/github-action/agentrecheck.yml)
to `.github/workflows/`.

### Try the example first (no API key needed)

```bash
cd examples/support_agent
pip install -e ../../sdk-python
agentrecheck run                            # 5/5 pass
SUPPORT_AGENT_PROMPT=v2 agentrecheck run    # a "simplified" prompt; 1 regression caught, exit 1
```

## Dashboard (optional)

The SDK and CLI work entirely offline. The dashboard adds a trace explorer with a step timeline,
test-run history, regression diffs, and cost and latency trends.

```bash
cd web
npm install
npm run dev          # http://localhost:3000
```

With no environment variables it starts in **local demo mode**: an embedded Postgres, a seeded demo
project, and a sign-in that sends no email. The demo project's API key is printed in the server log.
Point the SDK at it:

```bash
export AGENTRECHECK_API_KEY=ark_...           # from the log, or Settings → Generate new key
export AGENTRECHECK_API_URL=http://localhost:3000
agentrecheck run                              # results appear under Test runs
```

To run it for real on Vercel and Supabase, see [SUMMARY.md](SUMMARY.md#deploying).

## Documentation

- [Quickstart and concepts](docs/quickstart.md)
- [Assertions reference](docs/assertions.md)
- [CLI reference](docs/cli.md)
- [REST API](docs/api.md)
- The same content is served at `/docs` in the web app.

## Development

```bash
# SDK
cd sdk-python
uv venv --python 3.11 && uv pip install -e ".[dev]"     # or python -m venv + pip
.venv/bin/pytest --cov=agentrecheck
.venv/bin/ruff check . && .venv/bin/mypy

# Web
cd web
npm install
npm run lint && npm run typecheck && npm test && npm run build
```

## Status

Early MVP (v0.1.0). See [SUMMARY.md](SUMMARY.md) for what is built, what is mocked, and what is
next, and [TODO_FOR_KRUSHAL.md](TODO_FOR_KRUSHAL.md) for the steps that need credentials.

## License

The SDK and examples are MIT licensed. See [LICENSE](LICENSE).
