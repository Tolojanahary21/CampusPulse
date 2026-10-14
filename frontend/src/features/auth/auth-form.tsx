"use client";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ArrowRight, BookOpen, GraduationCap, ShieldCheck } from "lucide-react";
import { mutate } from "@/lib/api";
import { Button, ErrorNotice, Field, Success } from "@/components/ui";
import { useData } from "@/hooks/use-data";
import type { Campus } from "@/types";
import { PreferenceControls, usePreferences } from "@/components/preferences";
import {
  RegistrationVerification,
  rememberRegistration,
  restoreRegistration,
  type RegistrationChallenge,
} from "./registration-verification";
type Mode =
  | "login"
  | "register"
  | "forgot-password"
  | "reset-password"
  | "accept-invitation";
interface RegistrationOptions {
  enabled: boolean;
  campuses: Pick<Campus, "id" | "name" | "code">[];
}
const texts: Record<
  Mode,
  { title: string; description: string; button: string }
> = {
  login: {
    title: "Bienvenue chez vous.",
    description: "Connectez-vous pour retrouver la vie de votre campus.",
    button: "Se connecter",
  },
  register: {
    title: "Votre vie étudiante commence ici.",
    description:
      "Créez votre compte étudiant et rejoignez la communauté de votre établissement.",
    button: "Créer mon compte étudiant",
  },
  "forgot-password": {
    title: "Un nouveau départ.",
    description:
      "Nous vous enverrons un lien pour réinitialiser votre mot de passe.",
    button: "Envoyer le lien",
  },
  "reset-password": {
    title: "Choisissez votre mot de passe.",
    description: "Un mot de passe solide protège votre espace universitaire.",
    button: "Enregistrer le mot de passe",
  },
  "accept-invitation": {
    title: "Votre campus vous attend.",
    description:
      "Finalisez votre invitation en choisissant votre mot de passe.",
    button: "Activer mon compte",
  },
};
const englishTexts: typeof texts = {
  login: {
    title: "Welcome back.",
    description: "Sign in and reconnect with your campus.",
    button: "Sign in",
  },
  register: {
    title: "Your student journey starts here.",
    description:
      "Create your student account and join your institution’s community.",
    button: "Create my student account",
  },
  "forgot-password": {
    title: "A fresh start.",
    description: "We will email you a link to reset your password.",
    button: "Send reset link",
  },
  "reset-password": {
    title: "Choose your password.",
    description: "A strong password protects your university workspace.",
    button: "Save password",
  },
  "accept-invitation": {
    title: "Your campus is waiting.",
    description: "Complete your invitation by choosing your password.",
    button: "Activate my account",
  },
};
export function AuthForm({ mode }: { mode: Mode }) {
  const { t, locale } = usePreferences();
  const router = useRouter();
  const search = useSearchParams();
  const client = useQueryClient();
  const [error, setError] = useState<unknown>();
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [challenge, setChallenge] = useState<RegistrationChallenge | null>(null);
  const [registrationRestored, setRegistrationRestored] = useState(mode !== "register");
  useEffect(() => {
    if (mode === "register") setChallenge(restoreRegistration());
    setRegistrationRestored(true);
  }, [mode]);
  const registration = useData<RegistrationOptions>(
    "/auth/registration-options",
    mode === "register",
  );
  const canRegister =
    registration.data?.enabled && registration.data.campuses.length > 0;
  const text = (locale === "fr" ? texts : englishTexts)[mode];
  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (mode === "register" && !canRegister) return;
    const element = e.currentTarget;
    const form = new FormData(element);
    const password = String(form.get("password") || "");
    if (
      mode !== "login" &&
      mode !== "forgot-password" &&
      password !== form.get("confirm")
    ) {
      setError(new Error("Les mots de passe ne correspondent pas."));
      return;
    }
    setBusy(true);
    setError(undefined);
    try {
      const response = await mutate(
        `/auth/${mode}`,
        "POST",
        mode === "login"
          ? { email: form.get("email"), password }
          : mode === "register"
            ? {
                first_name: String(form.get("first_name") || "").trim(),
                last_name: String(form.get("last_name") || "").trim(),
                email: form.get("email"),
                password,
                campus_id: form.get("campus_id"),
              }
            : mode === "forgot-password"
              ? { email: form.get("email") }
              : { token: search.get("token") || form.get("token"), password },
      );
      if (mode === "login") {
        client.clear();
        router.replace("/app");
      } else if (mode === "register") {
        // The account does not exist yet. Clear passwords before presenting OTP.
        element.reset();
        setChallenge(rememberRegistration(response));
      } else setDone(true);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="auth-layout">
      <aside className="auth-story">
        <Link href="/" className="brand">
          <span className="brand-symbol">
            <GraduationCap size={28} />
          </span>
          Campus<span>Pulse</span>
        </Link>
        <div>
          <span className="pill">
            {t("LE CAMPUS, EN UN MÊME LIEU", "YOUR CAMPUS, ALL IN ONE PLACE")}
          </span>
          <h1>
            {t("Votre quotidien.", "Your everyday.")}
            <br />
            {t("Votre communauté.", "Your community.")}
            <br />
            <em>{t("Votre avenir.", "Your future.")}</em>
          </h1>
          <p>
            {t(
              "L’essentiel de votre vie universitaire, au bon endroit et au bon moment.",
              "The essentials of university life, in the right place at the right time.",
            )}
          </p>
          <div className="auth-art" aria-hidden="true">
            <div className="orbit orbit-one" />
            <div className="orbit orbit-two" />
            <div className="art-card">
              <BookOpen size={36} />
              <span>
                {t("Apprendre.", "Learn.")}
                <br />
                <strong>{t("Partager. Grandir.", "Share. Grow.")}</strong>
              </span>
            </div>
            <span className="art-dot" />
          </div>
        </div>
        <span className="small">
          {t(
            "CampusPulse · Le lien qui fait vivre votre campus",
            "CampusPulse · Bringing your campus together",
          )}
        </span>
      </aside>
      <section className="auth-main">
        <div className="auth-topbar">
          <Link href="/" className="back-link">
            {t("← Retour à l’accueil", "← Back to home")}
          </Link>
          <PreferenceControls />
        </div>
        <div className="auth-form">
          <p className="eyebrow">
            {t("VOTRE ESPACE UNIVERSITAIRE", "YOUR UNIVERSITY WORKSPACE")}
          </p>
          <h1>{mode === "register" && challenge && !done
            ? t("Vérifiez votre adresse email.", "Verify your email address.")
            : text.title}</h1>
          <p className="muted">{mode === "register" && challenge && !done
            ? t("Une dernière étape pour rejoindre votre campus.", "One last step before joining your campus.")
            : text.description}</p>
          {done ? (
            <>
              <Success>
                {mode === "forgot-password"
                  ? t(
                      "Si un compte correspond à cette adresse, un email vous sera envoyé. Consultez également vos courriers indésirables.",
                      "If an account matches this address, we will send you an email. Please also check your spam folder.",
                    )
                  : mode === "register"
                    ? t(
                        "Votre compte étudiant a été créé. Connectez-vous avec votre adresse email et votre mot de passe. L’administration pourra ensuite vous inscrire dans votre filière et votre niveau.",
                        "Your student account has been created. Sign in with your email and password. Your administrator can then enrol you in your programme and year level.",
                      )
                    : t(
                        "Votre mot de passe a été enregistré. Vous pouvez maintenant vous connecter.",
                        "Your password has been saved. You can now sign in.",
                      )}
              </Success>
              <Link className="button primary" href="/login">
                {t("Retour à la connexion", "Back to sign in")}{" "}
                <ArrowRight size={16} />
              </Link>
            </>
          ) : mode === "register" && !registrationRestored ? (
            <p className="notice" role="status">
              {t("Chargement de votre inscription…", "Loading your registration…")}
            </p>
          ) : mode === "register" && challenge ? (
            <RegistrationVerification
              challenge={challenge}
              onChallenge={setChallenge}
              onVerified={() => { setChallenge(null); setDone(true); }}
              onRestart={() => { setChallenge(null); setError(undefined); }}
            />
          ) : mode === "register" && registration.isPending ? (
            <p className="notice" role="status">
              {t("Chargement des établissements…", "Loading institutions…")}
            </p>
          ) : mode === "register" && registration.error ? (
            <>
              <ErrorNotice error={registration.error} />
              <Button
                variant="secondary"
                busy={registration.isFetching}
                onClick={() => void registration.refetch()}
              >
                {t("Réessayer", "Try again")}
              </Button>
            </>
          ) : mode === "register" && !canRegister ? (
            <p className="notice" role="status">
              {registration.data?.enabled
                ? t(
                    "Aucun établissement n’est ouvert aux inscriptions pour le moment. Contactez l’administration de votre établissement.",
                    "No institutions are accepting registrations at the moment. Contact your institution’s administration.",
                  )
                : t(
                    "Les inscriptions étudiantes sont temporairement fermées. Contactez l’administration de votre établissement.",
                    "Student registration is temporarily closed. Contact your institution’s administration.",
                  )}
            </p>
          ) : (
            <form onSubmit={submit}>
              <ErrorNotice error={error} />
              {mode === "register" && (
                <>
                  <div className="form-grid">
                    <Field label={t("Prénom", "First name")}>
                      <input
                        name="first_name"
                        autoComplete="given-name"
                        required
                        maxLength={100}
                      />
                    </Field>
                    <Field label={t("Nom", "Last name")}>
                      <input
                        name="last_name"
                        autoComplete="family-name"
                        required
                        maxLength={100}
                      />
                    </Field>
                  </div>
                  <Field label={t("Votre établissement", "Your institution")}>
                    <select name="campus_id" required defaultValue="">
                      <option value="" disabled>
                        {t(
                          "Choisir mon établissement",
                          "Choose my institution",
                        )}
                      </option>
                      {registration.data?.campuses.map((campus) => (
                        <option key={campus.id} value={campus.id}>
                          {campus.name} ({campus.code})
                        </option>
                      ))}
                    </select>
                  </Field>
                </>
              )}
              {(mode === "login" ||
                mode === "register" ||
                mode === "forgot-password") && (
                <Field label={t("Adresse email", "Email address")}>
                  <input
                    type="email"
                    name="email"
                    autoComplete="email"
                    placeholder={t(
                      "prenom.nom@universite.mg",
                      "first.last@university.edu",
                    )}
                    required
                    maxLength={255}
                  />
                </Field>
              )}
              {mode !== "login" &&
                mode !== "register" &&
                mode !== "forgot-password" &&
                !search.get("token") && (
                  <Field
                    label={t("Jeton reçu par email", "Token received by email")}
                  >
                    <input name="token" required autoComplete="off" />
                  </Field>
                )}
              {mode !== "forgot-password" && (
                <Field
                  label={t("Mot de passe", "Password")}
                  hint={
                    mode !== "login"
                      ? t("Au moins 12 caractères.", "At least 12 characters.")
                      : undefined
                  }
                >
                  <input
                    type="password"
                    name="password"
                    autoComplete={
                      mode === "login" ? "current-password" : "new-password"
                    }
                    minLength={mode === "login" ? 1 : 12}
                    required
                    maxLength={128}
                  />
                </Field>
              )}
              {mode !== "login" && mode !== "forgot-password" && (
                <Field
                  label={t("Confirmer le mot de passe", "Confirm password")}
                >
                  <input
                    type="password"
                    name="confirm"
                    autoComplete="new-password"
                    minLength={12}
                    required
                    maxLength={128}
                  />
                </Field>
              )}
              {mode === "login" && (
                <Link href="/forgot-password" className="forgot-link">
                  {t("Mot de passe oublié ?", "Forgot password?")}
                </Link>
              )}
              <Button type="submit" busy={busy} className="full-width">
                {text.button}
                <ArrowRight size={17} />
              </Button>
            </form>
          )}
          <div className="auth-note">
            <ShieldCheck size={19} />
            <span>
              {t(
                "Un espace privé, réservé aux membres de votre établissement.",
                "A private workspace for members of your institution.",
              )}
            </span>
          </div>
          {mode === "login" && (
            <p className="small muted">
              {t("Vous êtes étudiant ?", "Are you a student?")}{" "}
              <Link href="/register" className="auth-text-link">
                {t("Créer mon compte étudiant", "Create my student account")}
              </Link>
            </p>
          )}
          {mode === "register" && (
            <p className="small muted">
              {t("Déjà inscrit ?", "Already registered?")}{" "}
              <Link href="/login" className="auth-text-link">
                {t("Se connecter", "Sign in")}
              </Link>
            </p>
          )}
          {(mode === "login" || mode === "register") && (
            <p className="small muted auth-staff-note">
              {t(
                "Les comptes des responsables sont créés sur invitation par l’administration.",
                "Staff accounts are created by invitation from the administration.",
              )}
            </p>
          )}
        </div>
        <p className="small muted auth-footer">
          {t(
            "Une plateforme conçue pour apprendre ensemble.",
            "A platform designed for learning together.",
          )}
        </p>
      </section>
    </main>
  );
}
