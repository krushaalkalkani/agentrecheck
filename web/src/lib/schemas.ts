import { z } from "zod";

const stepBase = {
  index: z.number().int().default(0),
  latency_ms: z.number().default(0),
  started_at: z.string(),
  error: z.string().nullish(),
};

const llmStep = z.object({
  ...stepBase,
  type: z.literal("llm"),
  provider: z.string().default("unknown"),
  model: z.string().default("unknown"),
  input: z.unknown().optional(),
  output: z.unknown().optional(),
  tool_calls: z
    .array(z.object({ id: z.string().nullish(), name: z.string(), arguments: z.unknown().optional() }))
    .default([]),
  input_tokens: z.number().int().default(0),
  output_tokens: z.number().int().default(0),
  cost_usd: z.number().default(0),
});

const toolStep = z.object({
  ...stepBase,
  type: z.literal("tool"),
  name: z.string(),
  args: z.record(z.string(), z.unknown()).default({}),
  result: z.unknown().optional(),
});

export const traceSchema = z.object({
  id: z.string().min(1).max(200),
  name: z.string().max(500).default("agent"),
  input: z.unknown().optional(),
  output: z.unknown().optional(),
  error: z.string().nullish(),
  started_at: z.iso.datetime({ offset: true }),
  latency_ms: z.number().default(0),
  steps: z.array(z.discriminatedUnion("type", [llmStep, toolStep])).max(2000).default([]),
  metadata: z.record(z.string(), z.unknown()).default({}),
});

export type TraceInput = z.infer<typeof traceSchema>;

export const tracesBodySchema = z.union([
  traceSchema.transform((t) => [t]),
  z.object({ traces: z.array(traceSchema).min(1).max(100) }).transform((b) => b.traces),
]);

const checkSchema = z.object({
  name: z.string(),
  status: z.enum(["pass", "fail", "skip"]),
  message: z.string().default(""),
});

const diffSchema = z.object({
  baseline_tools: z.array(z.string()).nullable().default(null),
  actual_tools: z.array(z.string()).default([]),
  tools_changed: z.boolean().default(false),
  baseline_cost_usd: z.number().nullable().default(null),
  cost_usd: z.number().default(0),
  baseline_latency_ms: z.number().nullable().default(null),
  latency_ms: z.number().default(0),
  baseline_steps: z.number().nullable().default(null),
  steps: z.number().default(0),
  judge_score: z.number().nullable().default(null),
});

export const runSchema = z.object({
  id: z.string().min(1).max(200),
  started_at: z.iso.datetime({ offset: true }),
  duration_ms: z.number().default(0),
  git_sha: z.string().nullish(),
  git_branch: z.string().nullish(),
  results: z
    .array(
      z.object({
        case_id: z.string(),
        name: z.string().default(""),
        status: z.enum(["pass", "fail", "error"]),
        error: z.string().nullish(),
        checks: z.array(checkSchema).default([]),
        diff: diffSchema,
        trace: traceSchema.nullable().default(null),
      }),
    )
    .max(1000),
});

export type RunInput = z.infer<typeof runSchema>;

export const waitlistSchema = z.object({
  email: z.email().max(320),
  plan: z.string().max(40).default("pro"),
});
