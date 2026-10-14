"use client";
import { useState } from "react";
import { usePreferences } from "@/components/preferences";
import { ShieldCheck } from "lucide-react";
import { useSession } from "@/components/app-shell";
import {
  Badge,
  Button,
  Empty,
  ErrorNotice,
  Field,
  Loading,
  Modal,
  Pagination,
  Tabs,
} from "@/components/ui";
import { useAction, useData } from "@/hooks/use-data";
import { date, label, params } from "@/lib/format";
import type { Collection, RecordItem } from "@/types";
export function Moderation() {
  const { t, locale } = usePreferences();
  const { campusId } = useSession();
  const [status, setStatus] = useState("OPEN");
  const [page, setPage] = useState(1);
  const [review, setReview] = useState<RecordItem>();
  const { data, error, isPending } = useData<Collection>(
    `/moderation/reports${params({ campus_id: campusId, status, page, page_size: 15 })}`,
  );
  const action = useAction(() => setReview(undefined));
  return (
    <>
      <div className="section-heading">
        <h2>{t("Signalements de la communauté", "Community reports")}</h2>
        <ShieldCheck size={22} />
      </div>
      <Tabs
        value={status}
        onChange={(v) => {
          setStatus(v);
          setPage(1);
        }}
        items={[
          { id: "OPEN", label: t("À traiter", "Open") },
          { id: "RESOLVED", label: t("Résolus", "Resolved") },
          { id: "DISMISSED", label: t("Classés", "Dismissed") },
        ]}
      />
      <ErrorNotice error={error} />
      {isPending ? (
        <Loading />
      ) : !data?.items.length ? (
        <div className="panel">
          <Empty
            title={t(
              "Aucun signalement dans cette catégorie",
              "No reports in this category",
            )}
            description={t(
              "Chaque décision de modération est conservée dans le journal d’audit.",
              "Every moderation decision is recorded in the audit log.",
            )}
          />
        </div>
      ) : (
        <div className="list-stack">
          {data.items.map((item) => (
            <article className="content-card" key={item.id}>
              <div className="meta-row">
                <Badge value={item.status} />
                <span>{date(item.created_at, true, locale)}</span>
                <span>
                  {t("Signalé par", "Reported by")}{" "}
                  {String(item.reporter_name || t("un membre", "a member"))}
                </span>
              </div>
              <h3>
                {String(
                  item.post_title ||
                    t("Commentaire signalé", "Reported comment"),
                )}
              </h3>
              <p className="content-body">{String(item.content || "")}</p>
              <p>
                <strong>{t("Motif :", "Reason:")}</strong>{" "}
                {label(item.reason, locale)}
              </p>
              {!!item.description && <p>{String(item.description)}</p>}
              <div className="actions">
                <Button variant="secondary" onClick={() => setReview(item)}>
                  {t("Examiner le signalement", "Review report")}
                </Button>
              </div>
            </article>
          ))}
        </div>
      )}
      <Pagination data={data} page={page} setPage={setPage} />
      {review && (
        <Modal
          title={t("Décision de modération", "Moderation decision")}
          onClose={() => setReview(undefined)}
        >
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              action.mutate({
                path: `/moderation/reports/${review.id}`,
                method: "PATCH",
                data: {
                  status: f.get("status"),
                  action: f.get("action"),
                  reason: f.get("reason"),
                },
              });
            }}
          >
            <ErrorNotice error={action.error} />
            <Field label={t("Décision", "Decision")}>
              <select name="status">
                <option value="RESOLVED">
                  {t("Signalement résolu", "Resolve report")}
                </option>
                <option value="DISMISSED">
                  {t("Classer sans suite", "Dismiss report")}
                </option>
              </select>
            </Field>
            <Field label={t("Action sur le contenu", "Content action")}>
              <select name="action">
                <option value="NONE">
                  {t("Conserver le contenu", "Keep content")}
                </option>
                <option value="HIDE">
                  {t("Masquer le contenu", "Hide content")}
                </option>
                <option value="RESTORE">
                  {t("Restaurer le contenu", "Restore content")}
                </option>
              </select>
            </Field>
            <Field label={t("Motif de la décision", "Reason for the decision")}>
              <textarea name="reason" required minLength={3} maxLength={2000} />
            </Field>
            <p className="form-help">
              {t(
                "La décision, votre identité et son motif seront conservés dans l’historique de modération.",
                "The decision, your identity and the reason will be recorded in the moderation history.",
              )}
            </p>
            <Button busy={action.isPending}>
              {t("Enregistrer la décision", "Save decision")}
            </Button>
          </form>
        </Modal>
      )}
    </>
  );
}
