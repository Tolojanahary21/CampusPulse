export const labels: Record<string, string> = {
  ACTIVE: "Actif",
  SUSPENDED: "Suspendu",
  DISABLED: "Désactivé",
  ARCHIVED: "Archivé",
  DRAFT: "Brouillon",
  PUBLISHED: "Publié",
  CAMPUS: "Établissement",
  TARGETED: "Parcours ciblés",
  PLATFORM: "Toute la plateforme",
  STUDENT: "Étudiant",
  CAMPUS_ADMIN: "Administrateur d’établissement",
  PLATFORM_ADMIN: "Administrateur de plateforme",
  CONTENT_PUBLISHER: "Responsable de publication",
  MODERATOR: "Modérateur",
  COMPLETED: "Terminé",
  CANCELLED: "Annulé",
  PENDING: "En attente",
  OPEN: "À traiter",
  RESOLVED: "Résolu",
  DISMISSED: "Classé",
  COURSE: "Cours",
  EXERCISE: "Exercices",
  CORRECTION: "Corrigé",
  EXAM: "Examen",
  SUMMARY: "Fiche",
  OTHER: "Autre",
  GENERAL: "Information",
  ADMINISTRATIVE: "Administration",
  ACADEMIC: "Pédagogie",
  EVENT: "Événement",
  URGENT: "Urgent",
  HIDDEN: "Masqué",
  REMOVED: "Retiré",
};
const englishLabels: Record<string, string> = {
  ACTIVE: "Active",
  SUSPENDED: "Suspended",
  DISABLED: "Disabled",
  ARCHIVED: "Archived",
  DRAFT: "Draft",
  PUBLISHED: "Published",
  CAMPUS: "Institution",
  TARGETED: "Selected programmes",
  PLATFORM: "Entire platform",
  STUDENT: "Student",
  CAMPUS_ADMIN: "Institution administrator",
  PLATFORM_ADMIN: "Platform administrator",
  CONTENT_PUBLISHER: "Content publisher",
  MODERATOR: "Moderator",
  COMPLETED: "Completed",
  CANCELLED: "Cancelled",
  PENDING: "Pending",
  OPEN: "Open",
  RESOLVED: "Resolved",
  DISMISSED: "Dismissed",
  COURSE: "Course",
  EXERCISE: "Exercises",
  CORRECTION: "Answer key",
  SOLUTION: "Answer key",
  EXAM: "Exam",
  SUMMARY: "Summary",
  OTHER: "Other",
  GENERAL: "Information",
  ADMINISTRATIVE: "Administration",
  ACADEMIC: "Academic",
  EVENT: "Event",
  URGENT: "Urgent",
  HIDDEN: "Hidden",
  REMOVED: "Removed",
  DELETED: "Deleted",
  VISIBLE: "Visible",
  ENDED: "Ended",
  STAFF: "Staff",
  DISCUSSION: "Discussion",
  QUESTION: "Question",
  RESOURCE: "Resource",
  SPAM: "Spam",
  HARASSMENT: "Harassment",
  INAPPROPRIATE: "Inappropriate",
  MISINFORMATION: "Misinformation",
};
Object.assign(labels, {
  SOLUTION: "Corrigé",
  DELETED: "Supprimé",
  VISIBLE: "Visible",
  ENDED: "Terminée",
  STAFF: "Personnel",
  DISCUSSION: "Discussion",
  QUESTION: "Question",
  RESOURCE: "Ressource",
  SPAM: "Spam",
  HARASSMENT: "Harcèlement",
  INAPPROPRIATE: "Inapproprié",
  MISINFORMATION: "Désinformation",
});
export function label(value: unknown, locale: "fr" | "en" = "fr") {
  const v = String(value ?? "—");
  return (locale === "en" ? englishLabels : labels)[v] ?? v;
}
export function date(
  value: unknown,
  withTime = false,
  locale: "fr" | "en" = "fr",
) {
  if (!value)
    return locale === "fr" ? "Date non renseignée" : "Date not provided";
  const d = new Date(String(value));
  if (Number.isNaN(d.getTime()))
    return locale === "fr" ? "Date non renseignée" : "Date not provided";
  return new Intl.DateTimeFormat(locale === "fr" ? "fr-FR" : "en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    ...(withTime
      ? { hour: "2-digit" as const, minute: "2-digit" as const }
      : {}),
  }).format(d);
}
export function initials(first: string, last = "") {
  return `${first?.[0] ?? ""}${last?.[0] ?? ""}`.toUpperCase() || "CP";
}
export function params(values: Record<string, unknown>) {
  const q = new URLSearchParams();
  Object.entries(values).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") q.set(k, String(v));
  });
  return q.size ? `?${q.toString()}` : "";
}
export function canRole(
  user: { roles: { role: string; campus_id: string | null }[] } | undefined,
  roles: string[],
  campusId?: string,
) {
  return !!user?.roles.some(
    (r) =>
      r.role === "PLATFORM_ADMIN" ||
      (roles.includes(r.role) && (!campusId || r.campus_id === campusId)),
  );
}
