import { Suspense } from "react";
import { AuthForm } from "@/features/auth/auth-form";
import { Loading } from "@/components/ui";

export default function Page() {
  return (
    <Suspense fallback={<Loading />}>
      <AuthForm mode="register" />
    </Suspense>
  );
}
