"use client";
import { useState } from "react";
import { usePreferences } from "@/components/preferences";
import { History, Mail, Plus, Search } from "lucide-react";
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
  Success,
} from "@/components/ui";
import { useAction, useData } from "@/hooks/use-data";
import { params } from "@/lib/format";
import type { Collection, RecordItem } from "@/types";
function HistoryDialog({
  student,
  onClose,
}: {
  student: RecordItem;
  onClose: () => void;
}) {
  const { t } = usePreferences();
  const [page, setPage] = useState(1);
  const { data, error, isPending } = useData<Collection>(
    `/students/${student.id}/enrollments?page=${page}&page_size=20`,
  );
  return (
    <Modal
      title={t(
        `Parcours de ${student.first_name} ${student.last_name}`,
        `Academic history of ${student.first_name} ${student.last_name}`,
      )}
      onClose={onClose}
    >
      <ErrorNotice error={error} />
      {isPending ? (
        <Loading />
      ) : !data?.items.length ? (
        <Empty title={t("Aucune inscription", "No enrollments")} />
      ) : (
        data.items.map((item) => (
          <div className="history-row" key={item.id}>
            <div className="section-heading">
              <h3>
                {String(item.program_name)} · {String(item.level_name)}
              </h3>
              <Badge value={item.status} />
            </div>
            <p>
              {String(item.academic_year_name)} · {String(item.campus_name)}
            </p>
            <p>{String(item.enrollment_number)}</p>
          </div>
        ))
      )}
      <Pagination data={data} page={page} setPage={setPage} />
    </Modal>
  );
}
export function CampusUsers() {
  const { t } = usePreferences();
  const { campusId, isPlatform } = useSession();
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [invite, setInvite] = useState(false);
  const [history, setHistory] = useState<RecordItem>();
  const [success, setSuccess] = useState(false);
  const { data, error, isPending } = useData<Collection>(
    `/campuses/${campusId}/users${params({ q, page, page_size: 15 })}`,
  );
  const action = useAction(() => {
    setInvite(false);
    setSuccess(true);
  });
  return (
    <>
      <div className="section-heading">
        <h2>{t("Membres de l’établissement", "Campus members")}</h2>
        <Button onClick={() => setInvite(true)}>
          <Plus size={16} />
          {t("Inviter un membre", "Invite a member")}
        </Button>
      </div>
      <div className="toolbar">
        <div className="search-input">
          <Search size={17} />
          <input
            aria-label={t("Rechercher un membre", "Search members")}
            value={q}
            onChange={(e) => {
              setQ(e.target.value);
              setPage(1);
            }}
            placeholder={t(
              "Rechercher par nom ou email…",
              "Search by name or email…",
            )}
          />
        </div>
      </div>
      <ErrorNotice error={error || (!invite ? action.error : null)} />
      {success && (
        <Success>
          {t(
            "La modification a été enregistrée.",
            "Your changes have been saved.",
          )}
        </Success>
      )}
      <div className="panel">
        {isPending ? (
          <Loading />
        ) : !data?.items.length ? (
          <Empty
            title={t("Votre équipe se construit", "Build your community")}
            description={t(
              "Invitez les étudiants et les responsables de votre établissement.",
              "Invite your campus students and staff.",
            )}
          />
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>{t("Membre", "Member")}</th>
                  <th>{t("Adresse email", "Email address")}</th>
                  <th>{t("Adhésion au campus", "Campus membership")}</th>
                  <th>{t("Actions", "Actions")}</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((item) => (
                  <tr key={item.id}>
                    <td>
                      {String(item.first_name)} {String(item.last_name)}
                    </td>
                    <td>{String(item.email)}</td>
                    <td>
                      <Badge value={item.membership_status || item.status} />
                    </td>
                    <td>
                      <div className="actions">
                        <button
                          className="icon-button"
                          aria-label={t(
                            "Voir le parcours",
                            "View academic history",
                          )}
                          onClick={() => setHistory(item)}
                        >
                          <History size={16} />
                        </button>
                        {!item.email_verified_at && (
                          <button
                            className="icon-button"
                            aria-label={t(
                              "Renvoyer l’invitation",
                              "Resend invitation",
                            )}
                            disabled={action.isPending}
                            onClick={() =>
                              action.mutate({
                                path: `/campuses/${campusId}/users/${item.id}/resend-invitation`,
                              })
                            }
                          >
                            <Mail size={16} />
                          </button>
                        )}
                        <select
                          aria-label={t(
                            `Statut de ${item.first_name} ${item.last_name}`,
                            `Status of ${item.first_name} ${item.last_name}`,
                          )}
                          style={{
                            width: 130,
                            padding: "6px 8px",
                            fontSize: 11,
                          }}
                          value={String(item.membership_status || "ACTIVE")}
                          disabled={action.isPending}
                          onChange={(e) => {
                            if (
                              window.confirm(
                                t(
                                  "Modifier l’adhésion de ce membre à cet établissement ?",
                                  "Change this member’s campus membership?",
                                ),
                              )
                            )
                              action.mutate({
                                path: `/campuses/${campusId}/users/${item.id}/status`,
                                method: "PATCH",
                                data: { status: e.target.value },
                              });
                          }}
                        >
                          <option value="ACTIVE">{t("Actif", "Active")}</option>
                          <option value="SUSPENDED">
                            {t("Suspendu", "Suspended")}
                          </option>
                          <option value="ENDED">
                            {t("Terminée", "Completed")}
                          </option>
                        </select>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      <Pagination data={data} page={page} setPage={setPage} />
      {invite && (
        <Modal
          title={t("Inviter un membre", "Invite a member")}
          onClose={() => setInvite(false)}
        >
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              setSuccess(false);
              action.mutate({
                path: `/campuses/${campusId}/users`,
                data: {
                  email: f.get("email"),
                  first_name: f.get("first_name"),
                  last_name: f.get("last_name"),
                  role: f.get("role"),
                },
              });
            }}
          >
            <p className="form-help">
              {t(
                "Le membre recevra par email un lien pour choisir son mot de passe et activer son compte.",
                "The member will receive an email link to choose a password and activate their account.",
              )}
            </p>
            <ErrorNotice error={action.error} />
            <div className="form-grid">
              <Field label={t("Prénom", "First name")}>
                <input name="first_name" required maxLength={100} />
              </Field>
              <Field label={t("Nom", "Last name")}>
                <input name="last_name" required maxLength={100} />
              </Field>
            </div>
            <Field label={t("Email", "Email")}>
              <input name="email" type="email" required />
            </Field>
            <Field label={t("Rôle", "Role")}>
              <select name="role">
                <option value="STUDENT">{t("Étudiant", "Student")}</option>
                <option value="CONTENT_PUBLISHER">
                  {t("Responsable de publication", "Content publisher")}
                </option>
                <option value="MODERATOR">
                  {t("Modérateur", "Moderator")}
                </option>
                {isPlatform && (
                  <option value="CAMPUS_ADMIN">
                    {t(
                      "Administrateur d’établissement",
                      "Campus administrator",
                    )}
                  </option>
                )}
              </select>
            </Field>
            <div className="form-actions">
              <Button
                type="button"
                variant="secondary"
                onClick={() => setInvite(false)}
              >
                {t("Annuler", "Cancel")}
              </Button>
              <Button busy={action.isPending}>
                <Mail size={16} />
                {t("Envoyer l’invitation", "Send invitation")}
              </Button>
            </div>
          </form>
        </Modal>
      )}{" "}
      {history && (
        <HistoryDialog
          student={history}
          onClose={() => setHistory(undefined)}
        />
      )}
    </>
  );
}
