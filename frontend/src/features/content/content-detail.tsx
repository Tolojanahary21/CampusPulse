"use client";
import { usePreferences } from "@/components/preferences";
import { useState } from "react";
import Link from "next/link";
import { Archive, ArrowLeft, Download, Edit3, Send } from "lucide-react";
import { useParams } from "next/navigation";
import { useSession } from "@/components/app-shell";
import { Badge, Button, ErrorNotice, Loading } from "@/components/ui";
import { useAction, useData } from "@/hooks/use-data";
import { API_URL, ApiError } from "@/lib/api";
import { date } from "@/lib/format";
import type { RecordItem } from "@/types";
import { Comments } from "@/features/community/comments";
import { ContentEditor, type ContentKind } from "./content-editor";
export function ContentDetail({ kind }: { kind: ContentKind }) {
  const { t, locale } = usePreferences();
  const { id } = useParams<{ id: string }>();
  const { canPublish } = useSession();
  const {
    data: item,
    error,
    isPending,
  } = useData<RecordItem>(`/${kind}/${id}`);
  const action = useAction();
  const [editing, setEditing] = useState(false);
  const [downloadError, setDownloadError] = useState<unknown>();
  const [downloading, setDownloading] = useState(false);
  const doc = kind === "documents";
  async function download() {
    setDownloading(true);
    setDownloadError(undefined);
    try {
      const response = await fetch(
        `${API_URL}/files/${item?.file_asset_id}/download`,
        { credentials: "include" },
      );
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new ApiError(
          response.status,
          typeof data.detail === "string"
            ? data.detail
            : "Le téléchargement a été refusé.",
        );
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const disposition = response.headers.get("Content-Disposition") || "";
      const encoded = disposition.match(/filename\*=UTF-8''([^;]+)/i);
      const normal = disposition.match(/filename="?([^";]+)/i);
      a.download = encoded
        ? decodeURIComponent(encoded[1])
        : normal?.[1] ||
          String(item?.original_filename || item?.title || "document");
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) {
      setDownloadError(
        e instanceof TypeError
          ? new ApiError(
              0,
              "Connexion au serveur impossible. Vérifiez votre connexion puis réessayez.",
            )
          : e,
      );
    } finally {
      setDownloading(false);
    }
  }
  if (isPending) return <Loading />;
  return (
    <div className="detail-layout">
      <Link href={`/app/${kind}`} className="text-link">
        <ArrowLeft size={16} />
        {t("Retour", "Back")}{" "}
        {doc
          ? t("à la bibliothèque", "to the library")
          : t("aux annonces", "to announcements")}
      </Link>
      <ErrorNotice error={error || action.error || downloadError} />
      {item && (
        <>
          <article className="panel" style={{ marginTop: 22 }}>
            <div className="panel-body">
              <div className="detail-header">
                <div className="meta-row">
                  <Badge value={doc ? item.category : item.announcement_type} />
                  <Badge value={item.status} />
                  <Badge value={item.scope} />
                </div>
                <h1>{String(item.title)}</h1>
                <p className="small muted">
                  {date(item.created_at, true, locale)} ·{" "}
                  {String(
                    item.author_name ||
                      item.campus_name ||
                      t("Votre établissement", "Your institution"),
                  )}
                </p>
              </div>
              <div className="content-body">
                {String(
                  doc
                    ? item.description ||
                        t(
                          "Aucune description renseignée.",
                          "No description provided.",
                        )
                    : item.content,
                )}
              </div>
              {doc && (
                <div style={{ marginTop: 25 }}>
                  <Button
                    onClick={download}
                    busy={downloading}
                    disabled={item.status !== "PUBLISHED"}
                  >
                    <Download size={17} />
                    {t("Télécharger le document", "Download document")}
                  </Button>
                  {item.status !== "PUBLISHED" && (
                    <p className="small muted" style={{ marginTop: 10 }}>
                      {t(
                        "Le téléchargement sera disponible après publication.",
                        "The download will be available after publication.",
                      )}
                    </p>
                  )}
                </div>
              )}
              {canPublish && (
                <div className="form-actions">
                  <Button variant="secondary" onClick={() => setEditing(true)}>
                    <Edit3 size={16} />
                    {t("Modifier", "Edit")}
                  </Button>
                  {item.status !== "PUBLISHED" && (
                    <Button
                      busy={action.isPending}
                      onClick={() =>
                        action.mutate({ path: `/${kind}/${id}/publish` })
                      }
                    >
                      <Send size={16} />
                      {t("Publier", "Publish")}
                    </Button>
                  )}
                  {item.status !== "ARCHIVED" && (
                    <Button
                      variant="danger"
                      busy={action.isPending}
                      onClick={() => {
                        if (
                          window.confirm(
                            t(
                              "Archiver ce contenu ? Il ne sera plus visible dans le fil publié.",
                              "Archive this content? It will no longer appear in the published feed.",
                            ),
                          )
                        )
                          action.mutate({ path: `/${kind}/${id}/archive` });
                      }}
                    >
                      <Archive size={16} />
                      {t("Archiver", "Archive")}
                    </Button>
                  )}
                </div>
              )}
            </div>
          </article>
          {!doc && !!item.allow_comments && (
            <Comments path={`/announcements/${id}/comments`} />
          )}{" "}
          {editing && (
            <ContentEditor
              kind={kind}
              item={item}
              onClose={() => setEditing(false)}
            />
          )}
        </>
      )}
    </div>
  );
}
