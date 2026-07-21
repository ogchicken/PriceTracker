import Link from "next/link";
import { ArrowLeftIcon } from "lucide-react";

import { Brand } from "@/components/brand";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle
} from "@/components/ui/card";

export interface LegalSection {
  title: string;
  paragraphs: string[];
}

export function LegalPage({
  title,
  summary,
  sections
}: {
  title: string;
  summary: string;
  sections: LegalSection[];
}) {
  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <div className="mx-auto flex h-16 max-w-5xl items-center justify-between gap-4 px-4 sm:px-6">
          <Brand />
          <Button variant="ghost" asChild>
            <Link href="/">
              <ArrowLeftIcon data-icon="inline-start" aria-hidden="true" />
              Back home
            </Link>
          </Button>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-12 sm:px-6 sm:py-20">
        <Card>
          <CardHeader className="gap-4">
            <CardTitle asChild className="text-3xl sm:text-4xl">
              <h1>{title}</h1>
            </CardTitle>
            <CardDescription className="max-w-2xl text-base leading-7">{summary}</CardDescription>
          </CardHeader>
          <CardContent className="flex max-w-3xl flex-col gap-8">
            {sections.map((section) => (
              <section key={section.title} className="flex flex-col gap-3">
                <h2 className="text-xl font-semibold">{section.title}</h2>
                {section.paragraphs.map((paragraph) => (
                  <p key={paragraph} className="leading-7 text-muted-foreground">
                    {paragraph}
                  </p>
                ))}
              </section>
            ))}
          </CardContent>
          <CardFooter className="text-sm text-muted-foreground">
            Last updated July 21, 2026.
          </CardFooter>
        </Card>
      </main>
    </div>
  );
}
