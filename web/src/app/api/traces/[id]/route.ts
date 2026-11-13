import { NextResponse } from "next/server";

import { projectFromRequest } from "@/lib/auth";
import { getTrace } from "@/lib/data";
import { jsonError, unauthorized } from "@/lib/http";

/** GET /api/traces/:id — one trace with all its steps. */
export async function GET(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const project = await projectFromRequest(request);
  if (!project) return unauthorized();
  const trace = await getTrace(project.id, (await params).id);
  if (!trace) return jsonError(404, "Trace not found.");
  return NextResponse.json({ trace });
}
