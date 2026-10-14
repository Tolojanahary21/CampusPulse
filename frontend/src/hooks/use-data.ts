"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, mutate } from "@/lib/api";
export function useData<T>(path: string, enabled = true) {
  return useQuery<T>({
    queryKey: [path],
    queryFn: () => api<T>(path),
    enabled,
  });
}
export function useAction<T = Record<string, unknown>>(
  onSuccess?: (data: T) => void,
) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({
      path,
      method = "POST",
      data,
    }: {
      path: string;
      method?: string;
      data?: unknown;
    }) => mutate<T>(path, method, data),
    onSuccess: (data) => {
      void client.invalidateQueries();
      onSuccess?.(data);
    },
  });
}
