import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";

import { AppShell } from "@/components/app-shell";
import { isDemoMode } from "@/lib/api/server";

export const dynamic = "force-dynamic";

export default async function ProtectedLayout({ children }: { children: React.ReactNode }) {
  const clerkEnabled = Boolean(
    process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY && process.env.CLERK_SECRET_KEY
  );

  if (!isDemoMode && (!clerkEnabled || !process.env.CLERK_JWT_TEMPLATE_NAME?.trim())) {
    throw new Error("Live mode requires Clerk keys and CLERK_JWT_TEMPLATE_NAME.");
  }

  if (clerkEnabled) {
    const { userId } = await auth();
    if (!userId) redirect("/sign-in");
  }

  return (
    <AppShell demoMode={isDemoMode} clerkEnabled={clerkEnabled}>
      {children}
    </AppShell>
  );
}
