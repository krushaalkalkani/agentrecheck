import { NextResponse } from "next/server";

import { addToWaitlist } from "@/lib/data";
import { parseBody } from "@/lib/http";
import { waitlistSchema } from "@/lib/schemas";

/** POST /api/waitlist — join the Pro waitlist. Idempotent per email. */
export async function POST(request: Request) {
  const body = await parseBody(request, waitlistSchema);
  if (body.response) return body.response;
  await addToWaitlist(body.data.email, body.data.plan);
  return NextResponse.json({ ok: true });
}
