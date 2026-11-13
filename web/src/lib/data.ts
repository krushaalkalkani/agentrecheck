import { and, count, desc, eq, gte, or } from "drizzle-orm";

import { generateApiKey, hashApiKey } from "./api-keys";
import { getDb, schema, type Db } from "./db";
import type { Project } from "./db/schema";
import type { RunInput, TraceInput } from "./schemas";

const { projects, traces, testRuns, waitlist } = schema;

/** Free plan limits (the Pro plan is "coming soon"). */
export const FREE_PROJECT_LIMIT = 1;
export const FREE_TRACES_PER_MONTH = 1000;

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export class LimitError extends Error {}

// ------------------------------------------------------------------ projects

export async function listProjects(ownerId: string) {
  const db = await getDb();
  return db.select().from(projects).where(eq(projects.ownerId, ownerId)).orderBy(projects.createdAt);
}

export async function getProject(ownerId: string, projectId: string): Promise<Project | null> {
  if (!UUID_RE.test(projectId)) return null;
  const db = await getDb();
  const [row] = await db
    .select()
    .from(projects)
    .where(and(eq(projects.id, projectId), eq(projects.ownerId, ownerId)));
  return row ?? null;
}

export async function getProjectByApiKey(key: string): Promise<Project | null> {
  const db = await getDb();
  const [row] = await db.select().from(projects).where(eq(projects.apiKeyHash, hashApiKey(key)));
  return row ?? null;
}

export async function createProject(ownerId: string, name: string) {
  const db = await getDb();
  const [{ value: existing }] = await db
    .select({ value: count() })
    .from(projects)
    .where(eq(projects.ownerId, ownerId));
  if (existing >= FREE_PROJECT_LIMIT) {
    throw new LimitError(
      `The Free plan includes ${FREE_PROJECT_LIMIT} project. Join the Pro waitlist for unlimited projects.`,
    );
  }
  const { key, hash, prefix } = generateApiKey();
  const [project] = await db
    .insert(projects)
    .values({ ownerId, name, apiKeyHash: hash, apiKeyPrefix: prefix })
    .returning();
  return { project, apiKey: key };
}

export async function rotateApiKey(ownerId: string, projectId: string) {
  const project = await getProject(ownerId, projectId);
  if (!project) return null;
  const db = await getDb();
  const { key, hash, prefix } = generateApiKey();
  await db
    .update(projects)
    .set({ apiKeyHash: hash, apiKeyPrefix: prefix })
    .where(eq(projects.id, projectId));
  return key;
}

// -------------------------------------------------------------------- traces

function traceTotals(t: TraceInput) {
  let cost = 0;
  let tokens = 0;
  let llmCalls = 0;
  const executed: string[] = [];
  const requested: string[] = [];
  for (const step of t.steps) {
    if (step.type === "llm") {
      llmCalls += 1;
      cost += step.cost_usd;
      tokens += step.input_tokens + step.output_tokens;
      requested.push(...step.tool_calls.map((c) => c.name));
    } else {
      executed.push(step.name);
    }
  }
  return {
    costUsd: Number(cost.toFixed(8)),
    totalTokens: tokens,
    llmCalls,
    toolCalls: executed.length,
    toolSequence: executed.length ? executed : requested,
  };
}

export async function countTracesThisMonth(projectId: string, conn?: Db) {
  const db = conn ?? (await getDb());
  const now = new Date();
  const monthStart = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1));
  const [{ value }] = await db
    .select({ value: count() })
    .from(traces)
    .where(and(eq(traces.projectId, projectId), gte(traces.createdAt, monthStart)));
  return value;
}

/** `conn` lets the seeder write while the shared connection is still initializing. */
export async function insertTraces(projectId: string, items: TraceInput[], conn?: Db) {
  const used = await countTracesThisMonth(projectId, conn);
  if (used + items.length > FREE_TRACES_PER_MONTH) {
    throw new LimitError(
      `Free plan limit reached (${FREE_TRACES_PER_MONTH} traces per month). Join the Pro waitlist for 50k.`,
    );
  }
  const db = conn ?? (await getDb());
  await db
    .insert(traces)
    .values(
      items.map((t) => ({
        projectId,
        externalId: t.id,
        name: t.name,
        input: t.input ?? null,
        output: t.output ?? null,
        error: t.error ?? null,
        startedAt: new Date(t.started_at),
        latencyMs: t.latency_ms,
        steps: t.steps,
        metadata: t.metadata,
        ...traceTotals(t),
      })),
    )
    // Re-uploading the same trace is a no-op.
    .onConflictDoNothing({ target: [traces.projectId, traces.externalId] });
  return items.map((t) => t.id);
}

const traceSummary = {
  id: traces.id,
  externalId: traces.externalId,
  name: traces.name,
  error: traces.error,
  startedAt: traces.startedAt,
  latencyMs: traces.latencyMs,
  costUsd: traces.costUsd,
  totalTokens: traces.totalTokens,
  llmCalls: traces.llmCalls,
  toolCalls: traces.toolCalls,
  toolSequence: traces.toolSequence,
};

export async function listTraces(projectId: string, limit = 50) {
  const db = await getDb();
  return db
    .select(traceSummary)
    .from(traces)
    .where(eq(traces.projectId, projectId))
    .orderBy(desc(traces.startedAt))
    .limit(Math.min(Math.max(limit, 1), 200));
}

/** Look up by internal uuid or by the SDK's trace id. */
export async function getTrace(projectId: string, idOrExternal: string) {
  const db = await getDb();
  const match = UUID_RE.test(idOrExternal)
    ? or(eq(traces.id, idOrExternal), eq(traces.externalId, idOrExternal))
    : eq(traces.externalId, idOrExternal);
  const [row] = await db.select().from(traces).where(and(eq(traces.projectId, projectId), match));
  return row ?? null;
}

// ---------------------------------------------------------------------- runs

export async function insertRun(projectId: string, run: RunInput, conn?: Db) {
  const db = conn ?? (await getDb());
  const total = run.results.length;
  const passed = run.results.filter((r) => r.status === "pass").length;
  const cost = run.results.reduce((sum, r) => sum + r.diff.cost_usd, 0);
  const latency = total ? run.results.reduce((sum, r) => sum + r.diff.latency_ms, 0) / total : 0;
  const values = {
    projectId,
    externalId: run.id,
    startedAt: new Date(run.started_at),
    durationMs: run.duration_ms,
    total,
    passed,
    failed: total - passed,
    costUsd: Number(cost.toFixed(8)),
    avgLatencyMs: Number(latency.toFixed(3)),
    gitSha: run.git_sha ?? null,
    gitBranch: run.git_branch ?? null,
    results: run.results,
  };
  const [row] = await db
    .insert(testRuns)
    .values(values)
    .onConflictDoUpdate({ target: [testRuns.projectId, testRuns.externalId], set: values })
    .returning({ id: testRuns.id });
  return row.id;
}

const runSummary = {
  id: testRuns.id,
  externalId: testRuns.externalId,
  startedAt: testRuns.startedAt,
  durationMs: testRuns.durationMs,
  total: testRuns.total,
  passed: testRuns.passed,
  failed: testRuns.failed,
  costUsd: testRuns.costUsd,
  avgLatencyMs: testRuns.avgLatencyMs,
  gitSha: testRuns.gitSha,
  gitBranch: testRuns.gitBranch,
};

export async function listRuns(projectId: string, limit = 50) {
  const db = await getDb();
  return db
    .select(runSummary)
    .from(testRuns)
    .where(eq(testRuns.projectId, projectId))
    .orderBy(desc(testRuns.startedAt))
    .limit(Math.min(Math.max(limit, 1), 200));
}

export async function getRun(projectId: string, idOrExternal: string) {
  const db = await getDb();
  const match = UUID_RE.test(idOrExternal)
    ? or(eq(testRuns.id, idOrExternal), eq(testRuns.externalId, idOrExternal))
    : eq(testRuns.externalId, idOrExternal);
  const [row] = await db.select().from(testRuns).where(and(eq(testRuns.projectId, projectId), match));
  return row ?? null;
}

// ------------------------------------------------------------------ waitlist

export async function addToWaitlist(email: string, plan = "pro") {
  const db = await getDb();
  await db
    .insert(waitlist)
    .values({ email: email.trim().toLowerCase(), plan })
    .onConflictDoNothing({ target: waitlist.email });
}
