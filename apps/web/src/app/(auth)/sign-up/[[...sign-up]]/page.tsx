import { SignUp } from "@clerk/nextjs";

import { AuthShell } from "@/components/auth-shell";

export const metadata = { title: "Create account" };

export default function SignUpPage() {
  const clerkConfigured = Boolean(
    process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY && process.env.CLERK_SECRET_KEY
  );

  return (
    <AuthShell mode="sign-up">
      {clerkConfigured ? (
        <SignUp
          path="/sign-up"
          routing="path"
          signInUrl="/sign-in"
          forceRedirectUrl="/dashboard"
        />
      ) : undefined}
    </AuthShell>
  );
}
