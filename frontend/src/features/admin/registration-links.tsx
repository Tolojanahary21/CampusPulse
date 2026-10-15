"use client";
import { useState } from "react";
import { Check, Copy, Link2 } from "lucide-react";
import { usePreferences } from "@/components/preferences";
import { useSession } from "@/components/app-shell";
import { Button, ErrorNotice, Success } from "@/components/ui";
import { mutate } from "@/lib/api";
import { label } from "@/lib/format";

type SignupRole = "STUDENT" | "CAMPUS_ADMIN" | "CONTENT_PUBLISHER" | "MODERATOR";
type LinkResult = { token: string; campus_name: string; role: SignupRole; expires_at: string };
const roles: SignupRole[] = ["STUDENT", "CONTENT_PUBLISHER", "MODERATOR", "CAMPUS_ADMIN"];

export function RegistrationLinks() {
  const { t, locale } = usePreferences();
  const { campusId, campuses } = useSession();
  const [links, setLinks] = useState<Partial<Record<SignupRole, string>>>({});
  const [busyRole, setBusyRole] = useState<SignupRole | null>(null);
  const [copied, setCopied] = useState<SignupRole | null>(null);
  const [error, setError] = useState<unknown>();
  const [success, setSuccess] = useState("");
  const campus = campuses.find((item) => item.id === campusId);

  async function createLink(role: SignupRole) {
    if (!campusId || busyRole) return;
    setBusyRole(role);
    setError(undefined);
    setSuccess("");
    try {
      const result = await mutate<LinkResult>("/platform/registration-links", "POST", { campus_id: campusId, role });
      const url = `${window.location.origin}/register?invite=${encodeURIComponent(result.token)}`;
      setLinks((current) => ({ ...current, [role]: url }));
      setSuccess(t(`Lien ${label(role, locale).toLowerCase()} créé pour ${result.campus_name}. Il expire dans 30 jours et ne peut servir qu’une fois.`, `${label(role, locale)} link created for ${result.campus_name}. It expires in 30 days and can be used once.`));
    } catch (err) {
      setError(err);
    } finally {
      setBusyRole(null);
    }
  }

  async function copyLink(selectedRole: SignupRole) {
    const value = links[selectedRole];
    if (!value) return;
    try {
      await navigator.clipboard.writeText(value);
      setCopied(selectedRole);
      window.setTimeout(() => setCopied((current) => current === selectedRole ? null : current), 1800);
    } catch {
      setError(new Error(t("La copie automatique a échoué. Sélectionnez le lien pour le copier.", "Automatic copy failed. Select the link and copy it.")));
    }
  }

  return (
    <section className="panel registration-links-panel">
      <div className="panel-header">
        <div><h2>{t("Liens d’inscription par rôle", "Role registration links")}</h2><p className="small muted">{t("Choisissez un rôle et partagez le formulaire sécurisé associé. Chaque inscription doit confirmer son adresse e-mail par OTP.", "Choose a role and share its secure signup form. Every signup must verify its email with an OTP.")}</p></div>
        <Link2 size={20} aria-hidden="true" />
      </div>
      <div className="panel-body">
        {!campus ? <p className="notice">{t("Choisissez un établissement actif dans le menu latéral.", "Choose an active campus from the sidebar.")}</p> : (
          <>
            <p className="form-help">{t("Établissement sélectionné :", "Selected campus:")} <strong>{campus.name}</strong></p>
            <div className="registration-role-links">
              {roles.map((item) => <div className="registration-role-link" key={item}>
                <div><strong>{label(item, locale)}</strong><p className="small muted">{t("Formulaire dédié avec confirmation OTP de l’adresse e-mail.", "Dedicated signup form with email OTP verification.")}</p></div>
                <Button type="button" variant={links[item] ? "secondary" : "primary"} busy={busyRole === item} disabled={!!busyRole} onClick={() => void createLink(item)}>
                  <Link2 size={16} />{links[item] ? t("Créer un nouveau lien", "Create a new link") : t("Créer le lien", "Create link")}
                </Button>
              </div>)}
            </div>
          </>
        )}
        <ErrorNotice error={error} />
        {success && <Success>{success}</Success>}
        {Object.entries(links).map(([key, value]) => {
          const item = key as SignupRole;
          return <div className="registration-link-result" key={key}>
            <strong>{label(item, locale)}</strong>
            <div className="registration-link-copy">
              <input aria-label={t(`Lien ${label(item, locale)}`, `${label(item, locale)} link`)} readOnly value={value} onFocus={(event) => event.currentTarget.select()} />
              <Button type="button" variant="secondary" onClick={() => void copyLink(item)}>{copied === item ? <Check size={16} /> : <Copy size={16} />}{copied === item ? t("Copié", "Copied") : t("Copier", "Copy")}</Button>
            </div>
          </div>;
        })}
      </div>
    </section>
  );
}
