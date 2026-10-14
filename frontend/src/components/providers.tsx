"use client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { PreferencesProvider } from "./preferences";
export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { staleTime: 30000, retry: 1, refetchOnWindowFocus: false },
        },
      }),
  );
  return (
    <PreferencesProvider>
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    </PreferencesProvider>
  );
}
