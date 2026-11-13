import { NextResponse } from "next/server";

import { projectFromRequest } from "@/lib/auth";
import { insertTraces, LimitError, listTraces } from "@/lib/data";
import { baseUrl, jsonError, parseBody, unauthorized } from "@/lib/http";
import { tracesBodySchema } from "@/lib/schemas";

/** POST /api/traces — ingest one trace, or `{ "traces": [...] }` (max 100). */
export async function POST(request: Request) {
  const project = await projectFromRequest(request);
  if (!project) return unauthorized();

  const body = await parseBody(request, tracesBodySchema);
  if (body.response) return body.response;

  try {
    const ids = await insertTraces(project.id, body.data);
    return NextResponse.json({
      ids,
      url: `${baseUrl(request)}/dashboard/${project.id}/traces`,
    });
  } catch (error) {
    if (error instanceof LimitError) return jsonError(429, error.message);
    throw error;
  }
}

/** GET /api/traces?limit=50 — recent traces for the project. */
export async function GET(request: Request) {
  const project = await projectFromRequest(request);
  if (!project) return unauthorized();
  const limit = Number(new URL(request.url).searchParams.get("limit") ?? 50) || 50;
  return NextResponse.json({ traces: await listTraces(project.id, limit) });
}
