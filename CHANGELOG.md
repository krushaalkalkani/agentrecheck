# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-11-13

First release.

### Added

**Python SDK (`agentrecheck`)**

- `@trace` decorator and `start_trace` context manager that record an agent run: input, LLM calls
  (model, prompt, output, tokens, latency, cost), tool calls (name, args, result, error), and final
  output. Sync and async.
- `@tool` decorator, plus `record_llm_call` and `record_tool_call` for manual instrumentation.
- Adapters for the OpenAI SDK (Chat Completions and Responses) and the Anthropic SDK (Messages),
  with a pluggable registry (`register_adapter`) and auto-detection (`wrap`).
- Built-in price table with `register_price` overrides.
- Local JSON trace storage and optional upload to the dashboard API.

**Test cases**

- `agentrecheck snapshot` turns a recorded trace into a YAML case with its baseline.
- Assertions: tool sequence (`exact` or ordered `subset`), tool arguments (exact, regex, JSON
  Schema), final output (contains, not_contains, regex, LLM-as-judge with a rubric), and budgets
  (max cost, latency, steps).
- Optional LLM-as-judge using the user's own OpenAI or Anthropic key. Skipped when no key is set.

**CLI**

- `agentrecheck init | traces | show | snapshot | run | upload | version`.
- `run` replays every case, compares against baseline, prints a pass/fail table with tool-sequence
  diffs and cost/latency deltas, and exits non-zero on regression.
- Markdown summary for CI, written to `$GITHUB_STEP_SUMMARY` when present.

**Web app**

- Landing page with pricing and a Pro waitlist form.
- Docs page.
- Dashboard: projects with one API key each, trace explorer with a step timeline, test-run history
  with regression diffs and cost/latency trend charts.
- REST API: `POST/GET /api/traces`, `POST/GET /api/runs`, `POST /api/waitlist`, authenticated with
  a project API key.
- Supabase magic-link auth, with a local demo mode (embedded Postgres, seeded data) when no
  credentials are configured.

**Examples**

- `examples/support_agent`: an OpenAI tool-calling agent with three tools and five test cases, one
  of which demonstrates a caught regression. Runs offline.
- `examples/github-action/agentrecheck.yml`: ready-to-copy workflow.
