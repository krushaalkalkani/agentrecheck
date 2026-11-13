import { headers } from "next/headers";

import { CodeBlock } from "@/components/site";
import { requireUser } from "@/lib/auth";
import { countTracesThisMonth, FREE_TRACES_PER_MONTH, getProject } from "@/lib/data";

import { RotateKeyForm } from "../../key-forms";

export default async function SettingsPage({ params }: { params: Promise<{ projectId: string }> }) {
  const user = await requireUser();
  const { projectId } = await params;
  const project = await getProject(user.id, projectId);
  if (!project) return null;

  const used = await countTracesThisMonth(project.id);
  const headerList = await headers();
  const host = headerList.get("host") ?? "localhost:3000";
  const appUrl =
    process.env.NEXT_PUBLIC_APP_URL?.replace(/\/$/, "") ??
    `${host.startsWith("localhost") || host.startsWith("127.") ? "http" : "https"}://${host}`;

  return (
    <div className="max-w-2xl space-y-8">
      <section className="space-y-3">
        <h2 className="font-medium">API key</h2>
        <p className="text-sm text-muted-foreground">
          Current key starts with <code className="font-mono text-foreground">{project.apiKeyPrefix}…</code>{" "}
          Only a hash is stored, so the full key can&apos;t be shown again. Generate a new one if you
          lost it.
        </p>
        <RotateKeyForm projectId={project.id} />
      </section>

      <section className="space-y-3">
        <h2 className="font-medium">Send data to this project</h2>
        <CodeBlock title="shell">
          {`export AGENTRECHECK_API_KEY=<your key>
export AGENTRECHECK_API_URL=${appUrl}

python agent.py      # traces upload as each run finishes
agentrecheck run     # test runs upload with diffs`}
        </CodeBlock>
      </section>

      <section className="space-y-2">
        <h2 className="font-medium">Usage this month</h2>
        <div className="h-2 overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full bg-brand"
            style={{ width: `${Math.min((used / FREE_TRACES_PER_MONTH) * 100, 100)}%` }}
          />
        </div>
        <p className="font-mono text-xs text-muted-foreground">
          {used.toLocaleString("en-US")} / {FREE_TRACES_PER_MONTH.toLocaleString("en-US")} traces · Free
          plan
        </p>
      </section>
    </div>
  );
}
