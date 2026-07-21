import * as React from "react";
import * as SeparatorPrimitive from "@radix-ui/react-separator";
import { InboxIcon } from "lucide-react";

import { cn } from "@/lib/utils";

function Skeleton({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      aria-hidden="true"
      data-slot="skeleton"
      className={cn("animate-pulse rounded-md bg-muted", className)}
      {...props}
    />
  );
}

function Separator({
  className,
  orientation = "horizontal",
  decorative = true,
  ...props
}: React.ComponentProps<typeof SeparatorPrimitive.Root>) {
  return (
    <SeparatorPrimitive.Root
      data-slot="separator"
      decorative={decorative}
      orientation={orientation}
      className={cn(
        "shrink-0 bg-border data-[orientation=horizontal]:h-px data-[orientation=horizontal]:w-full data-[orientation=vertical]:h-full data-[orientation=vertical]:w-px",
        className
      )}
      {...props}
    />
  );
}

function Empty({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="empty"
      className={cn(
        "flex min-h-56 flex-col items-center justify-center gap-4 rounded-xl border border-dashed bg-muted/20 p-8 text-center",
        className
      )}
      {...props}
    />
  );
}

function EmptyIcon({ children, className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="empty-icon"
      className={cn(
        "flex size-11 items-center justify-center rounded-full bg-secondary text-secondary-foreground [&_svg]:size-5",
        className
      )}
      {...props}
    >
      {children ?? <InboxIcon aria-hidden="true" />}
    </div>
  );
}

function EmptyTitle({ className, ...props }: React.ComponentProps<"h3">) {
  return <h3 data-slot="empty-title" className={cn("font-semibold", className)} {...props} />;
}

function EmptyDescription({ className, ...props }: React.ComponentProps<"p">) {
  return (
    <p
      data-slot="empty-description"
      className={cn("max-w-md text-sm text-muted-foreground", className)}
      {...props}
    />
  );
}

export { Empty, EmptyDescription, EmptyIcon, EmptyTitle, Separator, Skeleton };
