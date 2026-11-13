import Link from "next/link";
import { notFound } from "next/navigation";

import { Stat, StatusBadge, Timeline, ToolDiff, ToolSequence } from "@/components/trace-view";
import { requireUser } from "@/lib/auth";
import { getProject, getRun } from "@/lib/data";
import { fmtCost, fmtDate, fmtMs, fmtPct, pctDelta, pretty } from "@/lib/format";
import type { CaseResult } from "@/lib/types";
import { cn } from "@/lib/utils";

function Delta({ actual, baseline, text }: { actual: number; baseline: number | null; text: string }) {
  const pct = pctDelta(actual, baseline);
  return (
    <div>
      <div className="font-mono text-sm tabular-nums">{text}</div>
      <div
        className={cn(
          "font-mono text-xs tabular-nums",
          pct === null || Math.abs(pct) < 5
            ? "text-muted-foreground"
            : pct > 0
              ? "text-warn"
              : "text-pass",
        )}
      >
        {pct === null ? "no baseline" : `${fmtPct(pct)} vs baseline`}
      </div>
    </div>
  );
}

function CaseCard({ result }: { result: CaseResult }) {
  const { diff } = result;
  const failed = result.status !== "pass";
  return (
    <details className="group overflow-hidden rounded-xl border bg-card" open={failed}>
      <summary className="flex cursor-pointer list-none flex-wrap items-center gap-x-6 gap-y-3 px-4 py-3 hover:bg-muted/30">
        <div className="flex min-w-48 flex-1 items-center gap-3">
          <StatusBadge status={result.status} />
          <div>
            <div className="font-mono text-sm">{result.case_id}</div>
            <div className="text-xs text-muted-foreground">{result.name}</div>
          </div>
        </div>
        <div className="w-24 text-xs">
          <div className="text-muted-foreground">Tools</div>
          <div className={cn("font-mono", diff.tools_changed ? "text-warn" : "text-muted-foreground")}>
            {diff.baseline_tools === null ? "—" : diff.tools_changed ? "changed" : "same"}
          </div>
        </div>
        <Delta actual={diff.cost_usd} baseline={diff.baseline_cost_usd} text={fmtCost(diff.cost_usd)} />
        <Delta actual={diff.latency_ms} baseline={diff.baseline_latency_ms} text={fmtMs(diff.latency_ms)} />
        <div className="w-16 text-xs">
          <div className="text-muted-foreground">Judge</div>
          <div className="font-mono tabular-nums">
            {diff.judge_score === null ? "—" : diff.judge_score.toFixed(2)}
          </div>
        </div>
      </summary>

      <div className="space-y-5 border-t p-4">
        {result.error ? (
          <p className="rounded-lg border border-fail/30 bg-fail/10 px-3 py-2 font-mono text-sm text-fail">
            agent raised: {result.error}
          </p>
        ) : null}

        <div className="grid gap-5 lg:grid-cols-2">
          <div className="space-y-2">
            <h4 className="text-sm font-medium">Checks</h4>
            <ul className="divide-y rounded-lg border text-sm">
              {result.checks.map((check, i) => (
                <li key={i} className="flex items-start gap-3 px-3 py-2">
                  <StatusBadge status={check.status} />
                  <div className="min-w-0">
                    <div className="font-mono text-xs break-all">{check.name}</div>
                    {check.message ? (
                      <div className="mt-0.5 text-xs text-muted-foreground">{check.message}</div>
                    ) : null}
                  </div>
                </li>
              ))}
              {result.checks.length === 0 ? (
                <li className="px-3 py-2 text-xs text-muted-foreground">No assertions on this case.</li>
              ) : null}
            </ul>
          </div>
          <div className="space-y-2">
            <h4 className="text-sm font-medium">Tool calls</h4>
            {diff.tools_changed && diff.baseline_tools ? (
              <ToolDiff baseline={diff.baseline_tools} actual={diff.actual_tools} />
            ) : (
              <ToolSequence tools={diff.actual_tools} />
            )}
          </div>
        </div>

        {result.trace ? (
          <>
            <div className="space-y-2">
              <h4 className="text-sm font-medium">Final output</h4>
              <pre className="max-h-48 overflow-auto rounded-lg border bg-background p-3 font-mono text-xs whitespace-pre-wrap break-words">
                {pretty(result.trace.output)}
              </pre>
            </div>
            <div className="space-y-2">
              <h4 className="text-sm font-medium">Timeline</h4>
              <Timeline
                steps={result.trace.steps}
                startedAt={result.trace.started_at}
                latencyMs={result.trace.latency_ms}
              />
            </div>
          </>
        ) : null}
      </div>
    </details>
  );
}

export default async function RunPage({
  params,
}: {
  params: Promise<{ projectId: string; runId: string }>;
}) {
  const user = await requireUser();
  const { projectId, runId } = await params;
  const project = await getProject(user.id, projectId);
  const run = project ? await getRun(project.id, runId) : null;
  if (!project || !run) notFound();

  const results = run.results as CaseResult[];
  // Regressions first.
  const ordered = [...results].sort(
    (a, b) => Number(a.status === "pass") - Number(b.status === "pass"),
  );

  return (
    <div className="space-y-6">
      <div>
        <Link
          href={`/dashboard/${project.id}/runs`}
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          ← All runs
        </Link>
        <div className="mt-2 flex flex-wrap items-center gap-3">
          <h2 className="font-mono text-xl font-semibold">{run.externalId}</h2>
          <StatusBadge status={run.failed === 0 ? "pass" : "fail"} />
        </div>
        <p className="mt-1 font-mono text-xs text-muted-foreground">
          {fmtDate(run.startedAt)}
          {run.gitBranch ? ` · ${run.gitBranch}` : ""}
          {run.gitSha ? ` @ ${run.gitSha.slice(0, 7)}` : ""}
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Passed" value={`${run.passed}/${run.total}`} />
        <Stat label="Regressions" value={String(run.failed)} />
        <Stat label="Total cost" value={fmtCost(run.costUsd)} />
        <Stat label="Avg latency" value={fmtMs(run.avgLatencyMs)} hint="per case" />
      </div>

      <div className="space-y-3">
        {ordered.map((result) => (
          <CaseCard key={result.case_id} result={result} />
        ))}
      </div>
    </div>
  );
}
