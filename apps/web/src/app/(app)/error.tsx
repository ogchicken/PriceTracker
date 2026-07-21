"use client";

import { AlertTriangleIcon, RefreshCwIcon } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle
} from "@/components/ui/card";

export default function AppError({
  error,
  reset
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="mx-auto flex min-h-[60vh] max-w-xl items-center">
      <Card className="w-full">
        <CardHeader>
          <span className="mb-2 flex size-11 items-center justify-center rounded-lg bg-destructive/10 text-destructive">
            <AlertTriangleIcon aria-hidden="true" className="size-5" />
          </span>
          <CardTitle asChild>
            <h1>We couldn’t load this view</h1>
          </CardTitle>
          <CardDescription>
            The problem may be temporary. Try the request again without losing your place.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Alert variant="destructive">
            <AlertTitle>Request failed</AlertTitle>
            <AlertDescription>
              {error.digest
                ? `Reference ${error.digest}`
                : "No sensitive technical details were exposed."}
            </AlertDescription>
          </Alert>
        </CardContent>
        <CardFooter>
          <Button onClick={reset}>
            <RefreshCwIcon data-icon="inline-start" aria-hidden="true" />
            Try again
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}
