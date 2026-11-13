import Link from "next/link";

import { requireUser } from "@/lib/auth";
import { FREE_PROJECT_LIMIT, listProjects } from "@/lib/data";
import { fmtShortDate } from "@/lib/format";

import { CreateProjectForm } from "./key-forms";

export default async function ProjectsPage() {
  const user = await requireUser();
  const projects = await listProjects(user.id);
  const atLimit = projects.length >= FREE_PROJECT_LIMIT;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Projects</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          One project per agent. Each has its own API key, traces, and test runs.
        </p>
      </div>

      {projects.length > 0 ? (
        <ul className="grid gap-3 sm:grid-cols-2">
          {projects.map((project) => (
            <li key={project.id}>
              <Link
                href={`/dashboard/${project.id}/runs`}
                className="block rounded-xl border bg-card p-4 transition-colors hover:border-brand/50"
              >
                <div className="font-medium">{project.name}</div>
                <div className="mt-2 flex items-center justify-between font-mono text-xs text-muted-foreground">
                  <span>{project.apiKeyPrefix}…</span>
                  <span>created {fmtShortDate(project.createdAt)}</span>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      ) : null}

      <section className="max-w-xl space-y-3 rounded-xl border bg-card p-5">
        <h2 className="font-medium">{projects.length ? "New project" : "Create your first project"}</h2>
        {atLimit ? (
          <p className="text-sm text-muted-foreground">
            The Free plan includes {FREE_PROJECT_LIMIT} project.{" "}
            <Link href="/#pricing" className="text-foreground underline underline-offset-4">
              Join the Pro waitlist
            </Link>{" "}
            for unlimited projects.
          </p>
        ) : (
          <CreateProjectForm />
        )}
      </section>
    </div>
  );
}
