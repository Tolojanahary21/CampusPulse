"use client";
import { useState } from "react";
import { usePreferences } from "@/components/preferences";
import { Button, ErrorNotice, Field, Loading, Success } from "@/components/ui";
import { useAction, useData } from "@/hooks/use-data";
export function Settings({
  path,
  platform = false,
}: {
  path: string;
  platform?: boolean;
}) {
  const { t } = usePreferences();
  const { data, error, isPending } = useData<Record<string, unknown>>(path);
  const [saved, setSaved] = useState(false);
  const action = useAction(() => setSaved(true));
  if (isPending) return <Loading />;
  return (
    <div className="panel">
      <div className="panel-header">
        <h2>
          {platform
            ? t("Paramètres de la plateforme", "Platform settings")
            : t("Paramètres de l’établissement", "Campus settings")}
        </h2>
      </div>
      <div className="panel-body">
        <ErrorNotice error={error || action.error} />
        {saved && (
          <Success>
            {t(
              "Les paramètres ont été enregistrés.",
              "Your settings have been saved.",
            )}
          </Success>
        )}
        {data && (
          <form
            key={JSON.stringify(data)}
            onSubmit={(e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              setSaved(false);
              const body = platform
                ? {
                    platform_name: f.get("platform_name"),
                    support_email: f.get("support_email") || null,
                    maintenance_message: f.get("maintenance_message") || null,
                  }
                : {
                    allow_announcement_comments:
                      f.get("allow_announcement_comments") === "on",
                    allow_student_posts: f.get("allow_student_posts") === "on",
                    allow_student_comments:
                      f.get("allow_student_comments") === "on",
                    allow_student_reactions:
                      f.get("allow_student_reactions") === "on",
                    max_upload_size_mb: Number(f.get("max_upload_size_mb")),
                  };
              action.mutate({ path, method: "PATCH", data: body });
            }}
          >
            {platform ? (
              <>
                <Field label={t("Nom de la plateforme", "Platform name")}>
                  <input
                    name="platform_name"
                    required
                    defaultValue={String(data.platform_name || "CampusPulse")}
                  />
                </Field>
                <Field
                  label={t("Adresse email de support", "Support email address")}
                >
                  <input
                    type="email"
                    name="support_email"
                    defaultValue={String(data.support_email || "")}
                  />
                </Field>
                <Field
                  label={t(
                    "Message d’information ou de maintenance",
                    "Information or maintenance message",
                  )}
                >
                  <textarea
                    name="maintenance_message"
                    defaultValue={String(data.maintenance_message || "")}
                  />
                </Field>
              </>
            ) : (
              <>
                {[
                  {
                    name: "allow_announcement_comments",
                    title: t(
                      "Commentaires sur les annonces officielles",
                      "Comments on official announcements",
                    ),
                    description: t(
                      "Les responsables peuvent ensuite activer les commentaires annonce par annonce.",
                      "Staff can then enable comments for individual announcements.",
                    ),
                  },
                  {
                    name: "allow_student_posts",
                    title: t("Publications étudiantes", "Student posts"),
                    description: t(
                      "Autoriser les étudiants à créer des publications communautaires.",
                      "Allow students to create community posts.",
                    ),
                  },
                  {
                    name: "allow_student_comments",
                    title: t(
                      "Commentaires communautaires",
                      "Community comments",
                    ),
                    description: t(
                      "Autoriser les étudiants à participer aux discussions.",
                      "Allow students to take part in discussions.",
                    ),
                  },
                  {
                    name: "allow_student_reactions",
                    title: t("Réactions communautaires", "Community reactions"),
                    description: t(
                      "Autoriser les étudiants à réagir aux publications.",
                      "Allow students to react to posts.",
                    ),
                  },
                ].map((setting) => (
                  <label key={setting.name} className="settings-row">
                    <div>
                      <strong>{setting.title}</strong>
                      <p>{setting.description}</p>
                    </div>
                    <input
                      type="checkbox"
                      name={setting.name}
                      defaultChecked={!!data[setting.name]}
                    />
                  </label>
                ))}
                <div style={{ marginTop: 22 }}>
                  <Field
                    label={t(
                      "Taille maximale des fichiers (Mo)",
                      "Maximum file size (MB)",
                    )}
                    hint={t(
                      "La limite générale du serveur reste prioritaire.",
                      "The server’s overall limit still applies.",
                    )}
                  >
                    <input
                      type="number"
                      name="max_upload_size_mb"
                      min={1}
                      max={100}
                      required
                      defaultValue={Number(data.max_upload_size_mb || 20)}
                    />
                  </Field>
                </div>
              </>
            )}
            <div className="form-actions">
              <Button busy={action.isPending}>
                {t("Enregistrer les paramètres", "Save settings")}
              </Button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
