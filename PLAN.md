# PLAN

Product: **AgentRecheck** — CI/CD for AI agents. (Renamed from AgentCheck; see DECISIONS.md.)

## 1. Python SDK (`sdk-python`)
- [x] Trace models (pydantic) + `@trace` decorator / `start_trace` context manager
- [x] `@tool` decorator + manual `record_llm_call` / `record_tool_call`
- [x] Pluggable adapters: OpenAI (chat completions + responses), Anthropic (messages)
- [x] Cost table, local JSON storage, optional cloud upload

## 2. Test cases from traces
- [x] `agentrecheck snapshot <trace_id>` -> YAML case with baseline
- [x] Assertions: tool sequence (exact/subset), tool args (exact/regex/JSON schema),
      output (contains/regex/LLM judge), budgets (cost/latency/steps)

## 3. CLI runner
- [x] `agentrecheck run` replays cases, compares to baseline, prints table + diffs
- [x] Non-zero exit on regression; markdown summary for CI
- [x] GitHub Action YAML in `/examples`

## 4. Web dashboard (`web`)
- [x] Next.js + Tailwind + shadcn-style UI, Drizzle schema, Postgres (Supabase) with local fallback
- [x] Auth: Supabase magic link (demo-mode fallback when not configured)
- [x] Projects + API key per project
- [x] REST API: POST /api/traces, POST /api/runs, GET endpoints, POST /api/waitlist
- [x] Trace explorer with timeline; test runs with history, diffs, trend charts

## 5. Landing page
- [x] Hero, problem, how it works, code snippet, pricing + waitlist form, links

## 6. Docs + example
- [x] README quickstart, /docs page
- [x] `examples/support_agent` (3 tools, 5 cases, one caught regression)

## 7. Quality
- [x] pytest (80%+ core), ruff, mypy
- [x] API route tests, eslint, tsc, production build
- [x] End-to-end: example -> CLI -> upload -> dashboard

## 8. Launch kit
- [x] LAUNCH.md, CHANGELOG.md, LICENSE (MIT), SUMMARY.md, TODO_FOR_KRUSHAL.md
