"use client";
import { usePreferences } from "@/components/preferences";
import { useState } from "react";
import { Flag, Send, Trash2, Edit3 } from "lucide-react";
import { useSession } from "@/components/app-shell";
import {
  Button,
  Empty,
  ErrorNotice,
  Field,
  Loading,
  Modal,
  Pagination,
} from "@/components/ui";
import { useAction, useData } from "@/hooks/use-data";
import { date, initials } from "@/lib/format";
import { API_URL } from "@/lib/api";
import type { Collection, RecordItem } from "@/types";
import { ReportDialog } from "./report";
export function Comments({
  path,
  community = false,
}: {
  path: string;
  community?: boolean;
}) {
  const { t, locale } = usePreferences();
  const { user } = useSession();
  const [page, setPage] = useState(1);
  const { data, error, isPending } = useData<Collection>(
    `${path}?page=${page}&page_size=20`,
  );
  const [content, setContent] = useState("");
  const [report, setReport] = useState("");
  const [editing, setEditing] = useState<RecordItem>();
  const add = useAction(() => setContent(""));
  const action = useAction(() => setEditing(undefined));
  return (
    <section className="panel" style={{ marginTop: 23 }}>
      <div className="panel-header">
        <h2>
          {t("La discussion", "Discussion")}{" "}
          <span className="muted small">{data?.total ?? ""}</span>
        </h2>
      </div>
      <div className="panel-body">
        <ErrorNotice error={error || add.error || action.error} />
        {isPending ? (
          <Loading />
        ) : !data?.items.length ? (
          <Empty
            title={t(
              "La discussion commence ici",
              "The discussion starts here",
            )}
            description={t(
              "Partagez une question ou une réponse utile à votre communauté.",
              "Share a question or a helpful answer with your community.",
            )}
          />
        ) : (
          data.items.map((item) => (
            <div className="comment" key={item.id}>
              <span className="avatar">
                {typeof item.author_avatar_url === "string" ? <img src={`${API_URL}${item.author_avatar_url}`} alt="" crossOrigin="use-credentials" /> : initials(String(item.author_name || t("Membre", "Member")))}
              </span>
              <div style={{ flex: 1 }}>
                <div className="comment-meta">
                  <strong>
                    {String(
                      item.author_name ||
                        t("Membre du campus", "Campus member"),
                    )}
                  </strong>{" "}
                  · {date(item.created_at, true, locale)}
                </div>
                <p>{String(item.content)}</p>
                {community && (
                  <div className="actions" style={{ marginTop: 8 }}>
                    <button
                      className="icon-button"
                      aria-label={t(
                        "Signaler ce commentaire",
                        "Report this comment",
                      )}
                      onClick={() => setReport(item.id)}
                    >
                      <Flag size={13} />
                    </button>
                    {item.author_user_id === user.id && (
                      <>
                        <button
                          className="icon-button"
                          aria-label={t(
                            "Modifier ce commentaire",
                            "Edit this comment",
                          )}
                          onClick={() => setEditing(item)}
                        >
                          <Edit3 size={13} />
                        </button>
                        <button
                          className="icon-button"
                          aria-label={t(
                            "Retirer ce commentaire",
                            "Remove this comment",
                          )}
                          onClick={() => {
                            if (
                              window.confirm(
                                t(
                                  "Retirer ce commentaire ?",
                                  "Remove this comment?",
                                ),
                              )
                            )
                              action.mutate({
                                path: `/community/comments/${item.id}`,
                                method: "DELETE",
                              });
                          }}
                        >
                          <Trash2 size={13} />
                        </button>
                      </>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))
        )}
        <Pagination data={data} page={page} setPage={setPage} />
        <form
          onSubmit={(e) => {
            e.preventDefault();
            add.mutate({ path, data: { content } });
          }}
          style={{ marginTop: 23 }}
        >
          <Field label={t("Votre commentaire", "Your comment")}>
            <textarea
              required
              minLength={1}
              maxLength={5000}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder={t(
                "Participez à la discussion avec bienveillance…",
                "Join the discussion respectfully…",
              )}
              rows={3}
            />
          </Field>
          <div className="actions" style={{ justifyContent: "flex-end" }}>
            <Button busy={add.isPending} disabled={!content.trim()}>
              <Send size={15} />
              {t("Commenter", "Comment")}
            </Button>
          </div>
        </form>
      </div>
      {report && (
        <ReportDialog commentId={report} onClose={() => setReport("")} />
      )}{" "}
      {editing && (
        <Modal
          title={t("Modifier votre commentaire", "Edit your comment")}
          onClose={() => setEditing(undefined)}
        >
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              action.mutate({
                path: `/community/comments/${editing.id}`,
                method: "PATCH",
                data: { content: f.get("content") },
              });
            }}
          >
            <ErrorNotice error={action.error} />
            <Field label={t("Commentaire", "Comment")}>
              <textarea
                name="content"
                required
                defaultValue={String(editing.content)}
              />
            </Field>
            <Button busy={action.isPending}>{t("Enregistrer", "Save")}</Button>
          </form>
        </Modal>
      )}
    </section>
  );
}
