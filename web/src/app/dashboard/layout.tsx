import type { Metadata } from "next";
import Link from "next/link";

import { Logo } from "@/components/site";
import { Button, buttonVariants } from "@/components/ui/button";
import { requireUser } from "@/lib/auth";
import { supabaseConfigured } from "@/lib/supabase";

import { signOut } from "../login/actions";

export const metadata: Metadata = { title: "Dashboard" };

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  const user = await requireUser();
  const demo = !supabaseConfigured();

  return (
    <div className="flex flex-1 flex-col">
      <header className="border-b">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
          <div className="flex items-center gap-3">
            <Logo />
            <span className="text-muted-foreground">/</span>
            <Link href="/dashboard" className="text-sm hover:underline">
              Projects
            </Link>
            {demo ? (
              <span className="hidden rounded-full border border-warn/30 bg-warn/10 px-2 py-0.5 text-[11px] text-warn sm:inline">
                demo mode · local data
              </span>
            ) : null}
          </div>
          <div className="flex items-center gap-2 text-sm">
            <Link href="/docs" className={buttonVariants({ variant: "ghost", size: "sm" })}>
              Docs
            </Link>
            <span className="hidden text-muted-foreground md:inline">{user.email}</span>
            <form action={signOut}>
              <Button type="submit" variant="outline" size="sm">
                Sign out
              </Button>
            </form>
          </div>
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6">{children}</main>
    </div>
  );
}
