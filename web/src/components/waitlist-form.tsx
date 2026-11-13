"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type State = "idle" | "sending" | "done" | "error";

export function WaitlistForm() {
  const [state, setState] = useState<State>("idle");

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const email = new FormData(event.currentTarget).get("email");
    setState("sending");
    try {
      const response = await fetch("/api/waitlist", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ email, plan: "pro" }),
      });
      setState(response.ok ? "done" : "error");
    } catch {
      setState("error");
    }
  }

  if (state === "done") {
    return (
      <p className="rounded-lg border border-pass/30 bg-pass/10 px-3 py-2 text-sm text-pass" role="status">
        You&apos;re on the list. We&apos;ll email you when Pro opens.
      </p>
    );
  }

  return (
    <form onSubmit={onSubmit} className="space-y-2">
      <div className="flex gap-2">
        <label htmlFor="waitlist-email" className="sr-only">
          Email address
        </label>
        <Input
          id="waitlist-email"
          name="email"
          type="email"
          required
          placeholder="you@company.com"
          autoComplete="email"
          className="h-9"
        />
        <Button type="submit" size="lg" disabled={state === "sending"}>
          {state === "sending" ? "Joining…" : "Join waitlist"}
        </Button>
      </div>
      {state === "error" ? (
        <p className="text-sm text-fail" role="alert">
          That didn&apos;t work. Check the address and try again.
        </p>
      ) : null}
    </form>
  );
}
