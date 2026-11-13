import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { bearerToken } from "./api-keys";
import { DEMO_COOKIE, DEMO_USER_ID } from "./auth-constants";
import { getProject, getProjectByApiKey } from "./data";
import type { Project } from "./db/schema";
import { createSupabaseServerClient, supabaseConfigured } from "./supabase";

export type User = { id: string; email: string };

export { DEMO_COOKIE, DEMO_USER_ID };

export async function getUser(): Promise<User | null> {
  if (supabaseConfigured()) {
    const supabase = await createSupabaseServerClient();
    const { data } = await supabase.auth.getUser();
    return data.user ? { id: data.user.id, email: data.user.email ?? "" } : null;
  }
  const email = (await cookies()).get(DEMO_COOKIE)?.value;
  return email ? { id: DEMO_USER_ID, email } : null;
}

export async function requireUser(): Promise<User> {
  const user = await getUser();
  if (!user) redirect("/login");
  return user;
}

/**
 * Resolve the project an API request is for.
 *
 * - `Authorization: Bearer ark_...` — a project API key (SDK and CI).
 * - A signed-in session plus `?project_id=` — the dashboard.
 */
export async function projectFromRequest(request: Request): Promise<Project | null> {
  const token = bearerToken(request);
  if (token) return getProjectByApiKey(token);

  const projectId = new URL(request.url).searchParams.get("project_id");
  if (!projectId) return null;
  const user = await getUser();
  return user ? getProject(user.id, projectId) : null;
}
