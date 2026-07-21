import Link from "next/link";
import { ArrowLeftIcon } from "lucide-react";

import { Brand } from "@/components/brand";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export function AuthShell({ children }: { children: React.ReactNode }) {
  return (
    <main className="grid min-h-screen lg:grid-cols-[0.9fr_1.1fr]">
      <section className="hidden flex-col justify-between bg-foreground p-12 text-background lg:flex">
        <Brand className="text-background" />
        <div className="flex max-w-lg flex-col gap-6">
          <Badge variant="secondary">A calmer way to watch prices</Badge>
          <p className="text-5xl font-semibold tracking-[-0.04em]">
            Make the target once. Check the dashboard when you want.
          </p>
          <p className="text-lg leading-8 text-background/70">
            Keep Amazon and eBay items, price history, and alerts together in one focused workspace.
          </p>
        </div>
        <p className="text-sm text-background/60">Your account protects your private watchlist.</p>
      </section>

      <section className="flex items-center justify-center p-4 sm:p-8">
        <div className="flex w-full max-w-md flex-col gap-6">
          <Button variant="ghost" asChild className="w-fit">
            <Link href="/">
              <ArrowLeftIcon data-icon="inline-start" aria-hidden="true" />
              Back home
            </Link>
          </Button>

          {children}
        </div>
      </section>
    </main>
  );
}
