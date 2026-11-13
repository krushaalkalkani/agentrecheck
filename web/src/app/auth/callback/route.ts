import type { EmailOtpType } from "@supabase/supabase-js";
import { NextResponse } from "next/server";

import { createSupabaseServerClient, supabaseConfigured } from "@/lib/supabase";

/** Magic-link landing: exchange the code (or token hash) for a session. */
export async function GET(request: Request) {
  const url = new URL(request.url);
  const failed = new URL("/login?error=link", url.origin);
  if (!supabaseConfigured()) return NextResponse.redirect(failed);

  const supabase = await createSupabaseServerClient();
  const code = url.searchParams.get("code");
  const tokenHash = url.searchParams.get("token_hash");
  const type = url.searchParams.get("type") as EmailOtpType | null;

  const { error } = code
    ? await supabase.auth.exchangeCodeForSession(code)
    : tokenHash && type
      ? await supabase.auth.verifyOtp({ token_hash: tokenHash, type })
      : { error: new Error("missing code") };

  return NextResponse.redirect(error ? failed : new URL("/dashboard", url.origin));
}
