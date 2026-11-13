"use server";

import { cookies, headers } from "next/headers";
import { redirect } from "next/navigation";
import { z } from "zod";

import { DEMO_COOKIE } from "@/lib/auth-constants";
import { createSupabaseServerClient, supabaseConfigured } from "@/lib/supabase";

export type LoginState = { ok: boolean; message: string } | null;

export async function signIn(_prev: LoginState, formData: FormData): Promise<LoginState> {
  const parsed = z.email().safeParse(String(formData.get("email") ?? "").trim());
  if (!parsed.success) return { ok: false, message: "Enter a valid email address." };
  const email = parsed.data;

  if (supabaseConfigured()) {
    const headerList = await headers();
    const origin =
      process.env.NEXT_PUBLIC_APP_URL?.replace(/\/$/, "") ??
      headerList.get("origin") ??
      `https://${headerList.get("host")}`;
    const supabase = await createSupabaseServerClient();
    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: `${origin}/auth/callback` },
    });
    if (error) return { ok: false, message: "Could not send the link. Try again in a minute." };
    return { ok: true, message: `Check ${email} for a sign-in link.` };
  }

  // Demo mode: no email is sent; sign straight in to the local workspace.
  (await cookies()).set(DEMO_COOKIE, email, {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 24 * 30,
  });
  redirect("/dashboard");
}

export async function signOut() {
  if (supabaseConfigured()) {
    const supabase = await createSupabaseServerClient();
    await supabase.auth.signOut();
  }
  (await cookies()).delete(DEMO_COOKIE);
  redirect("/");
}
