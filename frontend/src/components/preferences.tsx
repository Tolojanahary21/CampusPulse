"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { Globe2, Moon, Sun } from "lucide-react";
import { usePathname } from "next/navigation";

export type Locale = "fr" | "en";
export type Theme = "light" | "dark";
type Preferences = {
  locale: Locale;
  theme: Theme;
  setLocale: (value: Locale) => void;
  setTheme: (value: Theme) => void;
  t: (french: string, english: string) => string;
};
const Context = createContext<Preferences | null>(null);

export function PreferencesProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  // Stable server defaults keep the first hydrated tree identical to the HTML.
  const [locale, updateLocale] = useState<Locale>("fr");
  const [theme, updateTheme] = useState<Theme>("light");
  const setLocale = useCallback((value: Locale) => {
    updateLocale(value);
    document.documentElement.lang = value;
    try {
      localStorage.setItem("campuspulse.locale", value);
    } catch {
      /* Storage may be unavailable. */
    }
  }, []);
  const setTheme = useCallback((value: Theme) => {
    updateTheme(value);
    document.documentElement.dataset.theme = value;
    document.documentElement.style.colorScheme = value;
    try {
      localStorage.setItem("campuspulse.theme", value);
    } catch {
      /* Keep the current preference in memory. */
    }
  }, []);
  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const load = () => {
      let language: Locale = "fr";
      let appearance: Theme = media.matches ? "dark" : "light";
      try {
        const savedLocale = localStorage.getItem("campuspulse.locale");
        const savedTheme = localStorage.getItem("campuspulse.theme");
        if (savedLocale === "en" || savedLocale === "fr")
          language = savedLocale;
        if (savedTheme === "dark" || savedTheme === "light")
          appearance = savedTheme;
      } catch {
        /* Browser privacy settings must not prevent navigation. */
      }
      updateLocale(language);
      updateTheme(appearance);
      document.documentElement.lang = language;
      document.documentElement.dataset.theme = appearance;
      document.documentElement.style.colorScheme = appearance;
    };
    const sync = (event: StorageEvent) => {
      if (!event.key || event.key.startsWith("campuspulse.")) load();
    };
    load();
    window.addEventListener("storage", sync);
    media.addEventListener("change", load);
    return () => {
      window.removeEventListener("storage", sync);
      media.removeEventListener("change", load);
    };
  }, []);
  const t = useCallback(
    (french: string, english: string) => (locale === "fr" ? french : english),
    [locale],
  );
  const value = useMemo(
    () => ({ locale, theme, setLocale, setTheme, t }),
    [locale, theme, setLocale, setTheme, t],
  );
  return (
    <Context.Provider value={value}>
      <LocalizedPageMetadata />
      {children}
    </Context.Provider>
  );
}

const pageTitles: Record<string, [string, string]> = {
  "/": ["Votre campus, connecté", "Your campus, connected"],
  "/login": ["Connexion", "Sign in"],
  "/register": ["Créer mon compte étudiant", "Create my student account"],
  "/forgot-password": ["Mot de passe oublié", "Forgot password"],
  "/reset-password": ["Nouveau mot de passe", "New password"],
  "/accept-invitation": ["Activer mon compte", "Activate my account"],
  "/app": ["Mon campus", "My campus"],
  "/app/announcements": ["Annonces", "Announcements"],
  "/app/documents": ["Bibliothèque", "Library"],
  "/app/community": ["Communauté", "Community"],
  "/app/events": ["Événements", "Events"],
  "/app/notifications": ["Notifications", "Notifications"],
  "/app/profile": ["Mon profil", "My profile"],
  "/app/admin": ["Administration", "Administration"],
  "/app/platform": ["Plateforme", "Platform"],
};

function LocalizedPageMetadata() {
  const pathname = usePathname();
  const { t } = usePreferences();
  const key = pageTitles[pathname]
    ? pathname
    : pathname.split("/").slice(0, 3).join("/");
  const titles = pageTitles[key];
  // React 19 places these in <head>, including during server rendering.
  // Keep a single owner so route metadata cannot overwrite the chosen language.
  return (
    <>
      <title>{titles ? `${t(...titles)} · CampusPulse` : "CampusPulse"}</title>
      <meta
        name="description"
        content={t(
          "Les informations de votre établissement, vos ressources pédagogiques et votre communauté, réunies au même endroit.",
          "Your institution’s updates, learning resources and community, together in one place.",
        )}
      />
    </>
  );
}

export function usePreferences() {
  const context = useContext(Context);
  if (!context) throw new Error("PreferencesProvider is missing.");
  return context;
}

export function PreferenceControls({ className = "" }: { className?: string }) {
  const { locale, theme, setLocale, setTheme, t } = usePreferences();
  const themeLabel =
    theme === "light"
      ? t("Activer le mode sombre", "Switch to dark mode")
      : t("Activer le mode clair", "Switch to light mode");
  return (
    <div className={`preference-controls ${className}`}>
      <label className="language-control">
        <Globe2 size={16} aria-hidden="true" />
        <span className="sr-only">
          {t("Langue de l’interface", "Interface language")}
        </span>
        <select
          data-testid="language-select"
          value={locale}
          onChange={(event) => setLocale(event.target.value as Locale)}
        >
          <option value="fr" lang="fr">
            FR
          </option>
          <option value="en" lang="en">
            EN
          </option>
        </select>
      </label>
      <button
        className="theme-control"
        type="button"
        data-testid="theme-toggle"
        aria-label={themeLabel}
        title={themeLabel}
        onClick={() => setTheme(theme === "light" ? "dark" : "light")}
      >
        {theme === "light" ? (
          <Moon size={18} aria-hidden="true" />
        ) : (
          <Sun size={18} aria-hidden="true" />
        )}
      </button>
    </div>
  );
}
