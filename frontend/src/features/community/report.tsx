"use client";
import { usePreferences } from "@/components/preferences";
import { useState } from "react";
import { Button, ErrorNotice, Field, Modal, Success } from "@/components/ui";
import { useAction } from "@/hooks/use-data";
export function ReportDialog({
  postId,
  commentId,
  onClose,
}: {
  postId?: string;
  commentId?: string;
  onClose: () => void;
}) {
  const { t } = usePreferences();
  const [done, setDone] = useState(false);
  const action = useAction(() => setDone(true));
  return (
    <Modal title={t("Signaler un contenu", "Report content")} onClose={onClose}>
      {done ? (
        <>
          <Success>
            {t(
              "Votre signalement a été transmis à l’équipe de modération.",
              "Your report has been sent to the moderation team.",
            )}
          </Success>
          <Button onClick={onClose}>{t("Fermer", "Close")}</Button>
        </>
      ) : (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            const f = new FormData(e.currentTarget);
            action.mutate({
              path: "/reports",
              data: {
                ...(postId ? { post_id: postId } : { comment_id: commentId }),
                reason: f.get("reason"),
                description: f.get("description"),
              },
            });
          }}
        >
          <p className="form-help">
            {t(
              "Décrivez le problème pour aider les modérateurs à prendre une décision.",
              "Describe the issue to help moderators make a decision.",
            )}
          </p>
          <ErrorNotice error={action.error} />
          <Field label={t("Motif", "Reason")}>
            <select name="reason">
              <option value="SPAM">
                {t("Spam ou publicité", "Spam or advertising")}
              </option>
              <option value="HARASSMENT">
                {t("Harcèlement", "Harassment")}
              </option>
              <option value="INAPPROPRIATE">
                {t("Contenu inapproprié", "Inappropriate content")}
              </option>
              <option value="MISINFORMATION">
                {t("Fausse information", "Misinformation")}
              </option>
              <option value="OTHER">{t("Autre", "Other")}</option>
            </select>
          </Field>
          <Field label={t("Précisions", "Details")}>
            <textarea name="description" maxLength={2000} />
          </Field>
          <div className="form-actions">
            <Button variant="secondary" type="button" onClick={onClose}>
              {t("Annuler", "Cancel")}
            </Button>
            <Button busy={action.isPending}>
              {t("Envoyer le signalement", "Send report")}
            </Button>
          </div>
        </form>
      )}
    </Modal>
  );
}
