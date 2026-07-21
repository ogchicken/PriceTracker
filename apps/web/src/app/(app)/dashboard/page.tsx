import {
  ArrowDownRightIcon,
  BellRingIcon,
  CircleDollarSignIcon,
  PackageSearchIcon,
  PlusIcon,
  TargetIcon
} from "lucide-react";
import Link from "next/link";

import { AddItemDialog } from "@/components/add-item-dialog";
import { TrackedItemCard } from "@/components/tracked-item-card";
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
import { Empty, EmptyDescription, EmptyIcon, EmptyTitle } from "@/components/ui/feedback";
import { getDashboard } from "@/lib/api/server";
import { formatMoney } from "@/lib/utils";

export const metadata = { title: "Dashboard" };

export default async function DashboardPage() {
  const dashboard = await getDashboard();
  const metrics = [
    {
      label: "Tracked items",
      value: dashboard.trackedCount.toString(),
      detail: `${dashboard.activeCount} actively checking`,
      icon: PackageSearchIcon
    },
    {
      label: "Targets reached",
      value: dashboard.targetReachedCount.toString(),
      detail: "Based on the latest observed prices",
      icon: TargetIcon
    },
    {
      label: "Recent drops",
      value: dashboard.recentDrops.length.toString(),
      detail: "Items below their previous check",
      icon: ArrowDownRightIcon
    },
    {
      label: "Potential difference",
      value: formatMoney(dashboard.totalPotentialSavings),
      detail: "Current vs. prior observed prices",
      icon: CircleDollarSignIcon
    }
  ];

  return (
    <div className="flex flex-col gap-8">
      <section className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <Badge variant="secondary">Live workspace</Badge>
          </div>
          <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Good prices start here.</h1>
          <p className="max-w-2xl text-muted-foreground">
            Review the latest changes, then focus only on the items that need your attention.
          </p>
        </div>
        <AddItemDialog />
      </section>

      <section aria-labelledby="overview-heading">
        <h2 id="overview-heading" className="sr-only">
          Tracking overview
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {metrics.map((metric) => (
            <Card key={metric.label}>
              <CardHeader>
                <CardDescription>{metric.label}</CardDescription>
                <CardTitle className="text-3xl tracking-tight">{metric.value}</CardTitle>
                <CardAction>
                  <span className="flex size-9 items-center justify-center rounded-lg bg-accent text-accent-foreground">
                    <metric.icon aria-hidden="true" className="size-4" />
                  </span>
                </CardAction>
              </CardHeader>
              <CardContent>
                <p className="text-xs leading-5 text-muted-foreground">{metric.detail}</p>
              </CardContent>
              <CardFooter>
                <span className="h-1 w-full overflow-hidden rounded-full bg-muted">
                  <span className="block h-full w-2/3 rounded-full bg-primary" />
                </span>
              </CardFooter>
            </Card>
          ))}
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.5fr_0.8fr]">
        <div className="flex flex-col gap-4">
          <div className="flex items-end justify-between gap-4">
            <div className="flex flex-col gap-1">
              <h2 className="text-xl font-semibold">Your tracked items</h2>
              <p className="text-sm text-muted-foreground">
                Current price compared with your target and observed low.
              </p>
            </div>
            <span className="text-sm text-muted-foreground">{dashboard.items.length} items</span>
          </div>
          {dashboard.items.length ? (
            <div className="grid gap-5 md:grid-cols-2">
              {dashboard.items.map((item) => (
                <TrackedItemCard key={item.id} item={item} />
              ))}
            </div>
          ) : (
            <Empty>
              <EmptyIcon>
                <PackageSearchIcon aria-hidden="true" />
              </EmptyIcon>
              <EmptyTitle>No items tracked yet</EmptyTitle>
              <EmptyDescription>
                Add an Amazon or eBay product link and choose a target price to begin.
              </EmptyDescription>
              <AddItemDialog
                trigger={
                  <Button>
                    <PlusIcon data-icon="inline-start" aria-hidden="true" />
                    Add your first item
                  </Button>
                }
              />
            </Empty>
          )}
        </div>

        <Card className="h-fit">
          <CardHeader>
            <CardTitle>Recent price drops</CardTitle>
            <CardDescription>Changes since the previous successful check.</CardDescription>
            <CardAction>
              <BellRingIcon aria-hidden="true" className="size-5 text-primary" />
            </CardAction>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            {dashboard.recentDrops.length ? (
              dashboard.recentDrops.slice(0, 4).map((item) => (
                <Link
                  key={item.id}
                  href={`/items/${item.id}`}
                  className="flex items-center justify-between gap-4 rounded-lg p-3 transition-colors hover:bg-muted focus-visible:outline-2 focus-visible:outline-ring"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">{item.title}</p>
                    <p className="text-xs capitalize text-muted-foreground">{item.store}</p>
                  </div>
                  <div className="shrink-0 text-right">
                    <p className="text-sm font-semibold">{formatMoney(item.currentPrice, item.currency)}</p>
                    <p className="text-xs text-primary">
                      −{formatMoney((item.previousPrice ?? item.currentPrice) - item.currentPrice, item.currency)}
                    </p>
                  </div>
                </Link>
              ))
            ) : (
              <Empty className="min-h-48">
                <EmptyTitle>No recent drops</EmptyTitle>
                <EmptyDescription>New changes will appear here after checks complete.</EmptyDescription>
              </Empty>
            )}
          </CardContent>
          <CardFooter>
            <Button variant="ghost" className="w-full" asChild>
              <Link href="/notifications">View notifications</Link>
            </Button>
          </CardFooter>
        </Card>
      </section>
    </div>
  );
}
