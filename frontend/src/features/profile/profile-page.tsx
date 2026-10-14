"use client";
import { usePreferences } from "@/components/preferences";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { Save, ShieldCheck } from "lucide-react";
import { useSession } from "@/components/app-shell";
import {
  Badge,
  Button,
  Empty,
  ErrorNotice,
  Field,
  Loading,
  PageTitle,
  Pagination,
  Success,
} from "@/components/ui";
import { useAction, useData } from "@/hooks/use-data";
import { initials } from "@/lib/format";
import type { Collection } from "@/types";
export function ProfilePage() {
  const { t } = usePreferences();
  const { user } = useSession();
  const router = useRouter();
  const client = useQueryClient();
  const [saved, setSaved] = useState(false);
  const [page, setPage] = useState(1);
  const [passwordError, setPasswordError] = useState<unknown>();
  const history = useData<Collection>(
    `/students/${user.id}/enrollments?page=${page}&page_size=10`,
  );
  const preferences = useData<{
    email_announcements: boolean;
    email_community: boolean;
  }>("/notification-preferences");
  const profile = useAction(() => setSaved(true));
  const pref = useAction();
  const password = useAction(() => {
    client.clear();
    router.replace("/login");
  });
  return (
    <>
      <PageTitle
        eyebrow={t("VOTRE ESPACE PERSONNEL", "YOUR PERSONAL SPACE")}
        title={t("Mon profil & mon parcours", "My profile & studies")}
        description={t(
          "Vos informations, vos préférences et votre histoire universitaire.",
          "Your information, preferences and academic history.",
        )}
      />
      <div className="profile-grid">
        <div className="stack">
          <section className="panel">
            <div className="panel-header">
              <h2>{t("Mes informations", "My information")}</h2>
            </div>
            <div className="panel-body">
              <div className="profile-identity">
                <span className="avatar">
                  {initials(user.first_name, user.last_name)}
                </span>
                <div>
                  <h2>
                    {user.first_name} {user.last_name}
                  </h2>
                  <p className="muted small">{user.email}</p>
                </div>
              </div>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  setSaved(false);
                  const f = new FormData(e.currentTarget);
                  profile.mutate({
                    path: "/users/me",
                    method: "PATCH",
                    data: {
                      first_name: f.get("first_name"),
                      last_name: f.get("last_name"),
                      phone: f.get("phone") || null,
                    },
                  });
                }}
              >
                <ErrorNotice error={profile.error} />
                {saved && (
                  <Success>
                    {t(
                      "Votre profil a été mis à jour.",
                      "Your profile has been updated.",
                    )}
                  </Success>
                )}
                <div className="form-grid">
                  <Field label={t("Prénom", "First name")}>
                    <input
                      name="first_name"
                      defaultValue={user.first_name}
                      required
                      maxLength={100}
                    />
                  </Field>
                  <Field label={t("Nom", "Last name")}>
                    <input
                      name="last_name"
                      defaultValue={user.last_name}
                      required
                      maxLength={100}
                    />
                  </Field>
                </div>
                <Field label={t("Téléphone", "Phone")}>
                  <input
                    type="tel"
                    name="phone"
                    defaultValue={user.phone || ""}
                    maxLength={30}
                  />
                </Field>
                <Button busy={profile.isPending}>
                  <Save size={16} />
                  {t("Enregistrer les modifications", "Save changes")}
                </Button>
              </form>
            </div>
          </section>
          <section className="panel">
            <div className="panel-header">
              <h2>{t("Mon parcours universitaire", "My academic history")}</h2>
            </div>
            <div className="panel-body">
              <ErrorNotice error={history.error} />
              {history.isPending ? (
                <Loading />
              ) : !history.data?.items.length ? (
                <Empty
                  title={t(
                    "Votre parcours commence ici",
                    "Your journey starts here",
                  )}
                  description={t(
                    "Votre établissement ajoutera vos inscriptions à cet espace.",
                    "Your institution will add your enrollments here.",
                  )}
                />
              ) : (
                history.data.items.map((item) => (
                  <div className="history-row" key={item.id}>
                    <div className="section-heading">
                      <h3>
                        {String(item.program_name || t("Filière", "Program"))} ·{" "}
                        {String(item.level_name || "")}
                      </h3>
                      <Badge value={item.status} />
                    </div>
                    <p>
                      {String(item.campus_name || "")} ·{" "}
                      {String(item.academic_year_name || "")}
                    </p>
                    <p>
                      {t("Numéro d’inscription :", "Enrollment number:")}{" "}
                      {String(item.enrollment_number || "—")}
                    </p>
                  </div>
                ))
              )}
              <Pagination data={history.data} page={page} setPage={setPage} />
            </div>
          </section>
        </div>
        <div className="stack">
          <section className="panel">
            <div className="panel-header">
              <h2>{t("Mes préférences email", "My email preferences")}</h2>
            </div>
            <div className="panel-body">
              <p className="small muted">
                {t(
                  "Choisissez les actualités que vous souhaitez également recevoir par email.",
                  "Choose which updates you would also like to receive by email.",
                )}
              </p>
              <ErrorNotice error={preferences.error || pref.error} />
              {preferences.data && (
                <>
                  <label className="settings-row">
                    <div>
                      <strong>
                        {t("Annonces officielles", "Official announcements")}
                      </strong>
                      <p>
                        {t(
                          "Les nouvelles publiées pour votre campus.",
                          "News published for your campus.",
                        )}
                      </p>
                    </div>
                    <input
                      type="checkbox"
                      checked={preferences.data.email_announcements}
                      disabled={pref.isPending}
                      onChange={(e) =>
                        pref.mutate({
                          path: "/notification-preferences",
                          method: "PATCH",
                          data: {
                            ...preferences.data,
                            email_announcements: e.target.checked,
                          },
                        })
                      }
                    />
                  </label>
                  <label className="settings-row">
                    <div>
                      <strong>
                        {t("Activité communautaire", "Community activity")}
                      </strong>
                      <p>
                        {t(
                          "Les échanges qui vous concernent.",
                          "Conversations relevant to you.",
                        )}
                      </p>
                    </div>
                    <input
                      type="checkbox"
                      checked={preferences.data.email_community}
                      disabled={pref.isPending}
                      onChange={(e) =>
                        pref.mutate({
                          path: "/notification-preferences",
                          method: "PATCH",
                          data: {
                            ...preferences.data,
                            email_community: e.target.checked,
                          },
                        })
                      }
                    />
                  </label>
                </>
              )}
            </div>
          </section>
          <section className="panel">
            <div className="panel-header">
              <h2>{t("Sécurité du compte", "Account security")}</h2>
              <ShieldCheck size={20} color="var(--teal)" />
            </div>
            <div className="panel-body">
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  const f = new FormData(e.currentTarget);
                  if (f.get("new_password") !== f.get("confirm_password")) {
                    setPasswordError(
                      new Error(
                        "Les nouveaux mots de passe ne correspondent pas.",
                      ),
                    );
                    return;
                  }
                  setPasswordError(undefined);
                  password.mutate({
                    path: "/users/me/password",
                    method: "PATCH",
                    data: {
                      current_password: f.get("current_password"),
                      new_password: f.get("new_password"),
                    },
                  });
                }}
              >
                <ErrorNotice error={passwordError || password.error} />
                <Field label={t("Mot de passe actuel", "Current password")}>
                  <input
                    type="password"
                    name="current_password"
                    autoComplete="current-password"
                    required
                  />
                </Field>
                <Field
                  label={t("Nouveau mot de passe", "New password")}
                  hint={t(
                    "Au moins 12 caractères, avec lettres et chiffres.",
                    "At least 12 characters, including letters and numbers.",
                  )}
                >
                  <input
                    type="password"
                    name="new_password"
                    autoComplete="new-password"
                    minLength={12}
                    maxLength={128}
                    required
                  />
                </Field>
                <Field
                  label={t(
                    "Confirmer le nouveau mot de passe",
                    "Confirm new password",
                  )}
                >
                  <input
                    type="password"
                    name="confirm_password"
                    autoComplete="new-password"
                    minLength={12}
                    maxLength={128}
                    required
                  />
                </Field>
                <p className="form-help">
                  {t(
                    "Vous devrez vous reconnecter après cette modification. Vos autres sessions seront également fermées.",
                    "You will need to sign in again after this change. Your other sessions will also be signed out.",
                  )}
                </p>
                <Button busy={password.isPending} variant="secondary">
                  {t("Changer le mot de passe", "Change password")}
                </Button>
              </form>
            </div>
          </section>
        </div>
      </div>
    </>
  );
}
