import Link from "next/link";
import { notFound } from "next/navigation";

import { Stat, Timeline, ToolSequence } from "@/components/trace-view";
import { requireUser } from "@/lib/auth";
import { getProject, getTrace } from "@/lib/data";
import { fmtCost, fmtDate, fmtMs, pretty } from "@/lib/format";
import type { Step } from "@/lib/types";

export default async function TracePage({
  params,
}: {
  params: Promise<{ projectId: string; traceId: string }>;
}) {
  const user = await requireUser();
  const { projectId, traceId } = await params;
  const project = await getProject(user.id, projectId);
  const trace = project ? await getTrace(project.id, traceId) : null;
  if (!project || !trace) notFound();
  const steps = trace.steps as Step[];

  return (
    <div className="space-y-6">
      <div>
        <Link
          href={`/dashboard/${project.id}/traces`}
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          ← All traces
        </Link>
        <h2 className="mt-2 text-xl font-semibold">{trace.name}</h2>
        <p className="font-mono text-xs text-muted-foreground">
          {trace.externalId} · {fmtDate(trace.startedAt)}
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Latency" value={fmtMs(trace.latencyMs)} />
        <Stat label="Cost" value={fmtCost(trace.costUsd)} hint={`${trace.totalTokens} tokens`} />
        <Stat label="LLM calls" value={String(trace.llmCalls)} />
        <Stat label="Tool calls" value={String(trace.toolCalls)} />
      </div>

      {trace.error ? (
        <p className="rounded-lg border border-fail/30 bg-fail/10 px-3 py-2 font-mono text-sm text-fail">
          {trace.error}
        </p>
      ) : null}

      <section className="space-y-2">
        <h3 className="text-sm font-medium">Tool sequence</h3>
        <ToolSequence tools={trace.toolSequence} />
      </section>

      <section className="space-y-2">
        <h3 className="text-sm font-medium">Timeline</h3>
        <Timeline steps={steps} startedAt={trace.startedAt} latencyMs={trace.latencyMs} />
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        {(
          [
            ["Input", trace.input],
            ["Final output", trace.output],
          ] as const
        ).map(([label, value]) => (
          <div key={label} className="space-y-2">
            <h3 className="text-sm font-medium">{label}</h3>
            <pre className="max-h-80 overflow-auto rounded-xl border bg-card p-4 font-mono text-xs leading-relaxed whitespace-pre-wrap break-words">
              {pretty(value)}
            </pre>
          </div>
        ))}
      </section>
    </div>
  );
}
