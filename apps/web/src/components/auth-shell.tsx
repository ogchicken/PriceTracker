import Link from "next/link";
import { ArrowLeftIcon, LockKeyholeIcon } from "lucide-react";

import { Brand } from "@/components/brand";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle
} from "@/components/ui/card";

export function AuthShell({
  mode,
  children
}: {
  mode: "sign-in" | "sign-up";
  children?: React.ReactNode;
}) {
  const signingIn = mode === "sign-in";
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

          {children ?? (
            <Card>
              <CardHeader>
                <span className="mb-2 flex size-11 items-center justify-center rounded-lg bg-accent text-accent-foreground">
                  <LockKeyholeIcon aria-hidden="true" className="size-5" />
                </span>
                <CardTitle asChild>
                  <h1>{signingIn ? "Welcome back" : "Create your workspace"}</h1>
                </CardTitle>
                <CardDescription>
                  Authentication is not connected in this environment.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Alert variant="warning">
                  <AlertTitle>Demo mode is active</AlertTitle>
                  <AlertDescription>
                    You can explore the full product without entering credentials. Configure
                    Clerk environment variables to enable account sign-in.
                  </AlertDescription>
                </Alert>
              </CardContent>
              <CardFooter className="flex-col items-stretch">
                <Button asChild>
                  <Link href="/dashboard">Continue to demo dashboard</Link>
                </Button>
                <p className="text-center text-xs text-muted-foreground">
                  Demo changes are simulated and are not persisted.
                </p>
              </CardFooter>
            </Card>
          )}
        </div>
      </section>
    </main>
  );
}
