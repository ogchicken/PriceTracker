"use client";

import { useMemo, useState } from "react";
import { format } from "date-fns";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle
} from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { PricePointDto } from "@/lib/api/types";
import { formatMoney } from "@/lib/utils";

type Range = "7" | "30" | "90" | "all";

export function PriceChart({
  data,
  targetPrice,
  currency
}: {
  data: PricePointDto[];
  targetPrice: number;
  currency: string;
}) {
  const [range, setRange] = useState<Range>("30");
  const visibleData = useMemo(() => {
    if (range === "all") return data;
    return data.slice(-Number(range));
  }, [data, range]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Price history</CardTitle>
        <CardDescription>
          Observed item price over time. The dashed line marks your current target.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        <Tabs value={range} onValueChange={(value) => setRange(value as Range)}>
          <TabsList aria-label="Price history range">
            <TabsTrigger value="7">7D</TabsTrigger>
            <TabsTrigger value="30">30D</TabsTrigger>
            <TabsTrigger value="90">90D</TabsTrigger>
            <TabsTrigger value="all">All</TabsTrigger>
          </TabsList>
        </Tabs>
        <div className="h-80 w-full" role="region" aria-label="Price history chart">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={visibleData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="priceFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="var(--chart-1)" stopOpacity={0.35} />
                  <stop offset="95%" stopColor="var(--chart-1)" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="var(--border)" strokeDasharray="4 4" vertical={false} />
              <XAxis
                dataKey="capturedAt"
                tickFormatter={(value: string) => format(new Date(value), "MMM d")}
                tick={{ fill: "var(--muted-foreground)", fontSize: 12 }}
                axisLine={false}
                tickLine={false}
                minTickGap={24}
              />
              <YAxis
                tickFormatter={(value: number) => `$${Math.round(value)}`}
                tick={{ fill: "var(--muted-foreground)", fontSize: 12 }}
                axisLine={false}
                tickLine={false}
                width={58}
                domain={["auto", "auto"]}
              />
              <Tooltip
                formatter={(value) => [formatMoney(Number(value), currency), "Price"]}
                labelFormatter={(value) => format(new Date(String(value)), "MMMM d, yyyy")}
                contentStyle={{
                  background: "var(--popover)",
                  borderColor: "var(--border)",
                  borderRadius: "var(--radius)",
                  color: "var(--popover-foreground)"
                }}
              />
              <ReferenceLine
                y={targetPrice}
                stroke="var(--chart-2)"
                strokeDasharray="6 5"
                label={{
                  value: `Target ${formatMoney(targetPrice, currency)}`,
                  fill: "var(--muted-foreground)",
                  fontSize: 11,
                  position: "insideTopRight"
                }}
              />
              <Area
                type="monotone"
                dataKey="price"
                stroke="var(--chart-1)"
                strokeWidth={2.5}
                fill="url(#priceFill)"
                isAnimationActive={false}
                activeDot={{ r: 5, fill: "var(--primary)", stroke: "var(--background)" }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
      <CardFooter className="flex-wrap text-xs text-muted-foreground">
        <span className="flex items-center gap-2">
          <span aria-hidden="true" className="size-2 rounded-full bg-chart-1" />
          Observed price
        </span>
        <span className="flex items-center gap-2">
          <span aria-hidden="true" className="h-px w-5 border-t border-dashed border-chart-2" />
          Target threshold
        </span>
      </CardFooter>
    </Card>
  );
}
