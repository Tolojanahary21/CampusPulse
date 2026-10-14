"use client";
import { usePreferences } from "@/components/preferences";
import { useState } from "react";
import {
  CalendarDays,
  Clock,
  Edit3,
  ExternalLink,
  MapPin,
  Plus,
} from "lucide-react";
import { useSession } from "@/components/app-shell";
import {
  Badge,
  Button,
  Empty,
  ErrorNotice,
  Field,
  Loading,
  Modal,
  PageTitle,
  Pagination,
} from "@/components/ui";
import { useAction, useData } from "@/hooks/use-data";
import { date, label, params } from "@/lib/format";
import type { Collection, RecordItem } from "@/types";
function EventEditor({
  item,
  onClose,
}: {
  item?: RecordItem;
  onClose: () => void;
}) {
  const { t, locale } = usePreferences();
  const { campusId } = useSession();
  const action = useAction(onClose);
  function local(v: unknown) {
    if (!v) return "";
    const d = new Date(String(v));
    return new Date(d.getTime() - d.getTimezoneOffset() * 60000)
      .toISOString()
      .slice(0, 16);
  }
  return (
    <Modal
      title={
        item
          ? t("Modifier l’événement", "Edit event")
          : t("Créer un événement", "Create an event")
      }
      onClose={onClose}
    >
      <form
        onSubmit={(e) => {
          e.preventDefault();
          const f = new FormData(e.currentTarget);
          action.mutate({
            path: `/events${item ? `/${item.id}` : ""}`,
            method: item ? "PATCH" : "POST",
            data: {
              campus_id: campusId,
              title: f.get("title"),
              description: f.get("description"),
              location: f.get("location"),
              starts_at: new Date(String(f.get("starts_at"))).toISOString(),
              ends_at: new Date(String(f.get("ends_at"))).toISOString(),
              registration_url: f.get("registration_url") || null,
              status: f.get("status"),
            },
          });
        }}
      >
        <ErrorNotice error={action.error} />
        <Field label={t("Titre", "Title")}>
          <input
            name="title"
            required
            defaultValue={String(item?.title || "")}
          />
        </Field>
        <Field label={t("Description", "Description")}>
          <textarea
            name="description"
            required
            defaultValue={String(item?.description || "")}
          />
        </Field>
        <div className="form-grid">
          <Field label={t("Début", "Start")}>
            <input
              type="datetime-local"
              name="starts_at"
              required
              defaultValue={local(item?.starts_at)}
            />
          </Field>
          <Field label={t("Fin", "End")}>
            <input
              type="datetime-local"
              name="ends_at"
              required
              defaultValue={local(item?.ends_at)}
            />
          </Field>
        </div>
        <Field label={t("Lieu", "Location")}>
          <input name="location" defaultValue={String(item?.location || "")} />
        </Field>
        <Field
          label={t(
            "Lien d’inscription (facultatif)",
            "Registration link (optional)",
          )}
        >
          <input
            name="registration_url"
            type="url"
            placeholder="https://…"
            defaultValue={String(item?.registration_url || "")}
          />
        </Field>
        <Field label={t("Statut", "Status")}>
          <select name="status" defaultValue={String(item?.status || "DRAFT")}>
            {["DRAFT", "PUBLISHED", "CANCELLED", "COMPLETED"].map((v) => (
              <option value={v} key={v}>
                {label(v, locale)}
              </option>
            ))}
          </select>
        </Field>
        <div className="form-actions">
          <Button variant="secondary" type="button" onClick={onClose}>
            {t("Annuler", "Cancel")}
          </Button>
          <Button busy={action.isPending}>{t("Enregistrer", "Save")}</Button>
        </div>
      </form>
    </Modal>
  );
}
export function EventsPage() {
  const { t, locale } = usePreferences();
  const { campusId, canPublish } = useSession();
  const [page, setPage] = useState(1);
  const [editor, setEditor] = useState<RecordItem | null | undefined>();
  const { data, error, isPending } = useData<Collection>(
    `/events${params({ campus_id: campusId, page, page_size: 12, manage: canPublish })}`,
  );
  return (
    <>
      <PageTitle
        eyebrow={t("À VOS AGENDAS", "SAVE THE DATE")}
        title={t("Les rendez-vous du campus", "Campus events")}
        description={t(
          "Conférences, rencontres et temps forts de la vie universitaire.",
          "Conferences, meetups and highlights of university life.",
        )}
        action={
          canPublish ? (
            <Button disabled={!campusId} onClick={() => setEditor(null)}>
              <Plus size={17} />
              {t("Nouvel événement", "New event")}
            </Button>
          ) : undefined
        }
      />
      <ErrorNotice error={error} />
      {isPending ? (
        <Loading />
      ) : !data?.items.length ? (
        <div className="panel">
          <Empty
            title={t("Le calendrier se prépare", "The calendar is coming soon")}
            description={t(
              "Retrouvez bientôt les prochains rendez-vous de votre établissement.",
              "Upcoming events at your institution will appear here.",
            )}
          />
        </div>
      ) : (
        <div className="cards-grid">
          {data.items.map((item) => (
            <article className="content-card" key={item.id}>
              <div className="meta-row">
                <CalendarDays size={18} />
                <Badge value={item.status} />
                {canPublish && (
                  <button
                    className="icon-button"
                    style={{ marginLeft: "auto" }}
                    aria-label={t("Modifier l’événement", "Edit event")}
                    onClick={() => setEditor(item)}
                  >
                    <Edit3 size={16} />
                  </button>
                )}
              </div>
              <h3>{String(item.title)}</h3>
              <p className="content-body">{String(item.description)}</p>
              <p className="actions">
                <Clock size={14} />
                {date(item.starts_at, true, locale)}
              </p>
              <p className="small muted">
                {t("Jusqu’au", "Until")} {date(item.ends_at, true, locale)}
              </p>
              <p className="actions">
                <MapPin size={14} />
                {String(
                  item.location ||
                    t("Lieu à confirmer", "Location to be confirmed"),
                )}
              </p>
              {!!item.registration_url &&
                /^https?:\/\//i.test(String(item.registration_url)) && (
                  <a
                    className="button secondary"
                    href={String(item.registration_url)}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {t("S’inscrire", "Register")} <ExternalLink size={14} />
                  </a>
                )}
            </article>
          ))}
        </div>
      )}
      <Pagination data={data} page={page} setPage={setPage} />
      {editor !== undefined && (
        <EventEditor
          item={editor || undefined}
          onClose={() => setEditor(undefined)}
        />
      )}
    </>
  );
}
