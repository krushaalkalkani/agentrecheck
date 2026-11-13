"use client";

import Link from "next/link";
import { useActionState, useState } from "react";

import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

import { createProjectAction, rotateKeyAction, type KeyState } from "./actions";

/** Shows a freshly minted API key exactly once, with a copy button. */
function RevealedKey({ apiKey }: { apiKey: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <div className="space-y-2 rounded-lg border border-brand/30 bg-brand/5 p-3">
      <p className="text-sm font-medium">Copy your API key now. It won&apos;t be shown again.</p>
      <div className="flex gap-2">
        <code className="flex-1 overflow-x-auto rounded-md bg-background px-3 py-2 font-mono text-xs whitespace-nowrap">
          {apiKey}
        </code>
        <Button
          type="button"
          variant="outline"
          onClick={async () => {
            await navigator.clipboard.writeText(apiKey);
            setCopied(true);
          }}
        >
          {copied ? "Copied" : "Copy"}
        </Button>
      </div>
    </div>
  );
}

export function CreateProjectForm() {
  const [state, action, pending] = useActionState<KeyState, FormData>(createProjectAction, null);

  if (state?.apiKey && state.projectId) {
    return (
      <div className="space-y-3">
        <RevealedKey apiKey={state.apiKey} />
        <Link href={`/dashboard/${state.projectId}/settings`} className={buttonVariants({ size: "lg" })}>
          Continue to setup
        </Link>
      </div>
    );
  }

  return (
    <form action={action} className="space-y-3">
      <div className="space-y-2">
        <Label htmlFor="project-name">Project name</Label>
        <div className="flex gap-2">
          <Input
            id="project-name"
            name="name"
            required
            minLength={2}
            maxLength={60}
            placeholder="support-agent"
            className="h-9"
          />
          <Button type="submit" size="lg" disabled={pending}>
            {pending ? "Creating…" : "Create project"}
          </Button>
        </div>
      </div>
      {state?.error ? (
        <p className="text-sm text-fail" role="alert">
          {state.error}{" "}
          <Link href="/#pricing" className="underline underline-offset-4">
            See plans
          </Link>
        </p>
      ) : null}
    </form>
  );
}

export function RotateKeyForm({ projectId }: { projectId: string }) {
  const [state, action, pending] = useActionState<KeyState, FormData>(rotateKeyAction, null);
  return (
    <div className="space-y-3">
      {state?.apiKey ? <RevealedKey apiKey={state.apiKey} /> : null}
      {state?.error ? (
        <p className="text-sm text-fail" role="alert">
          {state.error}
        </p>
      ) : null}
      <form
        action={action}
        onSubmit={(event) => {
          if (!confirm("Generate a new key? The current key stops working immediately.")) {
            event.preventDefault();
          }
        }}
      >
        <input type="hidden" name="projectId" value={projectId} />
        <Button type="submit" variant="outline" disabled={pending}>
          {pending ? "Generating…" : "Generate new key"}
        </Button>
      </form>
    </div>
  );
}
