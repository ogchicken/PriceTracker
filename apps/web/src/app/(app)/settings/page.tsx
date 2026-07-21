import { ExternalLinkIcon, ShieldCheckIcon, UserRoundIcon } from "lucide-react";
import Link from "next/link";

import { PreferencesForm } from "@/components/preferences-form";
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
import { getPreferences } from "@/lib/api/server";

export const metadata = { title: "Settings" };

export default async function SettingsPage() {
  const preferences = await getPreferences();

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-8">
      <section className="flex flex-col gap-3">
        <Badge variant="secondary">Workspace preferences</Badge>
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Settings</h1>
        <p className="text-muted-foreground">
          Manage notification behavior and understand how this workspace is connected.
        </p>
      </section>

      <PreferencesForm preferences={preferences} />

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
                Clerk is connected for this deployment.
              </p>
            </div>
            <Badge variant="success">Connected</Badge>
          </div>
          <div className="flex flex-col justify-between gap-3 rounded-lg bg-muted p-4 sm:flex-row sm:items-center">
            <div className="flex flex-col gap-1">
              <p className="text-sm font-medium">Data source</p>
              <p className="text-sm text-muted-foreground">
                Your workspace reads and writes through the server API.
              </p>
            </div>
            <Badge variant="outline">API</Badge>
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
