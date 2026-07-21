import { clerkMiddleware } from "@clerk/nextjs/server";
import { type NextFetchEvent, type NextRequest, NextResponse } from "next/server";

export default function proxy(request: NextRequest, event: NextFetchEvent) {
  const clerkConfigured = Boolean(
    process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY && process.env.CLERK_SECRET_KEY
  );

  if (!clerkConfigured) {
    const demoEnabled =
      process.env.NEXT_PUBLIC_DEMO_MODE === "true" || !process.env.API_BASE_URL;
    if (demoEnabled) return NextResponse.next();
    return new NextResponse("Authentication is required but Clerk is not configured.", {
      status: 503,
      headers: { "Cache-Control": "no-store" }
    });
  }

  return clerkMiddleware()(request, event);
}

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)"
  ]
};
