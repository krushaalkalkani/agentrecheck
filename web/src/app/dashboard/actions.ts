"use server";

import { revalidatePath } from "next/cache";

import { requireUser } from "@/lib/auth";
import { createProject, LimitError, rotateApiKey } from "@/lib/data";

export type KeyState = { apiKey?: string; projectId?: string; error?: string } | null;

export async function createProjectAction(_prev: KeyState, formData: FormData): Promise<KeyState> {
  const user = await requireUser();
  const name = String(formData.get("name") ?? "").trim();
  if (name.length < 2 || name.length > 60) {
    return { error: "Give the project a name between 2 and 60 characters." };
  }
  try {
    const { project, apiKey } = await createProject(user.id, name);
    revalidatePath("/dashboard");
    return { apiKey, projectId: project.id };
  } catch (error) {
    if (error instanceof LimitError) return { error: error.message };
    throw error;
  }
}

export async function rotateKeyAction(_prev: KeyState, formData: FormData): Promise<KeyState> {
  const user = await requireUser();
  const projectId = String(formData.get("projectId") ?? "");
  const apiKey = await rotateApiKey(user.id, projectId);
  if (!apiKey) return { error: "Project not found." };
  revalidatePath(`/dashboard/${projectId}/settings`);
  return { apiKey, projectId };
}
