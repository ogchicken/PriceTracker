import { SignUp } from "@clerk/nextjs";

import { AuthShell } from "@/components/auth-shell";

export const metadata = { title: "Create account" };

export default function SignUpPage() {
  return (
    <AuthShell>
      <SignUp
        path="/sign-up"
        routing="path"
        signInUrl="/sign-in"
        forceRedirectUrl="/dashboard"
      />
    </AuthShell>
  );
}
