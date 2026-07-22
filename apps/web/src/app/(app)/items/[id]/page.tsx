import { formatDistanceToNow } from "date-fns";
import {
  ArrowLeftIcon,
  ArrowUpRightIcon,
  BoxIcon,
  CircleDollarSignIcon,
  Clock3Icon,
  PackageCheckIcon,
  StoreIcon,
  TargetIcon,
  TrendingDownIcon
} from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

import { ItemActions } from "@/components/item-actions";
import { PriceChart } from "@/components/price-chart";
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
import { getItem } from "@/lib/api/server";
import { formatMoney } from "@/lib/utils";

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const item = await getItem(id);
  return { title: item?.title ?? "Tracked item" };
}

export default async function ItemDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const item = await getItem(id);
  if (!item) notFound();

  const stats = [
    {
      label: "Current price",
      value: formatMoney(item.currentPrice, item.currency),
      detail: `Checked ${formatDistanceToNow(new Date(item.lastCheckedAt), { addSuffix: true })}`,
      icon: CircleDollarSignIcon
    },
    {
      label: "Target price",
      value: formatMoney(item.targetPrice, item.currency),
      detail:
        item.currentPrice <= item.targetPrice
          ? "The latest price meets your target"
          : `${formatMoney(item.currentPrice - item.targetPrice, item.currency)} to go`,
      icon: TargetIcon
    },
    {
      label: "Observed low",
      value: formatMoney(item.lowestPrice, item.currency),
      detail: "Lowest price in the stored history",
      icon: TrendingDownIcon
    }
  ];

  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-col gap-5">
        <Button variant="ghost" className="w-fit" asChild>
          <Link href="/dashboard">
            <ArrowLeftIcon data-icon="inline-start" aria-hidden="true" />
            Dashboard
          </Link>
        </Button>
        <section className="flex flex-col justify-between gap-6 lg:flex-row lg:items-start">
          <div className="flex min-w-0 gap-4">
            <span className="flex size-16 shrink-0 items-center justify-center rounded-xl bg-muted text-muted-foreground">
              <BoxIcon aria-hidden="true" className="size-7" />
            </span>
            <div className="flex min-w-0 flex-col gap-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="secondary" className="capitalize">
                  {item.store}
                </Badge>
                <Badge
                  variant={
                    item.status === "target_reached"
                      ? "success"
                      : item.status === "paused"
                        ? "secondary"
                        : "outline"
                  }
                >
                  {item.status === "target_reached"
                    ? "Target reached"
                    : item.status === "paused"
                      ? "Paused"
                      : "Tracking"}
                </Badge>
              </div>
              <h1 className="max-w-4xl text-balance text-3xl font-semibold tracking-tight sm:text-4xl">
                {item.title}
              </h1>
              <p className="text-sm text-muted-foreground">
                Added {formatDistanceToNow(new Date(item.createdAt), { addSuffix: true })}
              </p>
            </div>
          </div>
          <Button variant="outline" asChild>
            <a href={item.productUrl} target="_blank" rel="noreferrer">
              View at {item.store === "amazon" ? "Amazon" : "eBay"}
              <ArrowUpRightIcon data-icon="inline-end" aria-hidden="true" />
            </a>
          </Button>
        </section>
      </div>

      <section aria-labelledby="item-stats-heading">
        <h2 id="item-stats-heading" className="sr-only">
          Item price summary
        </h2>
        <div className="grid gap-4 md:grid-cols-3">
          {stats.map((stat) => (
            <Card key={stat.label}>
              <CardHeader>
                <CardDescription>{stat.label}</CardDescription>
                <CardTitle className="text-3xl tracking-tight">{stat.value}</CardTitle>
                <CardAction>
                  <span className="flex size-9 items-center justify-center rounded-lg bg-accent text-accent-foreground">
                    <stat.icon aria-hidden="true" className="size-4" />
                  </span>
                </CardAction>
              </CardHeader>
              <CardContent>
                <p className="text-xs leading-5 text-muted-foreground">{stat.detail}</p>
              </CardContent>
              <CardFooter>
                <Separator />
              </CardFooter>
            </Card>
          ))}
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1fr_22rem]">
        <PriceChart
          data={item.priceHistory}
          targetPrice={item.targetPrice}
          currency={item.currency}
        />
        <div className="flex flex-col gap-6">
          <ItemActions
            itemId={item.id}
            targetPrice={item.targetPrice}
            status={item.status}
            notifyBackInStock={item.notifyBackInStock}
          />
          <Card>
            <CardHeader>
              <CardTitle>Product details</CardTitle>
              <CardDescription>Context captured with the latest price check.</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-4 text-sm">
              <div className="flex items-center justify-between gap-4">
                <span className="flex items-center gap-2 text-muted-foreground">
                  <StoreIcon aria-hidden="true" className="size-4" />
                  Store
                </span>
                <span className="capitalize">{item.store}</span>
              </div>
              <Separator />
              <div className="flex items-center justify-between gap-4">
                <span className="flex items-center gap-2 text-muted-foreground">
                  <PackageCheckIcon aria-hidden="true" className="size-4" />
                  Shipping
                </span>
                <span>
                  {item.shippingPrice === null
                    ? "Not available"
                    : item.shippingPrice === 0
                      ? "Included"
                      : formatMoney(item.shippingPrice, item.currency)}
                </span>
              </div>
              <Separator />
              <div className="flex items-center justify-between gap-4">
                <span className="flex items-center gap-2 text-muted-foreground">
                  <Clock3Icon aria-hidden="true" className="size-4" />
                  Seller
                </span>
                <span className="text-right">{item.seller ?? "Not available"}</span>
              </div>
            </CardContent>
            <CardFooter className="text-xs text-muted-foreground">
              Marketplace details can change between checks.
            </CardFooter>
          </Card>
        </div>
      </section>
    </div>
  );
}
