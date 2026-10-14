"use client";
import { useQueries } from "@tanstack/react-query";
import { useData } from "@/hooks/use-data";
import { api } from "@/lib/api";
import type { Collection, RecordItem } from "@/types";
export function useAcademic(campusId: string) {
  const programs = useData<Collection>(
    `/campuses/${campusId}/programs?page_size=100`,
    !!campusId,
  );
  const years = useData<Collection>(
    `/campuses/${campusId}/academic-years?page_size=100`,
    !!campusId,
  );
  const levelQueries = useQueries({
    queries: (programs.data?.items || []).map((p) => ({
      queryKey: [`/programs/${p.id}/levels?page_size=100`],
      queryFn: () => api<Collection>(`/programs/${p.id}/levels?page_size=100`),
    })),
  });
  const levels: RecordItem[] = levelQueries.flatMap((q, index) =>
    (q.data?.items || []).map((l) => ({
      ...l,
      program_name: programs.data?.items[index]?.name,
    })),
  );
  const subjectQueries = useQueries({
    queries: levels.map((l) => ({
      queryKey: [`/levels/${l.id}/subjects?page_size=100`],
      queryFn: () => api<Collection>(`/levels/${l.id}/subjects?page_size=100`),
    })),
  });
  return {
    programs: programs.data?.items || [],
    years: years.data?.items || [],
    levels,
    subjects: subjectQueries.flatMap((q) => q.data?.items || []),
    error:
      programs.error ||
      years.error ||
      levelQueries.find((q) => q.error)?.error ||
      subjectQueries.find((q) => q.error)?.error,
    isPending: programs.isPending || years.isPending,
  };
}
export function options(items: RecordItem[], prefix?: string) {
  return items.map((item) => (
    <option key={item.id} value={item.id}>
      {prefix && item[prefix] ? `${item[prefix]} · ` : ""}
      {String(item.name || item.code || item.id)}
    </option>
  ));
}
