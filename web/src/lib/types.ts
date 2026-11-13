/** Wire types shared with the Python SDK (see sdk-python/src/agentrecheck/models.py). */

export type RequestedToolCall = { id?: string | null; name: string; arguments?: unknown };

export type LLMStep = {
  type: "llm";
  index: number;
  provider: string;
  model: string;
  input?: unknown;
  output?: unknown;
  tool_calls: RequestedToolCall[];
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  latency_ms: number;
  started_at: string;
  error?: string | null;
};

export type ToolStep = {
  type: "tool";
  index: number;
  name: string;
  args: Record<string, unknown>;
  result?: unknown;
  error?: string | null;
  latency_ms: number;
  started_at: string;
};

export type Step = LLMStep | ToolStep;

export type TracePayload = {
  id: string;
  name: string;
  input?: unknown;
  output?: unknown;
  error?: string | null;
  started_at: string;
  latency_ms: number;
  steps: Step[];
  metadata?: Record<string, unknown>;
  total_cost_usd?: number;
  total_tokens?: number;
  llm_calls?: number;
  tool_calls?: number;
  tool_sequence?: string[];
};

export type Check = { name: string; status: "pass" | "fail" | "skip"; message: string };

export type Diff = {
  baseline_tools: string[] | null;
  actual_tools: string[];
  tools_changed: boolean;
  baseline_cost_usd: number | null;
  cost_usd: number;
  baseline_latency_ms: number | null;
  latency_ms: number;
  baseline_steps: number | null;
  steps: number;
  judge_score: number | null;
};

export type CaseResult = {
  case_id: string;
  name: string;
  status: "pass" | "fail" | "error";
  error?: string | null;
  checks: Check[];
  diff: Diff;
  trace: TracePayload | null;
};
