# DECISIONS

Decisions made autonomously while building. Newest at the bottom.

1. **Renamed AgentCheck -> AgentRecheck.** `agentcheck` is already taken on PyPI (checked 2026-11-13).
   `agentrecheck` was free on both PyPI and npm at that time, keeps the original idea, and describes
   what the tool does: it re-checks your agent on every change. Package, import name and CLI are all
   `agentrecheck`. Not yet registered anywhere — see TODO_FOR_KRUSHAL.md.
2. **Test cases are YAML files with the baseline embedded.** Traces live in `.agentrecheck/` (gitignored);
   cases live in `agentrecheck_cases/` and are committed. A case never depends on a trace file existing.
3. **"subset" tool-sequence mode means ordered subsequence**: every expected tool must appear, in order,
   with other calls allowed in between.
4. **A run fails when** any assertion fails, the agent raises, or cost rises more than
   `regression.max_cost_increase_pct` (default 25%) over baseline. Latency regression is off by default
   because wall-clock latency is noisy in CI; it is always shown as a delta.
5. **LLM-as-judge is optional and uses the user's own key and SDK** (`openai` or `anthropic` extras).
   With no key, judge assertions are reported as `skip`, not `fail`.
6. **No default cloud URL.** Uploads only happen when both `AGENTRECHECK_API_KEY` and
   `AGENTRECHECK_API_URL` are set, so traces can never be sent to a domain we do not control.
