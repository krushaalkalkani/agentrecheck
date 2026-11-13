# Summary

**AgentRecheck** (renamed from AgentCheck, see [DECISIONS.md](DECISIONS.md)) — CI/CD for AI agents.
Built end to end in one session on 2026-11-13. Version 0.1.0.

## What was built

| Scope item | Status | Where |
| --- | --- | --- |
| 1. Python SDK: `@trace`, `@tool`, OpenAI + Anthropic adapters, local JSON, optional upload | Done | `sdk-python/src/agentrecheck/` |
| 2. Test cases from traces: `snapshot`, YAML assertions (tool sequence, tool args, output, judge, budgets) | Done | `snapshot.py`, `assertions.py`, `judge.py` |
| 3. CLI runner: replay, baseline diff, pass/fail table, non-zero exit, GitHub Action | Done | `cli.py`, `runner.py`, `report.py`, `examples/github-action/` |
| 4. Web dashboard: auth, projects + API keys, trace explorer with timeline, test runs with diffs and trend charts | Done; real auth and database need your credentials | `web/src/app/dashboard/` |
| 5. Landing page with pricing and waitlist form saved to the database | Done | `web/src/app/page.tsx` |
| 6. Docs: README quickstart, `/docs` page, example agent with 5 cases and a caught regression | Done | `README.md`, `docs/`, `examples/support_agent/` |
| Launch kit, changelog, MIT license | Done | `LAUNCH.md`, `CHANGELOG.md`, `LICENSE` |

## What was verified, and how

| Check | Result |
| --- | --- |
| SDK tests (`pytest`) | 41 passed, 96% line coverage |
| SDK lint and types (`ruff check`, `ruff format --check`, `mypy`) | Clean |
| Web API tests (`vitest`, in-memory Postgres) | 10 passed |
| Web lint and types (`eslint`, `tsc --noEmit`) | Clean |
| Web production build (`next build`) | Succeeds |
| Example, good prompt (`agentrecheck run`) | 5/5 pass, exit 0 |
| Example, regressed prompt (`SUPPORT_AGENT_PROMPT=v2`) | 4/5, `refund_outside_window` fails, exit 1 |
| End to end: example agent → CLI → upload → dashboard | Trace and both runs uploaded to the local app and viewed in the browser |
| Pages viewed in a browser | Landing (desktop and 375px), docs, demo sign-in, projects, runs list with charts, run detail with diff, traces list, trace timeline, settings |

**Not verified:**

- Anything against real Supabase: magic-link email, the auth callback, session refresh, and the
  `postgres` driver path. These type-check and follow the documented `@supabase/ssr` pattern but
  have never run against a real project.
- LLM-as-judge against a real model, and the adapters against the real OpenAI / Anthropic SDKs.
  Both are tested with fakes shaped like the SDK responses.
- The "create project" and "generate new key" buttons were not clicked in the browser (the
  underlying functions are covered by API tests; the demo workspace is already at the 1-project
  limit).
- A Vercel deployment. Nothing was deployed.

## Run it locally

### SDK + example (no API key needed)

```bash
cd sdk-python
uv venv --python 3.11 && uv pip install -e ".[dev]"    # or: python3.11 -m venv .venv && .venv/bin/pip install -e ".[dev]"
source .venv/bin/activate

cd ../examples/support_agent
python agent.py "Where is my order A1002?"
agentrecheck traces
agentrecheck run                             # 5/5
SUPPORT_AGENT_PROMPT=v2 agentrecheck run     # caught regression, exit 1
```

### Dashboard

```bash
cd web
npm install
npm run dev                                  # http://localhost:3000
```

Sign in with any email (demo mode). A seeded project with 14 runs and 12 traces is ready. To send
your own data, copy the demo API key from the server log (or use **Settings → Generate new key**):

```bash
export AGENTRECHECK_API_KEY=ark_...
export AGENTRECHECK_API_URL=http://localhost:3000
cd examples/support_agent && agentrecheck run
```

### Tests

```bash
cd sdk-python && .venv/bin/pytest --cov=agentrecheck && .venv/bin/ruff check . && .venv/bin/mypy
cd web && npm run lint && npm run typecheck && npm test && npm run build
```

## Deploying

### 1. Supabase (database + auth)

1. Create a project at supabase.com.
2. **Project Settings → Database → Connection string**: copy the **Transaction pooler** URI. This is
   `DATABASE_URL`.
3. Create the tables. Either:
   ```bash
   cd web && DATABASE_URL='postgres://...' npm run db:init
   ```
   or paste the SQL from `web/src/lib/db/init-sql.ts` into the Supabase SQL editor. The script is
   idempotent and enables row level security on every table (the app only connects server-side).
4. **Project Settings → API**: copy the project URL and the anon key
   (`NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`).
5. **Authentication → URL Configuration**: set **Site URL** to your production URL and add
   `https://<your-domain>/auth/callback` (and `http://localhost:3000/auth/callback` for local
   development) to **Redirect URLs**. Email sign-in is enabled by default.

### 2. Vercel

1. Push the repo to GitHub and import it in Vercel.
2. Set **Root Directory** to `web`. Framework preset: Next.js. No build settings to change.
3. Add environment variables (Production and Preview):

   | Name | Value |
   | --- | --- |
   | `DATABASE_URL` | Supabase transaction pooler URI |
   | `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL |
   | `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon key |
   | `NEXT_PUBLIC_APP_URL` | `https://<your-domain>` (no trailing slash) |
   | `NEXT_PUBLIC_GITHUB_URL` | Your repo URL |

4. Deploy, sign in with a magic link, create a project, copy its API key.
5. Point the SDK at it: `AGENTRECHECK_API_URL=https://<your-domain>`.

If you deploy **without** the Supabase variables, the app still boots in demo mode with an
in-memory database that resets on every cold start. Useful for a preview; not for real use.

### 3. PyPI

```bash
cd sdk-python && uv build && uv publish
```

## What is mocked or stubbed

| Thing | What happens today | To make it real |
| --- | --- | --- |
| Postgres | Embedded PGlite when `DATABASE_URL` is unset. Same schema and queries. | Set `DATABASE_URL` |
| Auth | Demo sign-in (any email, shared workspace) when Supabase env vars are unset | Set the two Supabase env vars |
| OpenAI in the example | Deterministic offline client in `mock_llm.py` | Set `OPENAI_API_KEY`, `pip install openai` |
| Dashboard data | Seeded demo project in local mode only | Never seeded when `DATABASE_URL` is set |
| LLM-as-judge | Real code, tested only with fake clients; skipped with no key | Set a provider key |
| Billing / Pro plan | None. Pro is "coming soon" with a waitlist, as specified | Out of scope |
| `pip install agentrecheck` | Package is not published | Publish to PyPI |
| GitHub link | Placeholder `https://github.com/your-org/agentrecheck` | Set `NEXT_PUBLIC_GITHUB_URL` |

See [TODO_FOR_KRUSHAL.md](TODO_FOR_KRUSHAL.md) for the full list of things that need you.

## Top 5 next steps

1. **Connect Supabase, deploy to Vercel, and click through real sign-in.** This is the only part of
   the product that has not run for real. About an hour, most of it dashboard clicking.
2. **Publish to PyPI and push to GitHub** so the quickstart is literally true, then run the example
   once against real OpenAI and adjust any assertion that is too tied to the mock's wording.
3. **Handle non-determinism properly.** Real agents vary between runs. Add `--repeat N` with a
   pass-rate threshold per case so one unlucky sample does not fail a build, and report flaky cases.
4. **Capture streaming responses and add framework adapters** (LangChain / LangGraph, OpenAI Agents
   SDK, Vercel AI SDK via a TypeScript SDK). Most production agents stream, and the stated target
   user includes TypeScript teams.
5. **Close the loop in the pull request.** Post the markdown summary as a PR comment with a link to
   the run in the dashboard, and add a "promote this run to baseline" action so accepting an
   intended change is one click instead of a re-snapshot.
