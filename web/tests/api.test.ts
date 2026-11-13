import { beforeAll, describe, expect, it, vi } from "vitest";

// Route handlers read cookies for dashboard sessions; there is no request
// scope in unit tests, so stub it out as "not signed in".
vi.mock("next/headers", () => ({
  cookies: async () => ({ get: () => undefined, getAll: () => [], set: () => {} }),
}));

import { GET as getRun } from "@/app/api/runs/[id]/route";
import { GET as listRuns, POST as postRun } from "@/app/api/runs/route";
import { GET as getTrace } from "@/app/api/traces/[id]/route";
import { GET as listTraces, POST as postTraces } from "@/app/api/traces/route";
import { POST as postWaitlist } from "@/app/api/waitlist/route";
import { createProject, LimitError } from "@/lib/data";
import { getDb, schema } from "@/lib/db";

const BASE = "http://localhost:3000";
let apiKey = "";
let projectId = "";

function req(path: string, init: { method?: string; body?: unknown; key?: string | null } = {}) {
  const key = init.key === undefined ? apiKey : init.key;
  return new Request(BASE + path, {
    method: init.method ?? "GET",
    headers: {
      "content-type": "application/json",
      ...(key ? { authorization: `Bearer ${key}` } : {}),
    },
    body: init.body === undefined ? undefined : JSON.stringify(init.body),
  });
}

const params = (id: string) => ({ params: Promise.resolve({ id }) });

// Shaped exactly like the Python SDK's Trace.to_payload().
function trace(id: string) {
  return {
    id,
    name: "support_agent",
    input: { args: ["Where is my order A1002?"], kwargs: {} },
    output: "Order A1002 is in transit.",
    error: null,
    started_at: "2026-11-13T05:37:29.123456+00:00",
    ended_at: "2026-11-13T05:37:30.123456+00:00",
    latency_ms: 812.5,
    metadata: {},
    steps: [
      {
        type: "llm",
        index: 0,
        provider: "openai",
        model: "gpt-4o-mini",
        input: [{ role: "user", content: "hi" }],
        output: null,
        tool_calls: [{ id: "call_0", name: "lookup_order", arguments: { order_id: "A1002" } }],
        input_tokens: 400,
        output_tokens: 20,
        cost_usd: 0.000072,
        latency_ms: 400,
        started_at: "2026-11-13T05:37:29.200000+00:00",
        error: null,
      },
      {
        type: "tool",
        index: 1,
        name: "lookup_order",
        args: { order_id: "A1002" },
        result: { status: "in transit" },
        error: null,
        latency_ms: 30,
        started_at: "2026-11-13T05:37:29.600000+00:00",
      },
    ],
    total_cost_usd: 0.000072,
    tool_sequence: ["lookup_order"],
  };
}

function run(id: string, status: "pass" | "fail" = "pass") {
  return {
    id,
    project: "support-agent",
    started_at: "2026-11-13T06:00:00+00:00",
    duration_ms: 900,
    git_sha: "abc1234",
    git_branch: "main",
    summary: { total: 2, passed: status === "pass" ? 2 : 1, failed: status === "pass" ? 0 : 1 },
    results: [
      {
        case_id: "order_status",
        name: "Order status",
        status: "pass",
        error: null,
        checks: [{ name: "tools.sequence (exact)", status: "pass", message: "" }],
        diff: {
          baseline_tools: ["lookup_order"],
          actual_tools: ["lookup_order"],
          tools_changed: false,
          baseline_cost_usd: 0.0001,
          cost_usd: 0.0001,
          baseline_latency_ms: 800,
          latency_ms: 820,
          baseline_steps: 3,
          steps: 3,
          judge_score: null,
        },
        trace: trace("tr_run_1"),
      },
      {
        case_id: "refund",
        name: "Refund",
        status,
        error: null,
        checks: [{ name: "tools.sequence (exact)", status, message: "expected a, got b" }],
        diff: {
          baseline_tools: ["lookup_order"],
          actual_tools: ["issue_refund"],
          tools_changed: true,
          baseline_cost_usd: 0.0002,
          cost_usd: 0.0003,
          baseline_latency_ms: 900,
          latency_ms: 700,
          baseline_steps: 3,
          steps: 3,
          judge_score: 0.4,
        },
        trace: null,
      },
    ],
  };
}

beforeAll(async () => {
  const created = await createProject("owner-1", "test project");
  apiKey = created.apiKey;
  projectId = created.project.id;
});

describe("auth", () => {
  it("rejects requests without a valid API key", async () => {
    expect((await postTraces(req("/api/traces", { method: "POST", body: trace("t"), key: null }))).status).toBe(401);
    expect((await listRuns(req("/api/runs", { key: "ark_wrong" }))).status).toBe(401);
    // A project_id without a session is not enough.
    expect((await listTraces(req(`/api/traces?project_id=${projectId}`, { key: null }))).status).toBe(401);
  });

  it("stores only a hash of the key and enforces the free project limit", async () => {
    const db = await getDb();
    const [row] = await db.select().from(schema.projects);
    expect(row.apiKeyHash).not.toContain(apiKey);
    expect(apiKey.startsWith(row.apiKeyPrefix)).toBe(true);
    await expect(createProject("owner-1", "second")).rejects.toBeInstanceOf(LimitError);
  });
});

describe("POST /api/traces", () => {
  it("ingests an SDK trace and computes totals", async () => {
    const response = await postTraces(req("/api/traces", { method: "POST", body: trace("tr_one") }));
    expect(response.status).toBe(200);
    const json = await response.json();
    expect(json.ids).toEqual(["tr_one"]);
    expect(json.url).toContain(`/dashboard/${projectId}/traces`);

    const detail = await getTrace(req("/api/traces/tr_one"), params("tr_one"));
    const { trace: stored } = await detail.json();
    expect(stored.toolSequence).toEqual(["lookup_order"]);
    expect(stored.llmCalls).toBe(1);
    expect(stored.totalTokens).toBe(420);
    expect(stored.costUsd).toBeCloseTo(0.000072);
    expect(stored.steps).toHaveLength(2);
  });

  it("accepts a batch and is idempotent on re-upload", async () => {
    const body = { traces: [trace("tr_one"), trace("tr_two")] };
    expect((await postTraces(req("/api/traces", { method: "POST", body }))).status).toBe(200);
    const list = await (await listTraces(req("/api/traces?limit=10"))).json();
    expect(list.traces.map((t: { externalId: string }) => t.externalId).sort()).toEqual(["tr_one", "tr_two"]);
  });

  it("validates payloads", async () => {
    const bad = await postTraces(req("/api/traces", { method: "POST", body: { id: "x", steps: "nope" } }));
    expect(bad.status).toBe(422);
    expect((await bad.json()).details.length).toBeGreaterThan(0);

    const notJson = new Request(`${BASE}/api/traces`, {
      method: "POST",
      headers: { authorization: `Bearer ${apiKey}` },
      body: "{not json",
    });
    expect((await postTraces(notJson)).status).toBe(400);
  });

  it("returns 404 for unknown traces and isolates projects", async () => {
    expect((await getTrace(req("/api/traces/nope"), params("nope"))).status).toBe(404);
    const other = await createProject("owner-2", "other");
    const response = await getTrace(req("/api/traces/tr_one", { key: other.apiKey }), params("tr_one"));
    expect(response.status).toBe(404);
  });
});

describe("runs", () => {
  it("stores a run with summary counts and returns its dashboard url", async () => {
    const response = await postRun(req("/api/runs", { method: "POST", body: run("run_1", "fail") }));
    expect(response.status).toBe(200);
    const { id, url } = await response.json();
    expect(url).toContain(`/runs/${id}`);

    const { runs } = await (await listRuns(req("/api/runs"))).json();
    expect(runs).toHaveLength(1);
    expect(runs[0]).toMatchObject({ total: 2, passed: 1, failed: 1, gitBranch: "main" });
    expect(runs[0].costUsd).toBeCloseTo(0.0004);

    const detail = await (await getRun(req(`/api/runs/${id}`), params(id))).json();
    expect(detail.run.results[1].diff.actual_tools).toEqual(["issue_refund"]);
    expect((await getRun(req("/api/runs/run_1"), params("run_1"))).status).toBe(200);
    expect((await getRun(req("/api/runs/missing"), params("missing"))).status).toBe(404);
  });

  it("re-uploading a run replaces it", async () => {
    await postRun(req("/api/runs", { method: "POST", body: run("run_1", "pass") }));
    const { runs } = await (await listRuns(req("/api/runs"))).json();
    expect(runs).toHaveLength(1);
    expect(runs[0].failed).toBe(0);
  });

  it("rejects malformed runs", async () => {
    const response = await postRun(req("/api/runs", { method: "POST", body: { id: "r", results: [{}] } }));
    expect(response.status).toBe(422);
  });
});

describe("POST /api/waitlist", () => {
  it("saves an email once and validates it", async () => {
    const body = { email: "Dev@Example.com" };
    expect((await postWaitlist(req("/api/waitlist", { method: "POST", body, key: null }))).status).toBe(200);
    expect((await postWaitlist(req("/api/waitlist", { method: "POST", body, key: null }))).status).toBe(200);
    const db = await getDb();
    const rows = await db.select().from(schema.waitlist);
    expect(rows.map((r) => r.email)).toEqual(["dev@example.com"]);

    const bad = await postWaitlist(req("/api/waitlist", { method: "POST", body: { email: "nope" }, key: null }));
    expect(bad.status).toBe(422);
  });
});
