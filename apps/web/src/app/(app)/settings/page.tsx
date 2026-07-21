import { ExternalLinkIcon, InfoIcon, ShieldCheckIcon, UserRoundIcon } from "lucide-react";
import Link from "next/link";

import { PreferencesForm } from "@/components/preferences-form";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle
} from "@/components/ui/card";
import { Separator } from "@/components/ui/feedback";
import { getPreferences, isDemoMode } from "@/lib/api/server";

export const metadata = { title: "Settings" };

export default async function SettingsPage() {
  const result = await getPreferences();
  const clerkEnabled = Boolean(
    process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY && process.env.CLERK_SECRET_KEY
  );

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-8">
      <section className="flex flex-col gap-3">
        <Badge variant="secondary">Workspace preferences</Badge>
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Settings</h1>
        <p className="text-muted-foreground">
          Manage notification behavior and understand how this workspace is connected.
        </p>
      </section>

      {result.notice ? (
        <Alert variant="warning">
          <InfoIcon aria-hidden="true" />
          <AlertTitle>Using sample preferences</AlertTitle>
          <AlertDescription>{result.notice}</AlertDescription>
        </Alert>
      ) : null}

      <PreferencesForm preferences={result.data} />

      <Card>
        <CardHeader>
          <CardTitle>Account</CardTitle>
          <CardDescription>
            Identity and workspace security are managed through the configured sign-in provider.
          </CardDescription>
          <CardAction>
            <span className="flex size-9 items-center justify-center rounded-lg bg-accent text-accent-foreground">
              <UserRoundIcon aria-hidden="true" className="size-4" />
            </span>
          </CardAction>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="flex flex-col justify-between gap-3 rounded-lg bg-muted p-4 sm:flex-row sm:items-center">
            <div className="flex flex-col gap-1">
              <p className="text-sm font-medium">Authentication status</p>
              <p className="text-sm text-muted-foreground">
                {clerkEnabled
                  ? "Clerk is connected for this deployment."
                  : "Demo access is enabled; Clerk is not configured."}
              </p>
            </div>
            <Badge variant={clerkEnabled ? "success" : "secondary"}>
              {clerkEnabled ? "Connected" : "Demo mode"}
            </Badge>
          </div>
          <div className="flex flex-col justify-between gap-3 rounded-lg bg-muted p-4 sm:flex-row sm:items-center">
            <div className="flex flex-col gap-1">
              <p className="text-sm font-medium">Data source</p>
              <p className="text-sm text-muted-foreground">
                {isDemoMode
                  ? "Sample data is used and changes are not persisted."
                  : "Your workspace reads and writes through the server API."}
              </p>
            </div>
            <Badge variant="outline">{isDemoMode ? "Sample" : "API"}</Badge>
          </div>
        </CardContent>
        <CardFooter className="flex-wrap">
          <Button variant="outline" asChild>
            <Link href="/privacy">
              <ShieldCheckIcon data-icon="inline-start" aria-hidden="true" />
              Privacy
            </Link>
          </Button>
          <Button variant="ghost" asChild>
            <Link href="/terms">
              Terms
              <ExternalLinkIcon data-icon="inline-end" aria-hidden="true" />
            </Link>
          </Button>
        </CardFooter>
      </Card>

      <Separator />
      <p className="text-center text-xs text-muted-foreground">
        PriceTracker only exposes browser-safe environment values to client components.
      </p>
    </div>
  );
}
