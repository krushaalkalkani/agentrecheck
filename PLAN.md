# PLAN

Product: **AgentRecheck** — CI/CD for AI agents. (Renamed from AgentCheck; see DECISIONS.md.)

## 1. Python SDK (`sdk-python`)
- [ ] Trace models (pydantic) + `@trace` decorator / `start_trace` context manager
- [ ] `@tool` decorator + manual `record_llm_call` / `record_tool_call`
- [ ] Pluggable adapters: OpenAI (chat completions + responses), Anthropic (messages)
- [ ] Cost table, local JSON storage, optional cloud upload

## 2. Test cases from traces
- [ ] `agentrecheck snapshot <trace_id>` -> YAML case with baseline
- [ ] Assertions: tool sequence (exact/subset), tool args (exact/regex/JSON schema),
      output (contains/regex/LLM judge), budgets (cost/latency/steps)

## 3. CLI runner
- [ ] `agentrecheck run` replays cases, compares to baseline, prints table + diffs
- [ ] Non-zero exit on regression; markdown summary for CI
- [ ] GitHub Action YAML in `/examples`

## 4. Web dashboard (`web`)
- [ ] Next.js + Tailwind + shadcn-style UI, Drizzle schema, Postgres (Supabase) with local fallback
- [ ] Auth: Supabase magic link (demo-mode fallback when not configured)
- [ ] Projects + API key per project
- [ ] REST API: POST /api/traces, POST /api/runs, GET endpoints, POST /api/waitlist
- [ ] Trace explorer with timeline; test runs with history, diffs, trend charts

## 5. Landing page
- [ ] Hero, problem, how it works, code snippet, pricing + waitlist form, links

## 6. Docs + example
- [ ] README quickstart, /docs page
- [ ] `examples/support_agent` (3 tools, 5 cases, one caught regression)

## 7. Quality
- [ ] pytest (80%+ core), ruff, mypy
- [ ] API route tests, eslint, tsc, production build
- [ ] End-to-end: example -> CLI -> upload -> dashboard

## 8. Launch kit
- [ ] LAUNCH.md, CHANGELOG.md, LICENSE (MIT), SUMMARY.md, TODO_FOR_KRUSHAL.md
