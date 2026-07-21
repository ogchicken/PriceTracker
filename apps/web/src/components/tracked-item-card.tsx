import { formatDistanceToNow } from "date-fns";
import {
  ArrowDownRightIcon,
  ArrowRightIcon,
  BoxIcon,
  PauseIcon,
  TargetIcon
} from "lucide-react";
import Link from "next/link";

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
import type { TrackedItemSummaryDto } from "@/lib/api/types";
import { formatMoney, formatPercent } from "@/lib/utils";

function statusBadge(status: TrackedItemSummaryDto["status"]) {
  if (status === "target_reached") return <Badge variant="success">Target reached</Badge>;
  if (status === "paused") {
    return (
      <Badge variant="secondary">
        <PauseIcon aria-hidden="true" />
        Paused
      </Badge>
    );
  }
  return <Badge variant="outline">Tracking</Badge>;
}

export function TrackedItemCard({ item }: { item: TrackedItemSummaryDto }) {
  const change =
    item.previousPrice && item.previousPrice > 0
      ? (item.currentPrice - item.previousPrice) / item.previousPrice
      : 0;

  return (
    <Card className="h-full transition-shadow hover:shadow-md">
      <CardHeader>
        <div className="mb-3 flex size-12 items-center justify-center rounded-lg bg-muted text-muted-foreground">
          <BoxIcon aria-hidden="true" className="size-5" />
        </div>
        <CardTitle className="line-clamp-2 leading-6">{item.title}</CardTitle>
        <CardDescription className="capitalize">
          {item.store} · checked{" "}
          {formatDistanceToNow(new Date(item.lastCheckedAt), { addSuffix: true })}
        </CardDescription>
        <CardAction>{statusBadge(item.status)}</CardAction>
      </CardHeader>
      <CardContent className="grid grid-cols-2 gap-4">
        <div className="flex flex-col gap-1">
          <span className="text-xs text-muted-foreground">Current price</span>
          <strong className="text-2xl tracking-tight">
            {formatMoney(item.currentPrice, item.currency)}
          </strong>
          {change < 0 ? (
            <span className="flex items-center gap-1 text-xs font-medium text-primary">
              <ArrowDownRightIcon aria-hidden="true" className="size-3" />
              {formatPercent(change)} since last check
            </span>
          ) : (
            <span className="text-xs text-muted-foreground">No recent drop</span>
          )}
        </div>
        <div className="flex flex-col gap-1 rounded-lg bg-muted p-3">
          <span className="flex items-center gap-1 text-xs text-muted-foreground">
            <TargetIcon aria-hidden="true" className="size-3" />
            Target
          </span>
          <strong>{formatMoney(item.targetPrice, item.currency)}</strong>
          <span className="text-xs text-muted-foreground">
            Low {formatMoney(item.lowestPrice, item.currency)}
          </span>
        </div>
      </CardContent>
      <CardFooter>
        <Button variant="outline" className="w-full" asChild>
          <Link href={`/items/${item.id}`}>
            View details
            <ArrowRightIcon data-icon="inline-end" aria-hidden="true" />
          </Link>
        </Button>
      </CardFooter>
    </Card>
  );
}
