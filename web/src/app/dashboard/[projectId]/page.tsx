import { redirect } from "next/navigation";

export default async function ProjectIndex({ params }: { params: Promise<{ projectId: string }> }) {
  redirect(`/dashboard/${(await params).projectId}/runs`);
}
