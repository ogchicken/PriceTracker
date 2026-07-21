"use client";

import { useState, useTransition } from "react";
import { SaveIcon } from "lucide-react";
import { toast } from "sonner";

import { savePreferencesAction } from "@/app/(app)/actions";
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
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
  FieldLegend,
  FieldSet
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { Switch } from "@/components/ui/switch";
import type { PreferencesDto } from "@/lib/api/types";

export function PreferencesForm({ preferences }: { preferences: PreferencesDto }) {
  const [emailNotifications, setEmailNotifications] = useState(preferences.emailNotifications);
  const [weeklyDigest, setWeeklyDigest] = useState(preferences.weeklyDigest);
  const [minimum, setMinimum] = useState(preferences.priceDropMinimumPercent.toString());
  const [isPending, startTransition] = useTransition();

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const priceDropMinimumPercent = Number(minimum);
    if (
      !Number.isFinite(priceDropMinimumPercent) ||
      priceDropMinimumPercent < 0 ||
      priceDropMinimumPercent > 100
    ) {
      toast.error("Minimum drop must be between 0 and 100 percent.");
      return;
    }
    startTransition(async () => {
      const result = await savePreferencesAction({
        emailNotifications,
        weeklyDigest,
        priceDropMinimumPercent
      });
      if (result.ok) toast.success(result.message);
      else toast.error("Could not save preferences", { description: result.message });
    });
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Email notifications</CardTitle>
        <CardDescription>Control which PriceTracker messages arrive in your inbox.</CardDescription>
      </CardHeader>
      <CardContent>
        <form id="preferences-form" onSubmit={submit}>
          <FieldGroup>
            <FieldSet>
              <FieldLegend>Delivery</FieldLegend>
              <Field className="flex-row items-center justify-between rounded-lg border p-4">
                <div className="flex flex-col gap-1">
                  <FieldLabel htmlFor="email-notifications">Target and price-drop alerts</FieldLabel>
                  <FieldDescription>
                    Send an email when an item reaches its target or crosses your minimum drop.
                  </FieldDescription>
                </div>
                <Switch
                  id="email-notifications"
                  checked={emailNotifications}
                  onCheckedChange={setEmailNotifications}
                  aria-label="Target and price-drop email alerts"
                />
              </Field>
              <Field className="flex-row items-center justify-between rounded-lg border p-4">
                <div className="flex flex-col gap-1">
                  <FieldLabel htmlFor="weekly-digest">Weekly digest</FieldLabel>
                  <FieldDescription>
                    Receive one summary of active items and observed changes.
                  </FieldDescription>
                </div>
                <Switch
                  id="weekly-digest"
                  checked={weeklyDigest}
                  onCheckedChange={setWeeklyDigest}
                  aria-label="Weekly digest emails"
                />
              </Field>
            </FieldSet>

            <Field>
              <FieldLabel htmlFor="minimum-drop">Minimum price drop (%)</FieldLabel>
              <Input
                id="minimum-drop"
                type="number"
                min="0"
                max="100"
                step="1"
                inputMode="numeric"
                value={minimum}
                onChange={(event) => setMinimum(event.target.value)}
              />
              <FieldDescription>
                Ignore smaller changes unless the item reaches its target price.
              </FieldDescription>
            </Field>
          </FieldGroup>
        </form>
      </CardContent>
      <CardFooter>
        <Button type="submit" form="preferences-form" disabled={isPending}>
          {isPending ? <Spinner data-icon="inline-start" /> : <SaveIcon data-icon="inline-start" />}
          {isPending ? "Saving…" : "Save preferences"}
        </Button>
      </CardFooter>
    </Card>
  );
}
