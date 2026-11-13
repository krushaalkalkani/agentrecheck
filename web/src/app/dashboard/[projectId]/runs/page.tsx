import Link from "next/link";

import { RunCharts, type RunPoint } from "@/components/run-charts";
import { Stat, StatusBadge } from "@/components/trace-view";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { requireUser } from "@/lib/auth";
import { getProject, listRuns } from "@/lib/data";
import { fmtCost, fmtDate, fmtMs, fmtShortDate } from "@/lib/format";

export default async function RunsPage({ params }: { params: Promise<{ projectId: string }> }) {
  const user = await requireUser();
  const { projectId } = await params;
  const project = await getProject(user.id, projectId);
  if (!project) return null;
  const runs = await listRuns(project.id, 60);

  if (runs.length === 0) {
    return (
      <div className="rounded-xl border border-dashed p-10 text-center">
        <h2 className="font-medium">No test runs yet</h2>
        <p className="mx-auto mt-1 max-w-md text-sm text-muted-foreground">
          Run <code className="font-mono">agentrecheck run</code> locally or in CI with your API key
          set. Each run shows up here with pass/fail history and diffs against baseline.
        </p>
        <Link
          href={`/dashboard/${project.id}/settings`}
          className="mt-4 inline-block text-sm underline underline-offset-4"
        >
          Setup instructions
        </Link>
      </div>
    );
  }

  const latest = runs[0];
  const green = runs.filter((r) => r.failed === 0).length;
  const points: RunPoint[] = [...runs].reverse().map((run) => ({
    label: fmtShortDate(run.startedAt),
    passed: run.passed,
    failed: run.failed,
    costUsd: run.costUsd,
    latencyMs: run.avgLatencyMs,
  }));

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat
          label="Latest run"
          value={`${latest.passed}/${latest.total} passed`}
          hint={fmtDate(latest.startedAt)}
        />
        <Stat label="Green runs" value={`${green}/${runs.length}`} hint={`last ${runs.length} runs`} />
        <Stat label="Latest cost" value={fmtCost(latest.costUsd)} hint="all cases" />
        <Stat label="Latest avg latency" value={fmtMs(latest.avgLatencyMs)} hint="per case" />
      </div>

      <RunCharts data={points} />

      <div className="overflow-hidden rounded-xl border bg-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Run</TableHead>
              <TableHead>Result</TableHead>
              <TableHead>Branch</TableHead>
              <TableHead>Started</TableHead>
              <TableHead className="text-right">Cost</TableHead>
              <TableHead className="text-right">Avg latency</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {runs.map((run) => (
              <TableRow key={run.id}>
                <TableCell>
                  <Link
                    href={`/dashboard/${project.id}/runs/${run.id}`}
                    className="font-mono text-xs hover:underline"
                  >
                    {run.externalId}
                  </Link>
                </TableCell>
                <TableCell>
                  <span className="flex items-center gap-2">
                    <StatusBadge status={run.failed === 0 ? "pass" : "fail"} />
                    <span className="font-mono text-xs tabular-nums text-muted-foreground">
                      {run.passed}/{run.total}
                    </span>
                  </span>
                </TableCell>
                <TableCell className="font-mono text-xs text-muted-foreground">
                  {run.gitBranch ?? "—"}
                  {run.gitSha ? ` @ ${run.gitSha.slice(0, 7)}` : ""}
                </TableCell>
                <TableCell className="text-muted-foreground">{fmtDate(run.startedAt)}</TableCell>
                <TableCell className="text-right font-mono tabular-nums">{fmtCost(run.costUsd)}</TableCell>
                <TableCell className="text-right font-mono tabular-nums">
                  {fmtMs(run.avgLatencyMs)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
