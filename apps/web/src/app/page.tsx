import Link from "next/link";
import {
  ArrowRightIcon,
  BellRingIcon,
  CheckIcon,
  GavelIcon,
  LineChartIcon,
  LinkIcon,
  ShieldCheckIcon,
  ShoppingBagIcon,
  SparklesIcon,
  TargetIcon
} from "lucide-react";

import { Brand } from "@/components/brand";
import { ThemeToggle } from "@/components/theme-toggle";
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
import { Separator } from "@/components/ui/feedback";

const steps = [
  {
    icon: LinkIcon,
    title: "Paste a product link",
    description: "Add a supported Amazon or eBay product URL."
  },
  {
    icon: TargetIcon,
    title: "Choose your target",
    description: "Set the price that would make the purchase worthwhile."
  },
  {
    icon: LineChartIcon,
    title: "We watch the price",
    description: "See price history and the latest observed price in one place."
  },
  {
    icon: BellRingIcon,
    title: "Know when it drops",
    description: "Get an email when the observed price reaches your target."
  }
];

const capabilities = [
  { value: "2", label: "marketplaces supported today" },
  { value: "4", label: "clear steps from link to alert" },
  { value: "1", label: "focused workspace for targets, history, and alerts" }
];

export default function LandingPage() {
  return (
    <div className="min-h-screen overflow-hidden bg-background">
      <header className="sticky top-0 z-30 border-b bg-background/90 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-6 px-4 sm:px-6 lg:px-8">
          <Brand />
          <nav aria-label="Primary navigation" className="hidden items-center gap-6 md:flex">
            <a href="#marketplaces" className="text-sm text-muted-foreground hover:text-foreground">
              Marketplaces
            </a>
            <a href="#how-it-works" className="text-sm text-muted-foreground hover:text-foreground">
              How it works
            </a>
          </nav>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <Button variant="ghost" asChild className="hidden sm:inline-flex">
              <Link href="/sign-in">Sign in</Link>
            </Button>
            <Button asChild>
              <Link href="/dashboard">
                Open tracker
                <ArrowRightIcon data-icon="inline-end" aria-hidden="true" />
              </Link>
            </Button>
          </div>
        </div>
      </header>

      <main>
        <section className="relative">
          <div
            aria-hidden="true"
            className="absolute inset-x-0 top-0 h-[34rem] bg-[radial-gradient(circle_at_50%_0%,var(--accent),transparent_68%)] opacity-70"
          />
          <div className="relative mx-auto grid max-w-7xl gap-14 px-4 py-20 sm:px-6 sm:py-28 lg:grid-cols-[1.05fr_0.95fr] lg:items-center lg:px-8 lg:py-32">
            <div className="flex flex-col items-start gap-7">
              <Badge variant="secondary">
                <SparklesIcon aria-hidden="true" />
                Less checking. Better timing.
              </Badge>
              <div className="flex flex-col gap-5">
                <h1 className="max-w-3xl text-balance text-5xl font-semibold tracking-[-0.045em] sm:text-6xl lg:text-7xl">
                  Buy when the price feels right.
                </h1>
                <p className="max-w-2xl text-pretty text-lg leading-8 text-muted-foreground sm:text-xl">
                  Track products from Amazon and eBay, set a target price, and keep a
                  clean record of every observed change.
                </p>
              </div>
              <div className="flex w-full flex-col gap-3 sm:w-auto sm:flex-row">
                <Button size="lg" asChild>
                  <Link href="/dashboard">
                    Start tracking
                    <ArrowRightIcon data-icon="inline-end" aria-hidden="true" />
                  </Link>
                </Button>
                <Button size="lg" variant="outline" asChild>
                  <a href="#how-it-works">See how it works</a>
                </Button>
              </div>
              <p className="flex items-center gap-2 text-sm text-muted-foreground">
                <ShieldCheckIcon aria-hidden="true" className="size-4 text-primary" />
                Demo mode works without an account or connected marketplace.
              </p>
            </div>

            <Card className="relative overflow-hidden shadow-xl">
              <CardHeader>
                <Badge variant="success">Target reached</Badge>
                <CardTitle className="pt-2 text-xl">Wireless mechanical keyboard</CardTitle>
                <CardDescription>Last checked moments ago · eBay</CardDescription>
                <CardAction>
                  <span className="flex size-10 items-center justify-center rounded-full bg-accent text-accent-foreground">
                    <BellRingIcon aria-hidden="true" className="size-5" />
                  </span>
                </CardAction>
              </CardHeader>
              <CardContent className="flex flex-col gap-6">
                <div className="grid grid-cols-3 gap-3">
                  <div className="flex flex-col gap-1 rounded-lg bg-muted p-3">
                    <span className="text-xs text-muted-foreground">Current</span>
                    <strong className="text-lg">$84.50</strong>
                  </div>
                  <div className="flex flex-col gap-1 rounded-lg bg-muted p-3">
                    <span className="text-xs text-muted-foreground">Target</span>
                    <strong className="text-lg">$85.00</strong>
                  </div>
                  <div className="flex flex-col gap-1 rounded-lg bg-muted p-3">
                    <span className="text-xs text-muted-foreground">Change</span>
                    <strong className="text-lg text-primary">−14.6%</strong>
                  </div>
                </div>
                <div className="relative h-40 overflow-hidden rounded-lg bg-muted/50 p-4">
                  <div className="absolute inset-x-4 top-1/2 border-t border-dashed border-primary/70" />
                  <svg
                    viewBox="0 0 500 140"
                    role="img"
                    aria-label="Illustrative product price trending down toward a target"
                    className="h-full w-full"
                  >
                    <path
                      d="M0 25 C60 22, 75 42, 130 35 S210 58, 255 52 S340 96, 390 78 S450 112, 500 105"
                      fill="none"
                      stroke="var(--chart-1)"
                      strokeWidth="5"
                      strokeLinecap="round"
                    />
                    <path
                      d="M0 25 C60 22, 75 42, 130 35 S210 58, 255 52 S340 96, 390 78 S450 112, 500 105 L500 140 L0 140 Z"
                      fill="var(--accent)"
                      opacity="0.45"
                    />
                  </svg>
                </div>
              </CardContent>
              <CardFooter>
                <CheckIcon aria-hidden="true" className="size-4 text-primary" />
                <span className="text-sm text-muted-foreground">
                  An alert would be ready to send.
                </span>
              </CardFooter>
            </Card>
          </div>
        </section>

        <section aria-label="Product capabilities" className="border-y bg-card/60">
          <div className="mx-auto grid max-w-7xl gap-8 px-4 py-10 sm:grid-cols-3 sm:px-6 lg:px-8">
            {capabilities.map((capability) => (
              <div key={capability.label} className="flex items-baseline gap-3 sm:justify-center">
                <strong className="text-3xl tracking-tight">{capability.value}</strong>
                <span className="max-w-40 text-sm leading-5 text-muted-foreground">
                  {capability.label}
                </span>
              </div>
            ))}
          </div>
        </section>

        <section id="marketplaces" className="mx-auto max-w-7xl px-4 py-24 sm:px-6 lg:px-8">
          <div className="mx-auto mb-12 flex max-w-2xl flex-col items-center gap-4 text-center">
            <Badge variant="outline">Supported stores</Badge>
            <h2 className="text-balance text-3xl font-semibold tracking-tight sm:text-4xl">
              Start with the places you already shop
            </h2>
            <p className="text-muted-foreground">
              PriceTracker currently recognizes product links from Amazon and eBay.
              Other stores are not yet supported.
            </p>
          </div>
          <div className="mx-auto grid max-w-4xl gap-6 md:grid-cols-2">
            <Card>
              <CardHeader>
                <span className="mb-3 flex size-11 items-center justify-center rounded-lg bg-secondary text-secondary-foreground">
                  <ShoppingBagIcon aria-hidden="true" className="size-5" />
                </span>
                <CardTitle>Amazon</CardTitle>
                <CardDescription>
                  Track a product page and compare the current, target, and observed low price.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Badge variant="secondary">amazon.com links</Badge>
              </CardContent>
              <CardFooter className="text-sm text-muted-foreground">
                Availability depends on product page access.
              </CardFooter>
            </Card>
            <Card>
              <CardHeader>
                <span className="mb-3 flex size-11 items-center justify-center rounded-lg bg-secondary text-secondary-foreground">
                  <GavelIcon aria-hidden="true" className="size-5" />
                </span>
                <CardTitle>eBay</CardTitle>
                <CardDescription>
                  Follow eligible listings while keeping shipping and seller context visible.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Badge variant="secondary">ebay.com links</Badge>
              </CardContent>
              <CardFooter className="text-sm text-muted-foreground">
                Listing changes and expiry can affect tracking.
              </CardFooter>
            </Card>
          </div>
        </section>

        <section id="how-it-works" className="bg-muted/45">
          <div className="mx-auto max-w-7xl px-4 py-24 sm:px-6 lg:px-8">
            <div className="mb-12 flex max-w-2xl flex-col gap-4">
              <Badge variant="outline">How it works</Badge>
              <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">
                A simple loop for smarter timing
              </h2>
              <p className="text-muted-foreground">
                Build a focused watchlist without repeatedly opening product pages.
              </p>
            </div>
            <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
              {steps.map((step, index) => (
                <Card key={step.title}>
                  <CardHeader>
                    <div className="mb-3 flex items-center justify-between gap-3">
                      <span className="flex size-10 items-center justify-center rounded-lg bg-accent text-accent-foreground">
                        <step.icon aria-hidden="true" className="size-5" />
                      </span>
                      <span className="font-mono text-xs text-muted-foreground">
                        0{index + 1}
                      </span>
                    </div>
                    <CardTitle>{step.title}</CardTitle>
                    <CardDescription>{step.description}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <Separator />
                  </CardContent>
                  <CardFooter className="text-xs text-muted-foreground">
                    Designed to stay understandable.
                  </CardFooter>
                </Card>
              ))}
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-4 py-24 sm:px-6 lg:px-8">
          <Card className="overflow-hidden bg-foreground text-background">
            <CardHeader className="gap-4 px-8 sm:px-12">
              <Badge variant="secondary">Ready when you are</Badge>
              <CardTitle className="max-w-2xl text-3xl leading-tight sm:text-4xl">
                Turn “I’ll check later” into a target you can track.
              </CardTitle>
              <CardDescription className="max-w-xl text-background/70">
                Explore the complete dashboard with realistic sample data, then connect
                authentication and the API when your environment is ready.
              </CardDescription>
            </CardHeader>
            <CardContent className="px-8 sm:px-12">
              <Button variant="secondary" size="lg" asChild>
                <Link href="/dashboard">
                  Explore the dashboard
                  <ArrowRightIcon data-icon="inline-end" aria-hidden="true" />
                </Link>
              </Button>
            </CardContent>
            <CardFooter className="px-8 text-background/60 sm:px-12">
              No purchase or savings claim is implied by the demo.
            </CardFooter>
          </Card>
        </section>
      </main>

      <footer className="border-t">
        <div className="mx-auto flex max-w-7xl flex-col gap-6 px-4 py-10 sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-8">
          <Brand />
          <nav aria-label="Legal" className="flex items-center gap-5 text-sm text-muted-foreground">
            <Link href="/privacy" className="hover:text-foreground">
              Privacy
            </Link>
            <Link href="/terms" className="hover:text-foreground">
              Terms
            </Link>
          </nav>
          <p className="text-sm text-muted-foreground">
            © {new Date().getFullYear()} PriceTracker
          </p>
        </div>
      </footer>
    </div>
  );
}
