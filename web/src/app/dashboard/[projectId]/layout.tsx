import { notFound } from "next/navigation";

import { requireUser } from "@/lib/auth";
import { getProject } from "@/lib/data";

import { ProjectNav } from "./project-nav";

export default async function ProjectLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ projectId: string }>;
}) {
  const user = await requireUser();
  const { projectId } = await params;
  const project = await getProject(user.id, projectId);
  if (!project) notFound();

  return (
    <div className="space-y-6">
      <div className="space-y-4 border-b">
        <h1 className="text-2xl font-semibold tracking-tight">{project.name}</h1>
        <ProjectNav projectId={project.id} />
      </div>
      {children}
    </div>
  );
}
