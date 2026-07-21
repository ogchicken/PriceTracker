import { SearchXIcon } from "lucide-react";
import Link from "next/link";

import { Brand } from "@/components/brand";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle
} from "@/components/ui/card";

export default function NotFound() {
  return (
    <main className="flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-lg">
        <CardHeader>
          <Brand className="mb-6" />
          <span className="mb-2 flex size-11 items-center justify-center rounded-lg bg-muted text-muted-foreground">
            <SearchXIcon aria-hidden="true" className="size-5" />
          </span>
          <CardTitle asChild>
            <h1>That page isn’t tracked</h1>
          </CardTitle>
          <CardDescription>
            The link may be outdated, or the tracked item may have been removed.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm leading-6 text-muted-foreground">
            Return to the dashboard to see the items currently available in your workspace.
          </p>
        </CardContent>
        <CardFooter className="flex-wrap">
          <Button asChild>
            <Link href="/dashboard">Open dashboard</Link>
          </Button>
          <Button variant="ghost" asChild>
            <Link href="/">Go home</Link>
          </Button>
        </CardFooter>
      </Card>
    </main>
  );
}
