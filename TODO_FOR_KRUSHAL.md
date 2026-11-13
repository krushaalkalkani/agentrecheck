# TODO for Krushal

Things I could not or should not do without you. Nothing here blocks running the product locally.

## Needs your accounts or credentials

1. **Create the Supabase project and connect it.** I did not create any cloud resources.
   Until this is done the web app runs in local demo mode (embedded Postgres, no real auth).
   Steps are in [SUMMARY.md](SUMMARY.md#deploying). You need three values:
   `DATABASE_URL`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
2. **Deploy `web/` to Vercel** and set the env vars from `web/.env.example`.
3. **Test magic-link sign-in against real Supabase.** The Supabase code path (login action,
   `/auth/callback`, session refresh in `src/proxy.ts`) follows the `@supabase/ssr` pattern and
   type-checks, but it has never run against a real project. Budget 15 minutes to click through it.
4. **Publish the SDK to PyPI** as `agentrecheck`. The name was free on PyPI and npm when I checked
   on 2026-11-13, but it is not reserved:
   ```bash
   cd sdk-python && uv build && uv publish
   ```
   Until then, `pip install agentrecheck` in the README, docs, landing page, and GitHub Action does
   not work; use `pip install -e sdk-python`.
5. **Create the GitHub repo and push.** Then set `NEXT_PUBLIC_GITHUB_URL` (the landing page links
   to a placeholder, `https://github.com/your-org/agentrecheck`) and replace `<REPO_URL>` /
   `<SITE_URL>` in `LAUNCH.md`.
6. **Run the judge against a real model once.** LLM-as-judge is tested with fake clients only.
   I noticed `ANTHROPIC_API_KEY` is set in your shell and deliberately did not use it, so no API
   calls were made and nothing was spent.
   ```bash
   cd examples/support_agent
   pip install "agentrecheck[anthropic]"     # or [openai]
   agentrecheck run --case refund_eligible
   ```
7. **Run the example against real OpenAI once** (`pip install openai`, set `OPENAI_API_KEY`). The
   example's five cases were recorded against the offline stand-in. A real model may phrase answers
   differently, so expect to loosen one or two `output.contains` checks and re-snapshot baselines.

## Decisions for you

8. **The name.** I renamed AgentCheck to AgentRecheck because `agentcheck` is taken on PyPI.
   Check the `.com` / `.dev` domain and trademark before launch. Renaming again is a find-and-replace
   of `agentrecheck` / `AgentRecheck` plus the `sdk-python/src/agentrecheck` folder.
9. **Model prices** in `sdk-python/src/agentrecheck/pricing.py`. The Anthropic prices come from
   current reference data; the OpenAI ones are from memory and marked approximate. Verify them
   before anyone relies on cost budgets.
10. **Demo mode on a public deployment.** If you deploy without Supabase env vars, anyone can
    "sign in" to a shared demo workspace with any email. Fine for a preview; not for launch.

## Known gaps (not blockers)

- No billing. Pro is waitlist-only, as specified. Free limits (1 project, 1,000 traces/month) are
  enforced in `web/src/lib/data.ts`.
- No team seats or project deletion UI.
- Streaming LLM responses are passed through but not captured.
- No TypeScript SDK (the target user includes TS teams; Python came first per the scope).
- Waitlist emails are stored in the `waitlist` table; there is no notification or export.
