"use client";

import { useState, useTransition } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { PlusIcon } from "lucide-react";
import { useRouter } from "next/navigation";
import { useForm, useWatch } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { createTrackedItemAction } from "@/app/(app)/actions";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
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
  FieldError,
  FieldGroup,
  FieldLabel
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { Switch } from "@/components/ui/switch";
import { marketplaceForUrl } from "@/lib/store-url";

export function getMarketplaceSupport(value: string) {
  return marketplaceForUrl(value);
}

const addItemSchema = z.object({
  productUrl: z
    .string()
    .url("Enter a complete URL, including https://.")
    .refine(
      (value) => getMarketplaceSupport(value) !== null,
      "This store is not supported yet. Use an Amazon or eBay product link."
    ),
  targetPrice: z
    .string()
    .min(1, "Enter a target price.")
    .refine((value) => Number.isFinite(Number(value)) && Number(value) > 0, {
      message: "Enter an amount greater than zero."
    }),
  currency: z
    .string()
    .trim()
    .length(3, "Use a three-letter currency code.")
    .regex(/^[A-Za-z]{3}$/, "Use letters only."),
  notifyBackInStock: z.boolean()
});

type AddItemValues = z.infer<typeof addItemSchema>;

export function AddItemDialog({
  trigger,
  defaultOpen = false
}: {
  trigger?: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const router = useRouter();
  const [open, setOpen] = useState(defaultOpen);
  const [isPending, startTransition] = useTransition();
  const form = useForm<AddItemValues>({
    resolver: zodResolver(addItemSchema),
    defaultValues: {
      productUrl: "",
      targetPrice: "",
      currency: "USD",
      notifyBackInStock: true
    },
    mode: "onBlur"
  });

  const url = useWatch({ control: form.control, name: "productUrl" });
  const notifyBackInStock = useWatch({ control: form.control, name: "notifyBackInStock" });
  const marketplace = getMarketplaceSupport(url);

  function submit(values: AddItemValues) {
    startTransition(async () => {
      const result = await createTrackedItemAction({
        productUrl: values.productUrl,
        targetPrice: Number(values.targetPrice),
        currency: values.currency.toUpperCase(),
        notifyBackInStock: values.notifyBackInStock
      });
      if (!result.ok) {
        if (result.fieldErrors?.productUrl?.[0]) {
          form.setError("productUrl", { message: result.fieldErrors.productUrl[0] });
        }
        if (result.fieldErrors?.targetPrice?.[0]) {
          form.setError("targetPrice", { message: result.fieldErrors.targetPrice[0] });
        }
        if (result.fieldErrors?.currency?.[0]) {
          form.setError("currency", { message: result.fieldErrors.currency[0] });
        }
        toast.error("Could not add item", { description: result.message });
        return;
      }
      toast.success("Item accepted", { description: result.message });
      form.reset();
      setOpen(false);
      router.refresh();
    });
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger ?? (
          <Button>
            <PlusIcon data-icon="inline-start" aria-hidden="true" />
            Add item
          </Button>
        )}
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Track a new item</DialogTitle>
          <DialogDescription>
            Paste a supported product page and set the price you want to pay.
          </DialogDescription>
        </DialogHeader>

        <form id="add-item-form" onSubmit={form.handleSubmit(submit)} noValidate>
          <FieldGroup>
            <Field data-invalid={Boolean(form.formState.errors.productUrl)}>
              <FieldLabel htmlFor="product-url">Product URL</FieldLabel>
              <Input
                id="product-url"
                type="url"
                inputMode="url"
                autoComplete="url"
                placeholder="https://www.amazon.com/dp/..."
                aria-invalid={Boolean(form.formState.errors.productUrl)}
                aria-describedby="product-url-description product-url-error"
                {...form.register("productUrl")}
              />
              <FieldDescription id="product-url-description">
                Amazon and eBay links are currently supported.
              </FieldDescription>
              <FieldError id="product-url-error">
                {form.formState.errors.productUrl?.message}
              </FieldError>
            </Field>

            <Field data-invalid={Boolean(form.formState.errors.targetPrice)}>
              <FieldLabel htmlFor="target-price">Target price</FieldLabel>
              <Input
                id="target-price"
                type="number"
                inputMode="decimal"
                min="0.01"
                max="1000000"
                step="0.01"
                placeholder="250.00"
                aria-invalid={Boolean(form.formState.errors.targetPrice)}
                aria-describedby="target-price-description target-price-error"
                {...form.register("targetPrice")}
              />
              <FieldDescription id="target-price-description">
                We alert when item price plus mandatory shipping reaches this amount.
              </FieldDescription>
              <FieldError id="target-price-error">
                {form.formState.errors.targetPrice?.message}
              </FieldError>
            </Field>

            <Field data-invalid={Boolean(form.formState.errors.currency)}>
              <FieldLabel htmlFor="currency">Currency</FieldLabel>
              <Input
                id="currency"
                inputMode="text"
                maxLength={3}
                autoCapitalize="characters"
                aria-invalid={Boolean(form.formState.errors.currency)}
                aria-describedby="currency-description currency-error"
                {...form.register("currency")}
              />
              <FieldDescription id="currency-description">
                Use the listing currency, such as USD, EUR, GBP, or JPY.
              </FieldDescription>
              <FieldError id="currency-error">
                {form.formState.errors.currency?.message}
              </FieldError>
            </Field>

            <Field className="flex-row items-center justify-between rounded-lg border p-4">
              <div className="flex flex-col gap-1">
                <FieldLabel htmlFor="notify-back-in-stock">Notify when back in stock</FieldLabel>
                <FieldDescription>
                  Alert me if this item is out of stock now and later becomes available.
                </FieldDescription>
              </div>
              <Switch
                id="notify-back-in-stock"
                checked={notifyBackInStock}
                onCheckedChange={(checked) =>
                  form.setValue("notifyBackInStock", checked, { shouldDirty: true })
                }
                aria-label="Notify when back in stock"
              />
            </Field>

            {url && marketplace ? (
              <Alert variant="success">
                <AlertTitle>Supported {marketplace === "amazon" ? "Amazon" : "eBay"} link</AlertTitle>
                <AlertDescription>
                  The product details will be verified when you add it.
                </AlertDescription>
              </Alert>
            ) : null}
          </FieldGroup>
        </form>

        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button type="submit" form="add-item-form" disabled={isPending}>
            {isPending ? <Spinner data-icon="inline-start" /> : <PlusIcon data-icon="inline-start" />}
            {isPending ? "Adding item…" : "Start tracking"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
