import { fmtCost, fmtMs, pretty, sequenceDiff } from "@/lib/format";
import type { Step } from "@/lib/types";
import { cn } from "@/lib/utils";

export function StatusBadge({ status }: { status: "pass" | "fail" | "error" | "skip" }) {
  const styles = {
    pass: "border-pass/30 bg-pass/10 text-pass",
    fail: "border-fail/30 bg-fail/10 text-fail",
    error: "border-fail/30 bg-fail/10 text-fail",
    skip: "border-warn/30 bg-warn/10 text-warn",
  }[status];
  return (
    <span
      className={cn(
        "inline-flex h-5 items-center rounded-full border px-2 font-mono text-[11px] font-medium uppercase tracking-wide",
        styles,
      )}
    >
      {status}
    </span>
  );
}

export function ToolSequence({ tools }: { tools: string[] }) {
  if (tools.length === 0) return <span className="text-muted-foreground">—</span>;
  return (
    <span className="flex flex-wrap items-center gap-1 font-mono text-xs">
      {tools.map((tool, i) => (
        <span key={i} className="flex items-center gap-1">
          {i > 0 ? <span className="text-muted-foreground">→</span> : null}
          <span className="rounded bg-muted px-1.5 py-0.5">{tool}</span>
        </span>
      ))}
    </span>
  );
}

/** Baseline → current diff of a tool sequence, like a code diff. */
export function ToolDiff({ baseline, actual }: { baseline: string[]; actual: string[] }) {
  return (
    <div className="overflow-hidden rounded-lg border font-mono text-xs">
      <div className="border-b bg-muted/40 px-3 py-1.5 text-muted-foreground">
        tool sequence · baseline → current
      </div>
      {sequenceDiff(baseline, actual).map((row, i) => (
        <div
          key={i}
          className={cn(
            "flex gap-3 px-3 py-1",
            row.marker === "-" && "bg-fail/10 text-fail",
            row.marker === "+" && "bg-pass/10 text-pass",
          )}
        >
          <span className="w-2 select-none">{row.marker}</span>
          <span>{row.value}</span>
        </div>
      ))}
    </div>
  );
}

function Payload({ label, value }: { label: string; value: unknown }) {
  return (
    <div>
      <div className="mb-1 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </div>
      <pre className="max-h-72 overflow-auto rounded-md bg-background p-3 font-mono text-xs leading-relaxed whitespace-pre-wrap break-words">
        {pretty(value)}
      </pre>
    </div>
  );
}

/**
 * Waterfall timeline of a run: each LLM and tool step is a bar positioned by
 * when it started and sized by how long it took. Click a step for payloads.
 */
export function Timeline({
  steps,
  startedAt,
  latencyMs,
}: {
  steps: Step[];
  startedAt: string | Date;
  latencyMs: number;
}) {
  if (steps.length === 0) {
    return <p className="text-sm text-muted-foreground">This run recorded no steps.</p>;
  }
  const origin = new Date(startedAt).getTime();
  const total = Math.max(latencyMs, 1);

  return (
    <ol className="divide-y overflow-hidden rounded-xl border bg-card">
      {steps.map((step) => {
        const offset = Math.max(new Date(step.started_at).getTime() - origin, 0);
        const left = Math.min((offset / total) * 100, 99);
        const width = Math.max(Math.min((step.latency_ms / total) * 100, 100 - left), 1);
        const isLlm = step.type === "llm";
        const requested = isLlm ? step.tool_calls.map((c) => c.name) : [];
        return (
          <li key={step.index}>
            <details className="group">
              <summary className="grid cursor-pointer list-none grid-cols-[2rem_3.5rem_minmax(0,12rem)_1fr_4rem] items-center gap-3 px-4 py-2.5 text-sm hover:bg-muted/40">
                <span className="font-mono text-xs text-muted-foreground">{step.index + 1}</span>
                <span
                  className={cn(
                    "rounded px-1.5 py-0.5 text-center font-mono text-[11px] uppercase",
                    isLlm ? "bg-sky-400/15 text-sky-300" : "bg-violet-400/15 text-violet-300",
                  )}
                >
                  {step.type}
                </span>
                <span className="truncate font-mono text-xs">
                  {isLlm ? step.model : step.name}
                  {requested.length ? (
                    <span className="text-muted-foreground"> → {requested.join(", ")}</span>
                  ) : null}
                </span>
                <span className="relative hidden h-2 rounded-full bg-muted sm:block">
                  <span
                    className={cn(
                      "absolute inset-y-0 rounded-full",
                      step.error ? "bg-fail" : isLlm ? "bg-sky-400" : "bg-violet-400",
                    )}
                    style={{ left: `${left}%`, width: `${width}%` }}
                  />
                </span>
                <span className="text-right font-mono text-xs text-muted-foreground">
                  {fmtMs(step.latency_ms)}
                </span>
              </summary>
              <div className="grid gap-4 border-t bg-muted/20 p-4 md:grid-cols-2">
                {isLlm ? (
                  <>
                    <Payload label="Prompt" value={step.input} />
                    <div className="space-y-4">
                      <Payload
                        label={requested.length ? "Requested tool calls" : "Output"}
                        value={requested.length ? step.tool_calls : step.output}
                      />
                      <p className="font-mono text-xs text-muted-foreground">
                        {step.input_tokens} in · {step.output_tokens} out · {fmtCost(step.cost_usd)}
                      </p>
                    </div>
                  </>
                ) : (
                  <>
                    <Payload label="Arguments" value={step.args} />
                    <Payload label={step.error ? "Error" : "Result"} value={step.error ?? step.result} />
                  </>
                )}
              </div>
            </details>
          </li>
        );
      })}
    </ol>
  );
}

export function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-xl border bg-card px-4 py-3">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="mt-1 font-mono text-lg font-medium tabular-nums">{value}</div>
      {hint ? <div className="mt-0.5 text-xs text-muted-foreground">{hint}</div> : null}
    </div>
  );
}
