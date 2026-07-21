"use client";

import { useState } from "react";
import { UserButton } from "@clerk/nextjs";
import {
  BellIcon,
  LayoutDashboardIcon,
  MenuIcon,
  PlusIcon,
  SettingsIcon
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { AddItemDialog } from "@/components/add-item-dialog";
import { Brand } from "@/components/brand";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger
} from "@/components/ui/sheet";
import { Separator } from "@/components/ui/feedback";
import { cn } from "@/lib/utils";

const navigation = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboardIcon },
  { href: "/notifications", label: "Notifications", icon: BellIcon },
  { href: "/settings", label: "Settings", icon: SettingsIcon }
];

function Navigation({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  return (
    <nav aria-label="Application navigation" className="flex flex-col gap-1">
      {navigation.map((item) => {
        const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            aria-current={active ? "page" : undefined}
            className={cn(
              "flex h-10 items-center gap-3 rounded-lg px-3 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-ring",
              active
                ? "bg-accent text-accent-foreground"
                : "text-muted-foreground hover:bg-accent/60 hover:text-foreground"
            )}
          >
            <item.icon aria-hidden="true" className="size-4" />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="min-h-screen bg-background">
      <aside className="fixed inset-y-0 left-0 hidden w-64 flex-col border-r border-sidebar-border bg-sidebar p-4 text-sidebar-foreground lg:flex">
        <Brand className="px-2" />
        <div className="mt-8 flex flex-1 flex-col gap-5">
          <AddItemDialog
            trigger={
              <Button className="w-full">
                <PlusIcon data-icon="inline-start" aria-hidden="true" />
                Add item
              </Button>
            }
          />
          <Navigation />
        </div>
        <div className="flex flex-col gap-4">
          <Separator />
          <div className="flex items-center gap-3 rounded-lg p-2">
            <UserButton />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">Your account</p>
              <p className="truncate text-xs text-muted-foreground">Manage with Clerk</p>
            </div>
          </div>
        </div>
      </aside>

      <div className="lg:pl-64">
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between gap-4 border-b bg-background/90 px-4 backdrop-blur-md sm:px-6 lg:px-8">
          <div className="flex items-center gap-3 lg:hidden">
            <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
              <SheetTrigger asChild>
                <Button variant="ghost" size="icon" aria-label="Open navigation">
                  <MenuIcon data-icon="inline-start" aria-hidden="true" />
                </Button>
              </SheetTrigger>
              <SheetContent side="left" className="flex flex-col gap-6">
                <SheetHeader>
                  <SheetTitle>PriceTracker navigation</SheetTitle>
                  <SheetDescription>Navigate your tracking workspace.</SheetDescription>
                </SheetHeader>
                <div className="flex flex-col gap-6">
                  <Brand />
                  <AddItemDialog
                    trigger={
                      <Button className="w-full">
                        <PlusIcon data-icon="inline-start" aria-hidden="true" />
                        Add item
                      </Button>
                    }
                  />
                  <Navigation onNavigate={() => setMobileOpen(false)} />
                </div>
              </SheetContent>
            </Sheet>
            <Brand compact />
          </div>
          <p className="hidden text-sm text-muted-foreground lg:block">
            Keep an eye on the price, not the product page.
          </p>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <Button variant="ghost" size="icon" asChild aria-label="Notifications">
              <Link href="/notifications">
                <BellIcon data-icon="inline-start" aria-hidden="true" />
              </Link>
            </Button>
            <span className="lg:hidden">
              <UserButton />
            </span>
          </div>
        </header>
        <main className="mx-auto w-full max-w-[100rem] p-4 sm:p-6 lg:p-8">{children}</main>
      </div>
    </div>
  );
}
