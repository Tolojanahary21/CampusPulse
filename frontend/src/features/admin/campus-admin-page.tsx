"use client";
import { useState } from "react";
import { usePreferences } from "@/components/preferences";
import { useSession } from "@/components/app-shell";
import { Empty, PageTitle, Tabs } from "@/components/ui";
import { AcademicAdmin, EnrollmentAdmin } from "./academic-admin";
import { CampusUsers } from "./campus-users";
import { Moderation } from "./moderation";
import { Settings } from "./settings";
export function CampusAdminPage() {
  const { t } = usePreferences();
  const { campusId, canManage, canModerate, campuses } = useSession();
  const [selected, setSelected] = useState("academic");
  const tab = canManage ? selected : "moderation";
  if (!canManage && !canModerate)
    return (
      <Empty
        title={t(
          "Cet espace est réservé à l’administration",
          "This area is for administrators",
        )}
        description={t(
          "Votre compte ne dispose pas des permissions pour gérer cet établissement.",
          "Your account does not have permission to manage this campus.",
        )}
      />
    );
  return (
    <>
      <PageTitle
        eyebrow={t(
          "ADMINISTRATION DE L’ÉTABLISSEMENT",
          "CAMPUS ADMINISTRATION",
        )}
        title={
          campuses.find((c) => c.id === campusId)?.name ||
          t("Mon établissement", "My campus")
        }
        description={t(
          "Organisez les parcours, accompagnez les membres et faites vivre votre établissement.",
          "Organize programs, support members and bring your campus to life.",
        )}
      />
      {!campusId ? (
        <Empty
          title={t("Sélectionnez un établissement", "Select a campus")}
          description={t(
            "Créez d’abord un établissement depuis l’espace plateforme.",
            "First create a campus in the platform administration area.",
          )}
        />
      ) : (
        <>
          <Tabs
            value={tab}
            onChange={setSelected}
            items={[
              ...(canManage
                ? [
                    {
                      id: "academic",
                      label: t("Structure académique", "Academic structure"),
                    },
                    { id: "users", label: t("Membres", "Members") },
                    {
                      id: "enrollments",
                      label: t("Inscriptions", "Enrollments"),
                    },
                  ]
                : []),
              { id: "moderation", label: t("Modération", "Moderation") },
              ...(canManage
                ? [{ id: "settings", label: t("Paramètres", "Settings") }]
                : []),
            ]}
          />
          {tab === "academic" && <AcademicAdmin key={campusId} />}{" "}
          {tab === "users" && <CampusUsers key={campusId} />}{" "}
          {tab === "enrollments" && <EnrollmentAdmin key={campusId} />}{" "}
          {tab === "moderation" && <Moderation key={campusId} />}{" "}
          {tab === "settings" && (
            <Settings path={`/campuses/${campusId}/settings`} key={campusId} />
          )}
        </>
      )}
    </>
  );
}
