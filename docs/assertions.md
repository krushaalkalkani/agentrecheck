# Assertions reference

A case file lives in `agentrecheck_cases/<id>.yaml`.

```yaml
id: refund_eligible
name: Refund for an eligible order
trace_id: tr_e8006f...          # the trace this was snapshotted from (informational)

input:                          # how the entrypoint is called: fn(*args, **kwargs)
  args: ["I'd like a refund for order A1001, the mouse arrived damaged."]
  kwargs: {}

baseline:                       # captured by `snapshot`; used for the diff and regression checks
  tool_sequence: [lookup_order, issue_refund]
  cost_usd: 0.00019335
  latency_ms: 72.0
  steps: 5
  output: Your refund of $49.00 for order A1001 has been issued.

assertions:
  tools: ...
  output: ...
  budgets: ...
```

Every section under `assertions` is optional.

## `tools`

| Key | Meaning |
| --- | --- |
| `sequence` | List of tool names |
| `mode: exact` (default) | The executed tools must equal `sequence` exactly |
| `mode: subset` | Every tool in `sequence` must appear, in that order. Other calls may come before, between, or after |
| `args` | List of argument checks (below) |

Each `args` entry targets one call of one tool:

```yaml
tools:
  args:
    - tool: issue_refund
      index: 0                              # which call of that tool; 0 = first (default)
      exact: { order_id: A1001, reason: arrived damaged }
    - tool: issue_refund
      regex: { order_id: "^A\\d{4}$" }      # per-argument regular expressions (re.search)
    - tool: issue_refund
      json_schema:                          # any JSON Schema
        type: object
        required: [order_id, reason]
        properties:
          reason: { type: string, minLength: 3 }
```

`exact`, `regex`, and `json_schema` can be combined in one entry. If the tool was called fewer than
`index + 1` times, the check fails.

## `output`

| Key | Meaning |
| --- | --- |
| `contains` | Substrings that must appear in the final output (case-insensitive) |
| `not_contains` | Substrings that must not appear (case-insensitive) |
| `regex` | A regular expression that must match (`re.search`, case-sensitive) |
| `judge.rubric` | What a good answer looks like, in plain language |
| `judge.min_score` | Minimum score from 0 to 1 (default 0.7) |

Non-string outputs are JSON-encoded before matching.

### LLM-as-judge

Judge checks are optional and use your own key:

```bash
pip install "agentrecheck[openai]"       # or "agentrecheck[anthropic]"
export OPENAI_API_KEY=...                # or ANTHROPIC_API_KEY
```

Choose the model with `judge_model: openai:gpt-4o-mini` in `agentrecheck.yaml` or the
`AGENTRECHECK_JUDGE_MODEL` environment variable. With no key the check is reported as `skip`. If the
judge call itself errors, the check fails with the error message.

Judge scores are model output and vary from call to call. Keep `min_score` well below what a good
answer usually scores, and prefer deterministic checks where they can express the requirement.

## `budgets`

| Key | Meaning |
| --- | --- |
| `max_cost_usd` | Total estimated LLM cost of the run |
| `max_latency_ms` | Wall-clock time of the run |
| `max_steps` | Total LLM calls plus tool calls |

## Baseline comparison

Independent of assertions, each run is compared to its baseline and the deltas are shown in the
result table. Two of them can fail a case, controlled in `agentrecheck.yaml`:

```yaml
regression:
  max_cost_increase_pct: 25        # default
  max_latency_increase_pct: null   # off by default
```

A changed tool sequence is shown as `Tools: changed` but only fails the case if a `tools.sequence`
assertion says so.

To accept a new behaviour as the baseline, re-record and snapshot again:

```bash
agentrecheck snapshot latest --id refund_eligible --force
```

`--force` overwrites the whole file, including hand-written assertions, so review the diff.
