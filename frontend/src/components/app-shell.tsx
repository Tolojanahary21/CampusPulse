"use client";
import { createContext, useContext, useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Bell,
  BookOpen,
  CalendarDays,
  ChevronDown,
  GraduationCap,
  LayoutDashboard,
  LogOut,
  Megaphone,
  Menu,
  School,
  Settings2,
  Shield,
  UserRound,
  Users,
  X,
} from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { api, ApiError, mutate } from "@/lib/api";
import { canRole, initials, label } from "@/lib/format";
import { useData } from "@/hooks/use-data";
import type { Campus, Collection, User } from "@/types";
import { Button, ErrorNotice, Loading } from "./ui";
import { PreferenceControls, usePreferences } from "./preferences";
interface Session {
  user: User;
  campusId: string;
  campuses: Campus[];
  canPublish: boolean;
  canManage: boolean;
  canModerate: boolean;
  isPlatform: boolean;
}
const Context = createContext<Session | null>(null);
export function useSession() {
  const context = useContext(Context);
  if (!context) throw new Error("Session absente");
  return context;
}
const nav = [
  {
    href: "/app",
    label: "Vue d’ensemble",
    english: "Overview",
    icon: LayoutDashboard,
  },
  {
    href: "/app/announcements",
    label: "Annonces officielles",
    english: "Official announcements",
    icon: Megaphone,
  },
  {
    href: "/app/documents",
    label: "Bibliothèque",
    english: "Library",
    icon: BookOpen,
  },
  {
    href: "/app/community",
    label: "Communauté",
    english: "Community",
    icon: Users,
  },
  {
    href: "/app/events",
    label: "Événements",
    english: "Events",
    icon: CalendarDays,
  },
  {
    href: "/app/notifications",
    label: "Notifications",
    english: "Notifications",
    icon: Bell,
  },
];
export function AppShell({ children }: { children: React.ReactNode }) {
  const { t, locale } = usePreferences();
  const { data: user, error, isPending } = useData<User>("/auth/me");
  const isPlatform = canRole(user, []);
  const { data: allCampuses } = useData<Collection<Campus>>(
    "/platform/campuses?page_size=100",
    isPlatform,
  );
  const [selected, setSelected] = useState("");
  const [mobile, setMobile] = useState(false);
  const [logoutError, setLogoutError] = useState<unknown>();
  const [loggingOut, setLoggingOut] = useState(false);
  const router = useRouter();
  const pathname = usePathname();
  const activeNav = nav.find((n) => n.href === pathname);
  const client = useQueryClient();
  const campuses = isPlatform
    ? allCampuses?.items || user?.campuses || []
    : user?.campuses || [];
  const campusId = campuses.some((c) => c.id === selected)
    ? selected
    : campuses[0]?.id || "";
  useEffect(() => {
    if (error instanceof ApiError && error.status === 401)
      router.replace("/login");
  }, [error, router]);
  useEffect(() => {
    const expired = () => {
      client.clear();
      router.replace("/login");
    };
    window.addEventListener("session-expired", expired);
    return () => window.removeEventListener("session-expired", expired);
  }, [client, router]);
  useEffect(() => setMobile(false), [pathname]);
  async function logout() {
    setLoggingOut(true);
    try {
      await mutate("/auth/logout", "POST");
      client.clear();
      router.replace("/login");
    } catch (e) {
      setLogoutError(e);
      setLoggingOut(false);
    }
  }
  if (isPending) return <Loading />;
  if (!user)
    return (
      <main className="standalone-error">
        <ErrorNotice error={error} />
        <Button
          onClick={() => {
            void client.invalidateQueries();
          }}
        >
          {t("Réessayer", "Try again")}
        </Button>
        <Link href="/login">{t("Se connecter", "Sign in")}</Link>
      </main>
    );
  const session = {
    user,
    campuses,
    campusId,
    isPlatform,
    canPublish: canRole(user, ["CAMPUS_ADMIN", "CONTENT_PUBLISHER"], campusId),
    canManage: canRole(user, ["CAMPUS_ADMIN"], campusId),
    canModerate: canRole(user, ["CAMPUS_ADMIN", "MODERATOR"], campusId),
  };
  return (
    <Context.Provider value={session}>
      <div className="app-layout">
        <a href="#main-content" className="skip-link">
          {t("Aller au contenu", "Skip to content")}
        </a>
        {mobile && (
          <button
            className="sidebar-scrim"
            aria-label={t("Fermer la navigation", "Close navigation")}
            onClick={() => setMobile(false)}
          />
        )}
        <aside className={`sidebar ${mobile ? "open" : ""}`}>
          <Link href="/app" className="brand">
            <span className="brand-symbol">
              <GraduationCap size={27} />
            </span>
            Campus<span>Pulse</span>
          </Link>
          <div className="campus-selector">
            <School size={20} />
            <div>
              <small>{t("MON ÉTABLISSEMENT", "MY INSTITUTION")}</small>
              <select
                aria-label={t("Établissement actif", "Active institution")}
                value={campusId}
                onChange={(e) => setSelected(e.target.value)}
              >
                {campuses.length ? (
                  campuses.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))
                ) : (
                  <option value="">
                    {t("Aucun établissement", "No institution")}
                  </option>
                )}
              </select>
            </div>
            <ChevronDown size={15} />
          </div>
          <p className="nav-label">{t("MON CAMPUS", "MY CAMPUS")}</p>
          <nav>
            {nav.map(({ href, label: caption, english, icon: Icon }) => (
              <Link
                key={href}
                className={`nav-link ${pathname === href || (href !== "/app" && pathname.startsWith(href + "/")) ? "active" : ""}`}
                href={href}
              >
                <Icon size={20} />
                {t(caption, english)}
              </Link>
            ))}
          </nav>
          {(session.canManage || session.canModerate || isPlatform) && (
            <>
              <p className="nav-label">ADMINISTRATION</p>
              <nav>
                {(session.canManage || session.canModerate) && (
                  <Link
                    className={`nav-link ${pathname === "/app/admin" ? "active" : ""}`}
                    href="/app/admin"
                  >
                    <Settings2 size={20} />
                    {t("Mon établissement", "My institution")}
                  </Link>
                )}
                {isPlatform && (
                  <Link
                    className={`nav-link ${pathname === "/app/platform" ? "active" : ""}`}
                    href="/app/platform"
                  >
                    <Shield size={20} />
                    {t("Plateforme", "Platform")}
                  </Link>
                )}
              </nav>
            </>
          )}
          <div className="sidebar-bottom">
            <div className="sidebar-note">
              <span className="online-dot" />
              {t(
                "Un campus. Mille possibilités.",
                "One campus. Endless possibilities.",
              )}
              <p>
                {t(
                  "Restez curieux, restez connectés.",
                  "Stay curious. Stay connected.",
                )}
              </p>
            </div>
            <Link href="/app/profile" className="sidebar-profile">
              <span className="avatar">
                {initials(user.first_name, user.last_name)}
              </span>
              <div>
                <strong>
                  {user.first_name} {user.last_name}
                </strong>
                <small>
                  {label(
                    user.roles.find(
                      (r) =>
                        r.campus_id === campusId || r.role === "PLATFORM_ADMIN",
                    )?.role || "STUDENT",
                    locale,
                  )}
                </small>
              </div>
              <UserRound size={17} />
            </Link>
          </div>
        </aside>
        <div className="workspace">
          <header className="topbar">
            <button
              className="icon-button mobile-menu"
              aria-label={
                mobile
                  ? t("Fermer le menu", "Close menu")
                  : t("Ouvrir le menu", "Open menu")
              }
              aria-expanded={mobile}
              onClick={() => setMobile(!mobile)}
            >
              {mobile ? <X size={22} /> : <Menu size={22} />}
            </button>
            <div className="breadcrumb">
              {t("Mon espace", "My workspace")} <span>/</span>
              <strong>
                {activeNav
                  ? t(activeNav.label, activeNav.english)
                  : "CampusPulse"}
              </strong>
            </div>
            <div className="topbar-actions">
              <span className="today">
                {new Intl.DateTimeFormat(locale === "fr" ? "fr-FR" : "en-GB", {
                  weekday: "long",
                  day: "numeric",
                  month: "long",
                }).format(new Date())}
              </span>
              <PreferenceControls />
              <Link
                href="/app/notifications"
                className="icon-button"
                aria-label="Notifications"
              >
                <Bell size={20} />
              </Link>
              <Link
                href="/app/profile"
                className="avatar small-avatar"
                aria-label={t("Mon profil", "My profile")}
              >
                {initials(user.first_name, user.last_name)}
              </Link>
              <button
                className="icon-button"
                onClick={logout}
                disabled={loggingOut}
                aria-label={t("Se déconnecter", "Sign out")}
              >
                <LogOut size={18} />
              </button>
            </div>
          </header>
          <main id="main-content" className="page-content">
            <ErrorNotice error={logoutError} />
            {children}
          </main>
          <footer className="workspace-footer">
            CampusPulse{" "}
            <span>
              {t(
                "Apprendre, partager, avancer ensemble.",
                "Learn, share and move forward together.",
              )}
            </span>
          </footer>
        </div>
      </div>
    </Context.Provider>
  );
}
