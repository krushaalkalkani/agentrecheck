import {
  doublePrecision,
  integer,
  jsonb,
  pgTable,
  text,
  timestamp,
  uniqueIndex,
  uuid,
} from "drizzle-orm/pg-core";

const id = () =>
  uuid("id")
    .primaryKey()
    .$defaultFn(() => crypto.randomUUID());
const createdAt = () =>
  timestamp("created_at", { withTimezone: true }).notNull().defaultNow();

export const projects = pgTable("projects", {
  id: id(),
  // Supabase auth user id (or the demo user id when auth is not configured).
  ownerId: text("owner_id").notNull(),
  name: text("name").notNull(),
  // Only a SHA-256 hash of the API key is stored; the key is shown once.
  apiKeyHash: text("api_key_hash").notNull().unique(),
  apiKeyPrefix: text("api_key_prefix").notNull(),
  createdAt: createdAt(),
});

export const traces = pgTable(
  "traces",
  {
    id: id(),
    projectId: uuid("project_id")
      .notNull()
      .references(() => projects.id, { onDelete: "cascade" }),
    externalId: text("external_id").notNull(),
    name: text("name").notNull(),
    input: jsonb("input"),
    output: jsonb("output"),
    error: text("error"),
    startedAt: timestamp("started_at", { withTimezone: true }).notNull(),
    latencyMs: doublePrecision("latency_ms").notNull().default(0),
    costUsd: doublePrecision("cost_usd").notNull().default(0),
    totalTokens: integer("total_tokens").notNull().default(0),
    llmCalls: integer("llm_calls").notNull().default(0),
    toolCalls: integer("tool_calls").notNull().default(0),
    toolSequence: jsonb("tool_sequence").$type<string[]>().notNull().default([]),
    steps: jsonb("steps").$type<unknown[]>().notNull().default([]),
    metadata: jsonb("metadata").$type<Record<string, unknown>>().notNull().default({}),
    createdAt: createdAt(),
  },
  (t) => [uniqueIndex("traces_project_external_idx").on(t.projectId, t.externalId)],
);

export const testRuns = pgTable(
  "test_runs",
  {
    id: id(),
    projectId: uuid("project_id")
      .notNull()
      .references(() => projects.id, { onDelete: "cascade" }),
    externalId: text("external_id").notNull(),
    startedAt: timestamp("started_at", { withTimezone: true }).notNull(),
    durationMs: doublePrecision("duration_ms").notNull().default(0),
    total: integer("total").notNull().default(0),
    passed: integer("passed").notNull().default(0),
    failed: integer("failed").notNull().default(0),
    costUsd: doublePrecision("cost_usd").notNull().default(0),
    avgLatencyMs: doublePrecision("avg_latency_ms").notNull().default(0),
    gitSha: text("git_sha"),
    gitBranch: text("git_branch"),
    results: jsonb("results").$type<unknown[]>().notNull().default([]),
    createdAt: createdAt(),
  },
  (t) => [uniqueIndex("test_runs_project_external_idx").on(t.projectId, t.externalId)],
);

export const waitlist = pgTable("waitlist", {
  id: id(),
  email: text("email").notNull().unique(),
  plan: text("plan").notNull().default("pro"),
  createdAt: createdAt(),
});

export type Project = typeof projects.$inferSelect;
export type TraceRow = typeof traces.$inferSelect;
export type TestRunRow = typeof testRuns.$inferSelect;
