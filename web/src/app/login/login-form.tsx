"use client";

import { useActionState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

import { signIn, type LoginState } from "./actions";

export function LoginForm({ demo }: { demo: boolean }) {
  const [state, action, pending] = useActionState<LoginState, FormData>(signIn, null);

  if (state?.ok) {
    return (
      <p className="rounded-lg border border-pass/30 bg-pass/10 px-3 py-2 text-sm text-pass" role="status">
        {state.message}
      </p>
    );
  }

  return (
    <form action={action} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="email">Email</Label>
        <Input
          id="email"
          name="email"
          type="email"
          required
          autoFocus
          autoComplete="email"
          placeholder="you@company.com"
          className="h-9"
        />
      </div>
      {state && !state.ok ? (
        <p className="text-sm text-fail" role="alert">
          {state.message}
        </p>
      ) : null}
      <Button type="submit" size="lg" className="w-full" disabled={pending}>
        {pending ? "One moment…" : demo ? "Continue to the demo" : "Email me a sign-in link"}
      </Button>
    </form>
  );
}
