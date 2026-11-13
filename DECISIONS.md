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
7. **The example runs offline by default.** No OpenAI key was available, so `examples/support_agent`
   ships a deterministic stand-in for the OpenAI client (`mock_llm.py`) that reads the system prompt
   and behaves accordingly. With `OPENAI_API_KEY` set it uses the real API. This also makes the
   example free and stable in CI.
8. **The "caught regression" is opt-in.** `agentrecheck run` passes 5/5 by default so the example
   doubles as a green CI demo. `SUPPORT_AGENT_PROMPT=v2 agentrecheck run` swaps in a "simplified"
   prompt and fails `refund_outside_window` with exit code 1.
9. **Web: Postgres everywhere, with an embedded fallback.** No Supabase credentials were available,
   and creating a project would have meant provisioning paid-tier-eligible resources on your account
   without asking. The app uses Drizzle against `DATABASE_URL` when set, and otherwise runs the same
   schema and queries on PGlite (Postgres compiled to WASM, in-process). One code path, no separate
   mock store.
10. **Auth falls back to a demo sign-in** when Supabase env vars are missing: any email, no message
    sent, one shared local workspace. Clearly labelled "demo mode" in the UI.
11. **API keys are hashed (SHA-256) and shown once.** The settings page can generate a new key but
    cannot reveal the old one.
12. **Run traces are stored inside the run, not in the trace explorer.** Replays from
    `agentrecheck run` would otherwise flood the explorer and eat the Free plan's trace quota.
13. **Next.js 16 with Cache Components turned off.** `create-next-app` now enables Cache Components
    by default. The dashboard is fully dynamic and per-user, so I kept the classic request-time
    model (`cacheComponents: false`), which is simpler to reason about for an MVP.
14. **shadcn/ui via the official CLI** (`base-nova` style, Base UI primitives): button, card, badge,
    input, label, table, tabs.
15. **Judge SDKs are optional extras**, not core dependencies, and a provider key that merely happens
    to be in the environment without its SDK installed results in a skipped check rather than an error.
16. **No destructive commands.** A safety hook in this environment blocks `rm`; nothing was deleted
    during the build.
