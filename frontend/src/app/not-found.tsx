"use client";
import Link from "next/link";
import { PreferenceControls, usePreferences } from "@/components/preferences";
export default function NotFound() {
  const { t } = usePreferences();
  return (
    <main className="not-found">
      <PreferenceControls />
      <p className="eyebrow">{t("ERREUR 404", "ERROR 404")}</p>
      <h1>
        {t(
          "Cette page a pris un autre chemin.",
          "This page has taken another path.",
        )}
      </h1>
      <p>
        {t(
          "Retrouvez les informations et ressources de votre campus depuis votre espace.",
          "Find your campus information and resources in your workspace.",
        )}
      </p>
      <Link className="button primary" href="/app">
        {t("Retour à mon espace", "Back to my workspace")}
      </Link>
    </main>
  );
}
