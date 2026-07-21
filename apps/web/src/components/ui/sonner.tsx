"use client";

import { LoaderCircleIcon } from "lucide-react";
import { Toaster as Sonner, type ToasterProps } from "sonner";

function Toaster(props: ToasterProps) {
  return (
    <Sonner
      theme="system"
      className="toaster group"
      icons={{
        loading: <LoaderCircleIcon aria-hidden="true" className="size-4 animate-spin" />
      }}
      toastOptions={{
        classNames: {
          toast: "group toast border-border bg-card text-card-foreground shadow-lg",
          description: "text-muted-foreground",
          actionButton: "bg-primary text-primary-foreground",
          cancelButton: "bg-muted text-muted-foreground"
        }
      }}
      {...props}
    />
  );
}

export { Toaster };
