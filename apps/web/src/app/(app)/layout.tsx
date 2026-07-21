import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";

import { AppShell } from "@/components/app-shell";

export const dynamic = "force-dynamic";

export default async function ProtectedLayout({ children }: { children: React.ReactNode }) {
  if (!process.env.CLERK_JWT_TEMPLATE_NAME?.trim()) {
    throw new Error("CLERK_JWT_TEMPLATE_NAME is required.");
  }

  const { userId } = await auth();
  if (!userId) redirect("/sign-in");

  return <AppShell>{children}</AppShell>;
}
