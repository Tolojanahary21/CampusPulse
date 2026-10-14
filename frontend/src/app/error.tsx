"use client";
import { Button } from "@/components/ui";
import { PreferenceControls, usePreferences } from "@/components/preferences";
export default function ErrorPage({
  reset,
}: {
  error: Error;
  reset: () => void;
}) {
  const { t } = usePreferences();
  return (
    <main className="not-found">
      <PreferenceControls />
      <h1>{t("Un imprévu est survenu.", "Something went wrong.")}</h1>
      <p>
        {t(
          "Rechargez cet espace pour reprendre votre navigation.",
          "Reload this page to continue browsing.",
        )}
      </p>
      <Button onClick={reset}>{t("Réessayer", "Try again")}</Button>
    </main>
  );
}
