import { NextResponse } from "next/server";
import type { ZodType } from "zod";

export function jsonError(status: number, error: string, details?: unknown) {
  return NextResponse.json({ error, ...(details ? { details } : {}) }, { status });
}

export const unauthorized = () =>
  jsonError(401, "Missing or invalid API key. Send 'Authorization: Bearer <project api key>'.");

/** Parse and validate a JSON body. Returns either data or a ready error response. */
export async function parseBody<T>(
  request: Request,
  schema: ZodType<T>,
): Promise<{ data: T; response?: undefined } | { data?: undefined; response: NextResponse }> {
  let raw: unknown;
  try {
    raw = await request.json();
  } catch {
    return { response: jsonError(400, "Request body must be valid JSON.") };
  }
  const parsed = schema.safeParse(raw);
  if (!parsed.success) {
    const details = parsed.error.issues
      .slice(0, 10)
      .map((issue) => ({ path: issue.path.join("."), message: issue.message }));
    return { response: jsonError(422, "Invalid payload.", details) };
  }
  return { data: parsed.data };
}

export function baseUrl(request: Request): string {
  return process.env.NEXT_PUBLIC_APP_URL?.replace(/\/$/, "") ?? new URL(request.url).origin;
}
