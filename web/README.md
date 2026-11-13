# AgentRecheck web

Landing page (`/`), docs (`/docs`), dashboard (`/dashboard`), and the REST API (`/api/*`).

Next.js App Router, Tailwind, shadcn/ui, Drizzle, Recharts, Supabase Auth.

## Run locally

```bash
npm install
npm run dev        # http://localhost:3000
```

With no environment variables the app runs in **local demo mode**:

- Postgres runs in-process (PGlite) and is stored in `.data/`.
- A demo project with sample traces and runs is seeded. Its API key is printed in the server log.
- Sign-in accepts any email and sends nothing.

Delete `.data/` to reset. Set `AGENTRECHECK_SEED=0` to start empty.

## Run against Supabase

Copy `.env.example` to `.env.local`, fill in the three Supabase values, then:

```bash
DATABASE_URL=... npm run db:init    # creates the tables (idempotent)
npm run dev
```

## Scripts

| Script | |
| --- | --- |
| `npm run dev` / `build` / `start` | Next.js |
| `npm run lint` | ESLint |
| `npm run typecheck` | Route type generation + `tsc --noEmit` |
| `npm test` | API route tests (Vitest, in-memory database) |
| `npm run db:init` | Apply the schema to `DATABASE_URL` |

## Layout

| Path | |
| --- | --- |
| `src/app/api/` | Route handlers |
| `src/app/dashboard/` | Authenticated pages |
| `src/lib/db/` | Drizzle schema, DDL, connection (Postgres or PGlite) |
| `src/lib/data.ts` | All queries and plan limits |
| `src/lib/auth.ts` | Session and API-key resolution |
| `src/lib/seed.ts` | Demo data for local mode |
| `src/proxy.ts` | Supabase session refresh |
| `tests/api.test.ts` | API tests |
