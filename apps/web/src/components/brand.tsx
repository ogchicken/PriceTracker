import Link from "next/link";
import { TrendingDownIcon } from "lucide-react";

import { cn } from "@/lib/utils";

export function Brand({
  compact = false,
  className
}: {
  compact?: boolean;
  className?: string;
}) {
  return (
    <Link
      href="/"
      aria-label="PriceTracker home"
      className={cn(
        "inline-flex items-center gap-2 rounded-md font-semibold tracking-tight focus-visible:outline-2 focus-visible:outline-ring",
        className
      )}
    >
      <span className="flex size-9 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-sm">
        <TrendingDownIcon aria-hidden="true" className="size-5" />
      </span>
      {compact ? null : <span>PriceTracker</span>}
    </Link>
  );
}
