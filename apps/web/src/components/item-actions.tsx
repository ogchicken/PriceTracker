"use client";

import { useState, useTransition } from "react";
import { PauseIcon, PlayIcon, SaveIcon, Trash2Icon } from "lucide-react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import {
  deleteTrackedItemAction,
  updateTrackedItemAction
} from "@/app/(app)/actions";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger
} from "@/components/ui/dialog";
import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { Switch } from "@/components/ui/switch";
import type { TrackingStatus } from "@/lib/api/types";

export function ItemActions({
  itemId,
  targetPrice,
  status,
  notifyBackInStock
}: {
  itemId: string;
  targetPrice: number;
  status: TrackingStatus;
  notifyBackInStock: boolean;
}) {
  const router = useRouter();
  const [target, setTarget] = useState(targetPrice.toFixed(2));
  const [backInStock, setBackInStock] = useState(notifyBackInStock);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [isPending, startTransition] = useTransition();
  const paused = status === "paused";

  function update(input: {
    targetPrice?: number;
    status?: "active" | "paused";
    notifyBackInStock?: boolean;
  }) {
    startTransition(async () => {
      const result = await updateTrackedItemAction({ id: itemId, ...input });
      if (result.ok) {
        toast.success(result.message);
        router.refresh();
      } else {
        toast.error("Update failed", { description: result.message });
      }
    });
  }

  function toggleBackInStock(checked: boolean) {
    setBackInStock(checked);
    startTransition(async () => {
      const result = await updateTrackedItemAction({ id: itemId, notifyBackInStock: checked });
      if (result.ok) {
        toast.success(result.message);
        router.refresh();
      } else {
        setBackInStock(!checked);
        toast.error("Update failed", { description: result.message });
      }
    });
  }

  function remove() {
    startTransition(async () => {
      const result = await deleteTrackedItemAction(itemId);
      if (result.ok) {
        toast.success(result.message);
        setDeleteOpen(false);
        router.push("/dashboard");
      } else {
        toast.error("Delete failed", { description: result.message });
      }
    });
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Tracking controls</CardTitle>
        <CardDescription>Change the target, pause checks, or remove this item.</CardDescription>
      </CardHeader>
      <CardContent>
        <form
          id="target-price-form"
          onSubmit={(event) => {
            event.preventDefault();
            const value = Number(target);
            if (!Number.isFinite(value) || value <= 0) {
              toast.error("Enter a target price greater than zero.");
              return;
            }
            update({ targetPrice: value });
          }}
        >
          <FieldGroup>
            <Field>
              <FieldLabel htmlFor="item-target-price">Target price (USD)</FieldLabel>
              <div className="relative">
                <span
                  aria-hidden="true"
                  className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-sm text-muted-foreground"
                >
                  $
                </span>
                <Input
                  id="item-target-price"
                  type="number"
                  min="0.01"
                  max="1000000"
                  step="0.01"
                  inputMode="decimal"
                  className="pl-7"
                  value={target}
                  onChange={(event) => setTarget(event.target.value)}
                />
              </div>
              <FieldDescription>Alerts use this threshold on future checks.</FieldDescription>
            </Field>
          </FieldGroup>
        </form>

        <Field className="mt-6 flex-row items-center justify-between rounded-lg border p-4">
          <div className="flex flex-col gap-1">
            <FieldLabel htmlFor="notify-back-in-stock">Back-in-stock alerts</FieldLabel>
            <FieldDescription>Notify me when this item returns to stock.</FieldDescription>
          </div>
          <Switch
            id="notify-back-in-stock"
            checked={backInStock}
            disabled={isPending}
            onCheckedChange={toggleBackInStock}
            aria-label="Back-in-stock alerts"
          />
        </Field>
      </CardContent>
      <CardFooter className="flex-wrap">
        <Button type="submit" form="target-price-form" disabled={isPending}>
          {isPending ? <Spinner data-icon="inline-start" /> : <SaveIcon data-icon="inline-start" />}
          Save target
        </Button>
        <Button
          type="button"
          variant="outline"
          disabled={isPending}
          onClick={() => update({ status: paused ? "active" : "paused" })}
        >
          {paused ? (
            <PlayIcon data-icon="inline-start" aria-hidden="true" />
          ) : (
            <PauseIcon data-icon="inline-start" aria-hidden="true" />
          )}
          {paused ? "Resume" : "Pause"}
        </Button>

        <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
          <DialogTrigger asChild>
            <Button type="button" variant="ghost" className="sm:ml-auto">
              <Trash2Icon data-icon="inline-start" aria-hidden="true" />
              Delete
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Delete tracked item?</DialogTitle>
              <DialogDescription>
                This removes the item and its stored price history from your workspace. This
                action cannot be undone.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setDeleteOpen(false)}>
                Keep item
              </Button>
              <Button type="button" variant="destructive" disabled={isPending} onClick={remove}>
                {isPending ? (
                  <Spinner data-icon="inline-start" />
                ) : (
                  <Trash2Icon data-icon="inline-start" aria-hidden="true" />
                )}
                Delete item
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </CardFooter>
    </Card>
  );
}
