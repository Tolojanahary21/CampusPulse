"use client";
import { usePreferences } from "@/components/preferences";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useSession } from "@/components/app-shell";
import { Button, ErrorNotice, Field, Modal } from "@/components/ui";
import { api, mutate } from "@/lib/api";
import { label } from "@/lib/format";
import { useAcademic, options } from "@/features/academic/use-academic";
import type { RecordItem } from "@/types";
export type ContentKind = "announcements" | "documents";
export function ContentEditor({
  kind,
  item,
  onClose,
}: {
  kind: ContentKind;
  item?: RecordItem;
  onClose: () => void;
}) {
  const { t, locale } = usePreferences();
  const { campusId, isPlatform } = useSession();
  const academic = useAcademic(campusId);
  const [scope, setScope] = useState(String(item?.scope || "CAMPUS"));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>();
  const client = useQueryClient();
  const doc = kind === "documents";
  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError(undefined);
    const f = new FormData(e.currentTarget);
    try {
      let fileAsset = item?.file_asset_id;
      if (
        doc &&
        f.get("file") instanceof File &&
        (f.get("file") as File).size
      ) {
        const upload = new FormData();
        upload.set("file", f.get("file")!);
        if (campusId && scope !== "PLATFORM") upload.set("campus_id", campusId);
        const asset = await api<{ id: string }>("/files/upload", {
          method: "POST",
          body: upload,
        });
        fileAsset = asset.id;
      }
      const data: Record<string, unknown> = {
        title: f.get("title"),
        scope,
        campus_id: scope === "PLATFORM" ? null : campusId,
        program_ids: scope === "TARGETED" ? f.getAll("program_ids") : [],
        level_ids: scope === "TARGETED" ? f.getAll("level_ids") : [],
        year_ids: scope === "TARGETED" ? f.getAll("year_ids") : [],
      };
      if (doc)
        Object.assign(data, {
          description: f.get("description"),
          category: f.get("category"),
          file_asset_id: fileAsset,
          subject_id: f.get("subject_id") || null,
        });
      else
        Object.assign(data, {
          content: f.get("content"),
          summary: f.get("summary"),
          announcement_type: f.get("announcement_type"),
          is_pinned: f.get("is_pinned") === "on",
          allow_comments: f.get("allow_comments") === "on",
          starts_at: f.get("starts_at")
            ? new Date(String(f.get("starts_at"))).toISOString()
            : null,
          ends_at: f.get("ends_at")
            ? new Date(String(f.get("ends_at"))).toISOString()
            : null,
        });
      await mutate(
        `/${kind}${item ? `/${item.id}` : ""}`,
        item ? "PATCH" : "POST",
        data,
      );
      await client.invalidateQueries();
      onClose();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }
  function localTime(value: unknown) {
    if (!value) return "";
    const d = new Date(String(value));
    return new Date(d.getTime() - d.getTimezoneOffset() * 60000)
      .toISOString()
      .slice(0, 16);
  }
  return (
    <Modal
      title={`${item ? t("Modifier", "Edit") : t("Créer", "Create")} ${doc ? t("un document", "a document") : t("une annonce", "an announcement")}`}
      onClose={onClose}
    >
      <form onSubmit={submit}>
        <ErrorNotice error={error || academic.error} />
        <Field label={t("Titre", "Title")}>
          <input
            name="title"
            required
            maxLength={255}
            defaultValue={String(item?.title || "")}
            placeholder={
              doc
                ? t(
                    "Ex. Introduction à l’algorithmique",
                    "E.g. Introduction to algorithms",
                  )
                : t(
                    "Ex. Calendrier des examens du semestre",
                    "E.g. Semester exam schedule",
                  )
            }
          />
        </Field>
        {doc ? (
          <>
            <Field label={t("Description", "Description")}>
              <textarea
                name="description"
                defaultValue={String(item?.description || "")}
              />
            </Field>
            <div className="form-grid">
              <Field label={t("Catégorie", "Category")}>
                <select
                  name="category"
                  defaultValue={String(item?.category || "COURSE")}
                >
                  {[
                    "COURSE",
                    "EXERCISE",
                    "SOLUTION",
                    "EXAM",
                    "SUMMARY",
                    "OTHER",
                  ].map((v) => (
                    <option key={v} value={v}>
                      {v === "SOLUTION"
                        ? t("Corrigé", "Solution")
                        : label(v, locale)}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label={t("Matière", "Subject")}>
                <select
                  name="subject_id"
                  defaultValue={String(item?.subject_id || "")}
                >
                  <option value="">{t("Sans matière", "No subject")}</option>
                  {options(academic.subjects)}
                </select>
              </Field>
            </div>
            <Field
              label={
                item
                  ? t(
                      "Remplacer le fichier (facultatif)",
                      "Replace file (optional)",
                    )
                  : t("Fichier pédagogique", "Learning material")
              }
              hint={t(
                "PDF, TXT, images, Word, Excel ou PowerPoint. La limite dépend de votre établissement.",
                "PDF, TXT, images, Word, Excel or PowerPoint. The size limit is set by your institution.",
              )}
            >
              <input
                type="file"
                name="file"
                accept=".pdf,.txt,.png,.jpg,.jpeg,.docx,.xlsx,.pptx"
                required={!item}
              />
            </Field>
          </>
        ) : (
          <>
            <Field label={t("Résumé", "Summary")}>
              <input
                name="summary"
                maxLength={500}
                defaultValue={String(item?.summary || "")}
              />
            </Field>
            <Field label={t("Contenu", "Content")}>
              <textarea
                name="content"
                required
                rows={6}
                defaultValue={String(item?.content || "")}
              />
            </Field>
            <Field label={t("Type d’annonce", "Announcement type")}>
              <select
                name="announcement_type"
                defaultValue={String(item?.announcement_type || "GENERAL")}
              >
                {[
                  "GENERAL",
                  "ADMINISTRATIVE",
                  "ACADEMIC",
                  "EVENT",
                  "URGENT",
                ].map((v) => (
                  <option key={v} value={v}>
                    {label(v, locale)}
                  </option>
                ))}
              </select>
            </Field>
          </>
        )}
        <Field label={t("Destinataires", "Audience")}>
          <select value={scope} onChange={(e) => setScope(e.target.value)}>
            <option value="CAMPUS">
              {t(
                "Tous les membres de l’établissement",
                "Everyone at the institution",
              )}
            </option>
            <option value="TARGETED">
              {t("Parcours universitaires ciblés", "Selected academic groups")}
            </option>
            {isPlatform && (
              <option value="PLATFORM">
                {t("Toute la plateforme", "Entire platform")}
              </option>
            )}
          </select>
        </Field>
        {scope === "TARGETED" && (
          <fieldset className="targeting">
            <legend>{t("Ciblage du contenu", "Content audience")}</legend>
            <p className="form-help">
              {t(
                "Les filtres se combinent : une inscription doit correspondre à chaque dimension renseignée. Ctrl ou Cmd pour sélectionner plusieurs choix.",
                "Filters are combined: an enrollment must match each selected dimension. Use Ctrl or Cmd to select multiple options.",
              )}
            </p>
            <Field label={t("Filières", "Programs")}>
              <select
                className="multiselect"
                multiple
                name="program_ids"
                defaultValue={(item?.program_ids as string[]) || []}
              >
                {options(academic.programs)}
              </select>
            </Field>
            <Field label={t("Niveaux", "Levels")}>
              <select
                className="multiselect"
                multiple
                name="level_ids"
                defaultValue={(item?.level_ids as string[]) || []}
              >
                {options(academic.levels, "program_name")}
              </select>
            </Field>
            <Field label={t("Années universitaires", "Academic years")}>
              <select
                className="multiselect"
                multiple
                name="year_ids"
                defaultValue={(item?.year_ids as string[]) || []}
              >
                {options(academic.years)}
              </select>
            </Field>
          </fieldset>
        )}
        {!doc && (
          <>
            <div className="form-grid">
              <Field label={t("Visible à partir du", "Visible from")}>
                <input
                  name="starts_at"
                  type="datetime-local"
                  defaultValue={localTime(item?.starts_at)}
                />
              </Field>
              <Field label={t("Visible jusqu’au", "Visible until")}>
                <input
                  name="ends_at"
                  type="datetime-local"
                  defaultValue={localTime(item?.ends_at)}
                />
              </Field>
            </div>
            <label className="checkbox">
              <input
                type="checkbox"
                name="is_pinned"
                defaultChecked={!!item?.is_pinned}
              />
              {t("Épingler cette annonce", "Pin this announcement")}
            </label>
            <label className="checkbox">
              <input
                type="checkbox"
                name="allow_comments"
                defaultChecked={!!item?.allow_comments}
              />
              {t(
                "Autoriser les commentaires (si l’établissement les autorise)",
                "Allow comments (if enabled by the institution)",
              )}
            </label>
          </>
        )}
        <div className="form-actions">
          <Button variant="secondary" type="button" onClick={onClose}>
            {t("Annuler", "Cancel")}
          </Button>
          <Button busy={busy} type="submit">
            {item
              ? t("Enregistrer", "Save")
              : t("Créer le brouillon", "Create draft")}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
