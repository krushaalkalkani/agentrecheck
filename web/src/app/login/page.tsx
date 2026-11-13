import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { Logo } from "@/components/site";
import { getUser } from "@/lib/auth";
import { supabaseConfigured } from "@/lib/supabase";

import { LoginForm } from "./login-form";

export const metadata: Metadata = { title: "Sign in" };

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  if (await getUser()) redirect("/dashboard");
  const demo = !supabaseConfigured();
  const { error } = await searchParams;

  return (
    <main className="flex flex-1 items-center justify-center px-4 py-16">
      <div className="w-full max-w-sm space-y-6">
        <Logo className="justify-center text-lg" />
        <div className="space-y-5 rounded-xl border bg-card p-6">
          <div className="space-y-1">
            <h1 className="text-lg font-semibold">Sign in</h1>
            <p className="text-sm text-muted-foreground">
              {demo
                ? "Demo mode: no email is sent and data stays on this machine."
                : "We'll email you a magic link. No password needed."}
            </p>
          </div>
          {error ? (
            <p className="text-sm text-fail" role="alert">
              That sign-in link is invalid or has expired. Request a new one.
            </p>
          ) : null}
          <LoginForm demo={demo} />
        </div>
      </div>
    </main>
  );
}
