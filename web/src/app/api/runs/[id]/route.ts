import { NextResponse } from "next/server";

import { projectFromRequest } from "@/lib/auth";
import { getRun } from "@/lib/data";
import { jsonError, unauthorized } from "@/lib/http";

/** GET /api/runs/:id — one run with per-case results and diffs. */
export async function GET(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const project = await projectFromRequest(request);
  if (!project) return unauthorized();
  const run = await getRun(project.id, (await params).id);
  if (!run) return jsonError(404, "Run not found.");
  return NextResponse.json({ run });
}
