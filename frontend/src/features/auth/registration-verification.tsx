"use client";

import { useEffect, useId, useRef, useState } from "react";
import { ArrowRight, MailCheck } from "lucide-react";
import { Button, ErrorNotice, Field, Success } from "@/components/ui";
import { usePreferences } from "@/components/preferences";
import { mutate } from "@/lib/api";

export interface RegistrationChallenge {
  challenge_id: string;
  email: string;
  expires_at: string;
  resend_available_at: string;
}

const storageKey = "campuspulse.registration-verification";

function cleanChallenge(value: unknown): RegistrationChallenge | null {
  if (!value || typeof value !== "object") return null;
  const item = value as Record<string, unknown>;
  if (
    typeof item.challenge_id !== "string" || !item.challenge_id ||
    typeof item.email !== "string" || !item.email ||
    typeof item.expires_at !== "string" || !Number.isFinite(Date.parse(item.expires_at)) ||
    typeof item.resend_available_at !== "string" || !Number.isFinite(Date.parse(item.resend_available_at))
  ) return null;
  // Persist only the metadata needed to resume verification, never form fields
  // containing a password or the one-time code.
  return {
    challenge_id: item.challenge_id,
    email: item.email,
    expires_at: item.expires_at,
    resend_available_at: item.resend_available_at,
  };
}

export function restoreRegistration(): RegistrationChallenge | null {
  try {
    const saved = sessionStorage.getItem(storageKey);
    if (!saved) return null;
    const challenge = cleanChallenge(JSON.parse(saved));
    if (!challenge) sessionStorage.removeItem(storageKey);
    return challenge;
  } catch {
    return null;
  }
}

export function rememberRegistration(value: unknown): RegistrationChallenge {
  const challenge = cleanChallenge(value);
  if (!challenge) throw new Error("La demande n’a pas pu aboutir.");
  try {
    sessionStorage.setItem(storageKey, JSON.stringify(challenge));
  } catch {
    // Verification remains usable when browser storage is unavailable.
  }
  return challenge;
}

export function forgetRegistration() {
  try {
    sessionStorage.removeItem(storageKey);
  } catch {
    // No storage permission is needed to finish or restart this flow.
  }
}

function countdown(seconds: number) {
  return `${Math.floor(seconds / 60).toString().padStart(2, "0")}:${(seconds % 60).toString().padStart(2, "0")}`;
}

export function RegistrationVerification({
  challenge,
  onChallenge,
  onVerified,
  onRestart,
}: {
  challenge: RegistrationChallenge;
  onChallenge: (value: RegistrationChallenge) => void;
  onVerified: () => void;
  onRestart: () => void;
}) {
  const { t } = usePreferences();
  const [code, setCode] = useState("");
  const [error, setError] = useState<unknown>();
  const [busy, setBusy] = useState<"verify" | "resend" | null>(null);
  const [resent, setResent] = useState(false);
  const [now, setNow] = useState(Date.now);
  const input = useRef<HTMLInputElement>(null);
  const hintId = useId();
  const remaining = Math.max(0, Math.ceil((Date.parse(challenge.expires_at) - now) / 1000));
  const cooldown = Math.max(0, Math.ceil((Date.parse(challenge.resend_available_at) - now) / 1000));

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    if (busy === null) input.current?.focus();
  }, [busy]);

  async function verify(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy || code.length !== 6 || remaining === 0) return;
    setBusy("verify");
    setError(undefined);
    try {
      await mutate("/auth/verify-email", "POST", {
        challenge_id: challenge.challenge_id,
        code,
      });
      setCode("");
      forgetRegistration();
      onVerified();
    } catch (err) {
      setError(err);
      input.current?.focus();
      input.current?.select();
    } finally {
      setBusy(null);
      setNow(Date.now());
    }
  }

  async function resend() {
    if (busy || cooldown > 0) return;
    setBusy("resend");
    setError(undefined);
    setResent(false);
    try {
      const response = await mutate<RegistrationChallenge>(
        "/auth/resend-verification", "POST", { challenge_id: challenge.challenge_id },
      );
      onChallenge(rememberRegistration(response));
      setCode("");
      setNow(Date.now());
      setResent(true);
      input.current?.focus();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="registration-verification">
      <div className="verification-destination">
        <MailCheck size={24} aria-hidden="true" />
        <div>
          <p>{t("Envoi du code demandé à", "Code delivery requested to")}</p>
          <strong>{challenge.email}</strong>
        </div>
      </div>
      <p className="small muted">
        {t(
          "Votre compte sera créé uniquement après vérification. Consultez votre boîte de réception et vos courriers indésirables ; l’email peut prendre quelques instants à arriver.",
          "Your account will only be created after verification. Check your inbox and spam folder; the email may take a few moments to arrive.",
        )}
      </p>
      <form onSubmit={verify}>
        <ErrorNotice error={error} />
        {resent && (
          <Success>{t(
            "L’envoi d’un nouveau code a été demandé. Seul le code le plus récent est valable.",
            "Delivery of a new code has been requested. Only the latest code is valid.",
          )}</Success>
        )}
        <Field label={t("Code de vérification", "Verification code")}>
          <input
            ref={input}
            data-testid="otp-code"
            className="verification-code"
            name="code"
            type="text"
            inputMode="numeric"
            autoComplete="one-time-code"
            pattern="[0-9]{6}"
            minLength={6}
            maxLength={6}
            required
            value={code}
            disabled={busy !== null}
            aria-describedby={hintId}
            onChange={(event) => setCode(event.target.value.replace(/\D/g, "").slice(0, 6))}
            onPaste={(event) => {
              event.preventDefault();
              setCode(event.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6));
            }}
          />
        </Field>
        <p id={hintId} className="small muted verification-timing">
          {t("Saisissez les 6 chiffres reçus par email.", "Enter the 6 digits received by email.")}
          {remaining > 0 && (
            <span role="timer" aria-live="off">
              {t(`Code valable encore ${countdown(remaining)}.`, `Code valid for ${countdown(remaining)}.`)}
            </span>
          )}
        </p>
        {remaining === 0 && (
          <p className="notice" role="status">
            {t("Ce code a expiré. Demandez un nouveau code ci-dessous.", "This code has expired. Request a new code below.")}
          </p>
        )}
        <Button
          type="submit"
          data-testid="verify-email"
          busy={busy === "verify"}
          disabled={busy !== null || code.length !== 6 || remaining === 0}
          className="full-width"
        >
          {t("Vérifier et créer mon compte", "Verify and create my account")}
          <ArrowRight size={17} />
        </Button>
      </form>
      <div className="verification-actions">
        <Button
          type="button"
          variant="secondary"
          data-testid="resend-code"
          busy={busy === "resend"}
          disabled={busy !== null || cooldown > 0}
          onClick={() => void resend()}
        >
          {t("Renvoyer un code", "Resend code")}
        </Button>
        <Button
          type="button"
          variant="ghost"
          data-testid="change-registration"
          disabled={busy !== null}
          onClick={() => { forgetRegistration(); onRestart(); }}
        >
          {t("Modifier mon inscription", "Change my registration")}
        </Button>
      </div>
      <p className="small muted verification-cooldown" aria-live="off">
        {cooldown > 0
          ? t(`Renvoi disponible dans ${cooldown} s.`, `Resend available in ${cooldown}s.`)
          : t("Vous pouvez demander un nouveau code si nécessaire.", "You can request a new code if needed.")}
      </p>
    </div>
  );
}
