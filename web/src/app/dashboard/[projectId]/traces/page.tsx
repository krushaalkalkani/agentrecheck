import Link from "next/link";

import { ToolSequence } from "@/components/trace-view";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { requireUser } from "@/lib/auth";
import { getProject, listTraces } from "@/lib/data";
import { fmtCost, fmtDate, fmtMs } from "@/lib/format";

export default async function TracesPage({ params }: { params: Promise<{ projectId: string }> }) {
  const user = await requireUser();
  const { projectId } = await params;
  const project = await getProject(user.id, projectId);
  if (!project) return null;
  const traces = await listTraces(project.id, 100);

  if (traces.length === 0) {
    return (
      <div className="rounded-xl border border-dashed p-10 text-center">
        <h2 className="font-medium">No traces yet</h2>
        <p className="mx-auto mt-1 max-w-md text-sm text-muted-foreground">
          Set <code className="font-mono">AGENTRECHECK_API_KEY</code> and{" "}
          <code className="font-mono">AGENTRECHECK_API_URL</code>, then run your{" "}
          <code className="font-mono">@trace</code>-decorated agent. Runs appear here as they finish.
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

  return (
    <div className="overflow-hidden rounded-xl border bg-card">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Trace</TableHead>
            <TableHead>Started</TableHead>
            <TableHead>Tool sequence</TableHead>
            <TableHead className="text-right">Steps</TableHead>
            <TableHead className="text-right">Cost</TableHead>
            <TableHead className="text-right">Latency</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {traces.map((trace) => (
            <TableRow key={trace.id}>
              <TableCell>
                <Link
                  href={`/dashboard/${project.id}/traces/${trace.id}`}
                  className="font-medium hover:underline"
                >
                  {trace.name}
                </Link>
                <div className="font-mono text-xs text-muted-foreground">
                  {trace.externalId}
                  {trace.error ? <span className="ml-2 text-fail">error</span> : null}
                </div>
              </TableCell>
              <TableCell className="text-muted-foreground">{fmtDate(trace.startedAt)}</TableCell>
              <TableCell>
                <ToolSequence tools={trace.toolSequence} />
              </TableCell>
              <TableCell className="text-right font-mono tabular-nums">
                {trace.llmCalls + trace.toolCalls}
              </TableCell>
              <TableCell className="text-right font-mono tabular-nums">{fmtCost(trace.costUsd)}</TableCell>
              <TableCell className="text-right font-mono tabular-nums">{fmtMs(trace.latencyMs)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
