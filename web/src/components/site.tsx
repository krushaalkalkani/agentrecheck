import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export const GITHUB_URL =
  process.env.NEXT_PUBLIC_GITHUB_URL ?? "https://github.com/your-org/agentrecheck";

export function Logo({ className }: { className?: string }) {
  return (
    <Link href="/" className={cn("flex items-center gap-2 font-semibold tracking-tight", className)}>
      <svg viewBox="0 0 24 24" className="size-5 text-brand" fill="none" aria-hidden>
        <path
          d="M20 12a8 8 0 1 1-2.6-5.9"
          stroke="currentColor"
          strokeWidth="2.2"
          strokeLinecap="round"
        />
        <path
          d="m8.5 12 2.6 2.6L20 5.8"
          stroke="currentColor"
          strokeWidth="2.2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      AgentRecheck
    </Link>
  );
}

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 border-b bg-background/80 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Logo />
        <nav className="flex items-center gap-1 text-sm">
          <Link href="/docs" className={buttonVariants({ variant: "ghost", size: "sm" })}>
            Docs
          </Link>
          <Link
            href="/#pricing"
            className={cn(buttonVariants({ variant: "ghost", size: "sm" }), "hidden sm:inline-flex")}
          >
            Pricing
          </Link>
          <a
            href={GITHUB_URL}
            className={cn(buttonVariants({ variant: "ghost", size: "sm" }), "hidden sm:inline-flex")}
          >
            GitHub
          </a>
          <Link href="/dashboard" className={cn(buttonVariants({ size: "sm" }), "ml-2")}>
            Dashboard
          </Link>
        </nav>
      </div>
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer className="border-t">
      <div className="mx-auto flex max-w-6xl flex-col items-start justify-between gap-4 px-4 py-8 text-sm text-muted-foreground sm:flex-row sm:items-center sm:px-6">
        <Logo className="text-foreground" />
        <div className="flex flex-wrap gap-x-6 gap-y-2">
          <Link href="/docs" className="hover:text-foreground">
            Docs
          </Link>
          <a href={GITHUB_URL} className="hover:text-foreground">
            GitHub
          </a>
          <Link href="/#pricing" className="hover:text-foreground">
            Pricing
          </Link>
          <span>MIT-licensed SDK</span>
        </div>
      </div>
    </footer>
  );
}

/** A code sample with an optional file-name tab. */
export function CodeBlock({
  title,
  children,
  className,
}: {
  title?: string;
  children: string;
  className?: string;
}) {
  return (
    <div className={cn("overflow-hidden rounded-xl border bg-card", className)}>
      {title ? (
        <div className="border-b px-4 py-2 font-mono text-xs text-muted-foreground">{title}</div>
      ) : null}
      <pre className="overflow-x-auto p-4 font-mono text-[13px] leading-relaxed text-foreground/90">
        <code>{children}</code>
      </pre>
    </div>
  );
}
