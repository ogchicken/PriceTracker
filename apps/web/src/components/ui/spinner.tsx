import { LoaderCircleIcon } from "lucide-react";

import { cn } from "@/lib/utils";

function Spinner({ className, ...props }: React.ComponentProps<"svg">) {
  return (
    <LoaderCircleIcon
      role="status"
      aria-label="Loading"
      data-slot="spinner"
      className={cn("animate-spin", className)}
      {...props}
    />
  );
}

export { Spinner };
