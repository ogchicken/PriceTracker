import { formatDistanceToNow } from "date-fns";
import { ArrowRightIcon, BellIcon, BellRingIcon } from "lucide-react";
import Link from "next/link";

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
import { Empty, EmptyDescription, EmptyIcon, EmptyTitle, Separator } from "@/components/ui/feedback";
import { getNotifications } from "@/lib/api/server";
import { cn } from "@/lib/utils";

export const metadata = { title: "Notifications" };

export default async function NotificationsPage() {
  const result = await getNotifications();
  const notifications = result.data;
  const unread = notifications.filter((notification) => notification.readAt === null).length;

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-8">
      <section className="flex flex-col gap-3">
        <div className="flex items-center gap-2">
          <Badge variant="secondary">{unread} unread</Badge>
        </div>
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Notifications</h1>
        <p className="text-muted-foreground">
          Target alerts and meaningful changes from your tracked items.
        </p>
      </section>

      {result.notice ? (
        <Alert variant="warning">
          <BellIcon aria-hidden="true" />
          <AlertTitle>Live notifications unavailable</AlertTitle>
          <AlertDescription>{result.notice}</AlertDescription>
        </Alert>
      ) : null}

      {notifications.length ? (
        <Card>
          <CardHeader>
            <CardTitle>Inbox</CardTitle>
            <CardDescription>Newest events appear first.</CardDescription>
            <CardAction>
              <BellRingIcon aria-hidden="true" className="size-5 text-primary" />
            </CardAction>
          </CardHeader>
          <CardContent className="flex flex-col gap-1">
            {notifications.map((notification, index) => (
              <div key={notification.id}>
                <div className="flex items-start gap-4 rounded-lg p-3">
                  <span
                    aria-hidden="true"
                    className={cn(
                      "mt-1 size-2 shrink-0 rounded-full",
                      notification.readAt ? "bg-muted" : "bg-primary"
                    )}
                  />
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 className="font-medium">{notification.title}</h2>
                      {notification.readAt ? null : <Badge variant="secondary">New</Badge>}
                    </div>
                    <p className="mt-1 text-sm leading-6 text-muted-foreground">
                      {notification.body}
                    </p>
                    <p className="mt-2 text-xs text-muted-foreground">
                      {formatDistanceToNow(new Date(notification.createdAt), { addSuffix: true })}
                    </p>
                  </div>
                  <Button variant="ghost" size="icon-sm" asChild aria-label={`View ${notification.title}`}>
                    <Link href={`/items/${notification.itemId}`}>
                      <ArrowRightIcon data-icon="inline-end" aria-hidden="true" />
                    </Link>
                  </Button>
                </div>
                {index < notifications.length - 1 ? <Separator /> : null}
              </div>
            ))}
          </CardContent>
          <CardFooter className="text-xs text-muted-foreground">
            Email delivery follows your preferences.
          </CardFooter>
        </Card>
      ) : (
        <Empty>
          <EmptyIcon>
            <BellIcon aria-hidden="true" />
          </EmptyIcon>
          <EmptyTitle>No notifications yet</EmptyTitle>
          <EmptyDescription>
            Price drops and target alerts for your tracked items will appear here.
          </EmptyDescription>
          <Button asChild>
            <Link href="/dashboard">Return to dashboard</Link>
          </Button>
        </Empty>
      )}
    </div>
  );
}
