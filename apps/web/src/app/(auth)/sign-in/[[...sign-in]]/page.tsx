import { SignIn } from "@clerk/nextjs";

import { AuthShell } from "@/components/auth-shell";

export const metadata = { title: "Sign in" };

export default function SignInPage() {
  const clerkConfigured = Boolean(
    process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY && process.env.CLERK_SECRET_KEY
  );

  return (
    <AuthShell mode="sign-in">
      {clerkConfigured ? (
        <SignIn
          path="/sign-in"
          routing="path"
          signUpUrl="/sign-up"
          forceRedirectUrl="/dashboard"
        />
      ) : undefined}
    </AuthShell>
  );
}
