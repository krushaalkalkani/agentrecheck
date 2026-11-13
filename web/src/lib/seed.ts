/**
 * Demo data for local mode, so the dashboard is not empty on first run.
 * Only used with the embedded local database (never with DATABASE_URL).
 */
import { count } from "drizzle-orm";

import { generateApiKey } from "./api-keys";
import { DEMO_USER_ID } from "./auth-constants";
import type { Db } from "./db";
import { projects } from "./db/schema";
import type { RunInput, TraceInput } from "./schemas";

type Scenario = {
  caseId: string;
  name: string;
  message: string;
  tools: [string, Record<string, unknown>, unknown][];
  answer: string;
};

const SCENARIOS: Scenario[] = [
  {
    caseId: "order_status",
    name: "Order status lookup",
    message: "Where is my order A1002?",
    tools: [["lookup_order", { order_id: "A1002" }, { status: "in transit", eta: "2 days" }]],
    answer: "Order A1002 (Mechanical keyboard) is in transit and should arrive in 2 days.",
  },
  {
    caseId: "password_reset",
    name: "Help-center question",
    message: "How do I reset my password?",
    tools: [["search_kb", { query: "reset password" }, { title: "Reset your password" }]],
    answer: "Go to Settings → Security → Reset password. We'll email you a reset link.",
  },
  {
    caseId: "refund_eligible",
    name: "Refund for an eligible order",
    message: "I'd like a refund for order A1001, the mouse arrived damaged.",
    tools: [
      ["lookup_order", { order_id: "A1001" }, { status: "delivered", refund_eligible: true }],
      ["issue_refund", { order_id: "A1001", reason: "arrived damaged" }, { amount: 49, status: "issued" }],
    ],
    answer: "Your refund of $49.00 for order A1001 has been issued (reference R-A1001).",
  },
  {
    caseId: "refund_outside_window",
    name: "Refund request outside the 30-day window",
    message: "Please refund order A1003, I changed my mind.",
    tools: [["lookup_order", { order_id: "A1003" }, { status: "delivered", refund_eligible: false }]],
    answer:
      "I'm sorry — order A1003 was delivered 92 days ago, which is outside our 30-day refund window.",
  },
  {
    caseId: "refund_with_question",
    name: "Refund plus a follow-up question",
    message: "I want a refund for order A1001. Also, how long do refunds take?",
    tools: [
      ["lookup_order", { order_id: "A1001" }, { status: "delivered", refund_eligible: true }],
      ["issue_refund", { order_id: "A1001", reason: "arrived damaged" }, { amount: 49, status: "issued" }],
      ["search_kb", { query: "refund processing time" }, { title: "Refund processing time" }],
    ],
    answer: "Your refund of $49.00 has been issued. Refunds arrive within 5-7 business days.",
  },
];

/** Small deterministic PRNG so the seeded data is stable across restarts. */
function rng(seed: number) {
  let state = seed;
  return () => {
    state = (state * 1664525 + 1013904223) % 4294967296;
    return state / 4294967296;
  };
}

function buildTrace(
  id: string,
  scenario: Pick<Scenario, "message" | "tools" | "answer">,
  startedAt: Date,
  rand: () => number,
  costFactor = 1,
): TraceInput {
  const steps: TraceInput["steps"] = [];
  let cursor = startedAt.getTime();
  const llm = (toolCall: [string, Record<string, unknown>] | null, output: string | null) => {
    const latency = 380 + rand() * 520;
    const inputTokens = Math.round((420 + steps.length * 95 + rand() * 40) * costFactor);
    const outputTokens = Math.round((toolCall ? 22 : 48) + rand() * 12);
    steps.push({
      type: "llm",
      index: steps.length,
      provider: "openai",
      model: "gpt-4o-mini",
      input: [{ role: "user", content: scenario.message }],
      output,
      tool_calls: toolCall ? [{ id: `call_${steps.length}`, name: toolCall[0], arguments: toolCall[1] }] : [],
      input_tokens: inputTokens,
      output_tokens: outputTokens,
      cost_usd: Number(((inputTokens * 0.15 + outputTokens * 0.6) / 1e6).toFixed(8)),
      latency_ms: Number(latency.toFixed(1)),
      started_at: new Date(cursor).toISOString(),
    });
    cursor += latency;
  };
  for (const [name, args, result] of scenario.tools) {
    llm([name, args], null);
    const latency = 25 + rand() * 90;
    steps.push({
      type: "tool",
      index: steps.length,
      name,
      args,
      result,
      latency_ms: Number(latency.toFixed(1)),
      started_at: new Date(cursor).toISOString(),
    });
    cursor += latency;
  }
  llm(null, scenario.answer);
  return {
    id,
    name: "support_agent",
    input: { args: [scenario.message], kwargs: {} },
    output: scenario.answer,
    started_at: startedAt.toISOString(),
    latency_ms: Number((cursor - startedAt.getTime()).toFixed(1)),
    steps,
    metadata: { seeded: true },
  };
}

const cost = (t: TraceInput) =>
  t.steps.reduce((sum, s) => sum + (s.type === "llm" ? s.cost_usd : 0), 0);

function buildRun(index: number, startedAt: Date, rand: () => number): RunInput {
  // Run 10 ships a "simplified" prompt that drops the verify-before-refund rule;
  // run 11 reverts it. Runs 7+ use a longer prompt (higher cost).
  const regressed = index === 10;
  const costFactor = index >= 7 ? 1.18 : 1;
  const baselineRand = rng(7);
  const results: RunInput["results"] = SCENARIOS.map((scenario, i) => {
    const baseline = buildTrace(`base_${i}`, scenario, startedAt, baselineRand);
    let actual: Pick<Scenario, "message" | "tools" | "answer"> = scenario;
    const broken = regressed && scenario.caseId === "refund_outside_window";
    if (regressed && scenario.caseId.startsWith("refund")) {
      actual = {
        ...scenario,
        tools: broken
          ? [["issue_refund", { order_id: "A1003", reason: "customer request" }, { amount: 349, status: "issued" }]]
          : scenario.tools.filter(([name]) => name !== "lookup_order"),
        answer: broken
          ? "Your refund of $349.00 for order A1003 has been issued (reference R-A1003)."
          : scenario.answer,
      };
    }
    const trace = buildTrace(`tr_seed_${index}_${i}`, actual, startedAt, rand, costFactor);
    const baselineTools = scenario.tools.map(([name]) => name);
    const actualTools = actual.tools.map(([name]) => name);
    const checks: RunInput["results"][number]["checks"] = broken
      ? [
          {
            name: "tools.sequence (exact)",
            status: "fail",
            message: "expected ['lookup_order'], got ['issue_refund']",
          },
          { name: "output.contains['30-day']", status: "fail", message: "not found in output" },
          { name: "output.not_contains['has been issued']", status: "fail", message: "found in output" },
          { name: "budgets.max_steps", status: "pass", message: "" },
        ]
      : [
          { name: "tools.sequence", status: "pass", message: "" },
          { name: "output.contains", status: "pass", message: "" },
          { name: "budgets.max_steps", status: "pass", message: "" },
        ];
    return {
      case_id: scenario.caseId,
      name: scenario.name,
      status: broken ? "fail" : "pass",
      checks,
      diff: {
        baseline_tools: baselineTools,
        actual_tools: actualTools,
        tools_changed: baselineTools.join() !== actualTools.join(),
        baseline_cost_usd: Number(cost(baseline).toFixed(8)),
        cost_usd: Number(cost(trace).toFixed(8)),
        baseline_latency_ms: baseline.latency_ms,
        latency_ms: trace.latency_ms,
        baseline_steps: baseline.steps.length,
        steps: trace.steps.length,
        judge_score:
          scenario.caseId === "refund_eligible" ? Number((0.84 + rand() * 0.12).toFixed(2)) : null,
      },
      trace,
    };
  });
  return {
    id: `run_seed_${String(index).padStart(2, "0")}`,
    started_at: startedAt.toISOString(),
    duration_ms: results.reduce((sum, r) => sum + r.diff.latency_ms, 0),
    git_sha: (0x9f3a21c + index * 0x51f15e).toString(16).padStart(7, "0").slice(0, 7),
    git_branch: regressed ? "simplify-prompt" : "main",
    results,
  };
}

export async function seedDemoData(db: Db) {
  const [{ value }] = await db.select({ value: count() }).from(projects);
  if (value > 0) return;

  const { key, hash, prefix } = generateApiKey();
  const [project] = await db
    .insert(projects)
    .values({ ownerId: DEMO_USER_ID, name: "support-agent (demo)", apiKeyHash: hash, apiKeyPrefix: prefix })
    .returning();

  // Imported lazily: data.ts depends on the db module that is calling us.
  const { insertRun, insertTraces } = await import("./data");
  const rand = rng(42);
  const now = Date.now();
  const hour = 3600_000;

  const traceItems = Array.from({ length: 12 }, (_, i) =>
    buildTrace(
      `tr_seed_live_${String(i).padStart(2, "0")}`,
      SCENARIOS[i % SCENARIOS.length],
      new Date(now - (i * 5 + 1) * hour),
      rand,
    ),
  );
  await insertTraces(project.id, traceItems, db);

  for (let i = 0; i < 14; i++) {
    await insertRun(project.id, buildRun(i, new Date(now - (13 - i) * 12 * hour), rand), db);
  }

  console.log(
    `\n[agentrecheck] Seeded demo project "${project.name}".\n` +
      `[agentrecheck] Demo API key (shown once, local only): ${key}\n`,
  );
}
