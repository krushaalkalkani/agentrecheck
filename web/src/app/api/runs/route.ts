import { NextResponse } from "next/server";

import { projectFromRequest } from "@/lib/auth";
import { insertRun, listRuns } from "@/lib/data";
import { baseUrl, parseBody, unauthorized } from "@/lib/http";
import { runSchema } from "@/lib/schemas";

/** POST /api/runs — upload the result of `agentrecheck run`. */
export async function POST(request: Request) {
  const project = await projectFromRequest(request);
  if (!project) return unauthorized();

  const body = await parseBody(request, runSchema);
  if (body.response) return body.response;

  const id = await insertRun(project.id, body.data);
  return NextResponse.json({
    id,
    url: `${baseUrl(request)}/dashboard/${project.id}/runs/${id}`,
  });
}

/** GET /api/runs?limit=50 — recent test runs for the project. */
export async function GET(request: Request) {
  const project = await projectFromRequest(request);
  if (!project) return unauthorized();
  const limit = Number(new URL(request.url).searchParams.get("limit") ?? 50) || 50;
  return NextResponse.json({ runs: await listRuns(project.id, limit) });
}
