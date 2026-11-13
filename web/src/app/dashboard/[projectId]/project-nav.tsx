"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

const TABS = [
  { slug: "runs", label: "Test runs" },
  { slug: "traces", label: "Traces" },
  { slug: "settings", label: "Settings" },
];

export function ProjectNav({ projectId }: { projectId: string }) {
  const pathname = usePathname();
  return (
    <nav className="-mb-px flex gap-6 text-sm" aria-label="Project sections">
      {TABS.map((tab) => {
        const href = `/dashboard/${projectId}/${tab.slug}`;
        const active = pathname.startsWith(href);
        return (
          <Link
            key={tab.slug}
            href={href}
            aria-current={active ? "page" : undefined}
            className={cn(
              "border-b-2 pb-3 transition-colors",
              active
                ? "border-brand text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground",
            )}
          >
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
