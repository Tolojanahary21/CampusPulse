"use client";
import { usePreferences } from "@/components/preferences";
import Link from "next/link";
import {
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  CalendarDays,
  FileText,
  Megaphone,
  Pin,
  Sparkles,
  Users,
} from "lucide-react";
import { useSession } from "@/components/app-shell";
import { Badge, Empty, ErrorNotice, Loading, PageTitle } from "@/components/ui";
import { CampusArt } from "@/components/campus-art";
import { useData } from "@/hooks/use-data";
import { date, params } from "@/lib/format";
import type { Collection } from "@/types";
export function DashboardPage() {
  const { t, locale } = usePreferences();
  const { user, campusId, isPlatform, canManage } = useSession();
  const query = params({ campus_id: campusId });
  const summary = useData<Record<string, number>>(`/dashboard/summary${query}`);
  const announcements = useData<Collection>(
    `/announcements${params({ campus_id: campusId, page_size: 3 })}`,
  );
  const events = useData<Collection>(
    `/events${params({ campus_id: campusId, page_size: 3 })}`,
  );
  const activity = useData<Collection>(
    `/dashboard/activity${params({ campus_id: campusId, page_size: 4 })}`,
  );
  const stats = isPlatform
    ? [
        {
          key: "campuses",
          label: t("Établissements", "Institutions"),
          icon: Users,
        },
        { key: "students", label: t("Étudiants", "Students"), icon: Users },
        {
          key: "announcements",
          label: t("Annonces publiées", "Published announcements"),
          icon: Megaphone,
        },
        {
          key: "documents",
          label: t("Documents partagés", "Shared documents"),
          icon: BookOpen,
        },
      ]
    : [
        {
          key: "announcements",
          label: t("Annonces disponibles", "Available announcements"),
          icon: Megaphone,
        },
        {
          key: "documents",
          label: t("Ressources pédagogiques", "Learning resources"),
          icon: BookOpen,
        },
        { key: "events", label: t("Événements", "Events"), icon: CalendarDays },
        {
          key: canManage ? "students" : "unread_notifications",
          label: canManage
            ? t("Étudiants du campus", "Campus students")
            : t("Notifications non lues", "Unread notifications"),
          icon: Users,
        },
      ];
  return (
    <>
      <PageTitle
        eyebrow={t("HEUREUX DE VOUS RETROUVER", "WELCOME BACK")}
        title={t("Votre campus, en un regard.", "Your campus at a glance.")}
        description={t(
          "Les dernières nouvelles et tout ce dont vous avez besoin pour avancer.",
          "The latest news and everything you need to move forward.",
        )}
      />
      <section className="dashboard-hero">
        <div>
          <p
            className="eyebrow"
            style={{ margin: "0 0 9px", color: "var(--teal)" }}
          >
            {t(
              "L’ESSENTIEL, AU BON ENDROIT",
              "EVERYTHING YOU NEED, IN ONE PLACE",
            )}
          </p>
          <h2>
            {t("Bonjour", "Hello")} {user.first_name}{" "}
            <span aria-hidden="true">☀</span>
            <br />
            {t("Une belle journée commence ici.", "A great day starts here.")}
          </h2>
          <p>
            {t(
              "Une information à découvrir, une ressource à explorer, une idée à partager.",
              "News to discover, resources to explore, ideas to share.",
            )}
          </p>
          <Link href="/app/announcements" className="button primary">
            {t("Les nouvelles du campus", "Campus news")}{" "}
            <ArrowRight size={15} />
          </Link>
        </div>
        <CampusArt />
      </section>
      <ErrorNotice error={summary.error} />
      <div className="stats-grid">
        {stats.map(({ key, label: caption, icon: Icon }) => (
          <article className="stat-card" key={key}>
            <span className="stat-icon">
              <Icon size={22} />
            </span>
            <div>
              <div className="stat-value">
                {summary.isPending ? "…" : (summary.data?.[key] ?? "—")}
              </div>
              <div className="stat-label">{caption}</div>
            </div>
          </article>
        ))}
      </div>
      <div className="dashboard-grid">
        <div className="stack">
          <section className="panel">
            <div className="panel-header">
              <div>
                <h2>{t("À la une du campus", "Campus highlights")}</h2>
                <p className="muted">
                  {t(
                    "Vos informations officielles les plus récentes",
                    "Your latest official updates",
                  )}
                </p>
              </div>
              <Link href="/app/announcements" className="text-link">
                {t("Tout voir", "View all")} <ArrowUpRight size={14} />
              </Link>
            </div>
            <ErrorNotice error={announcements.error} />
            {announcements.isPending ? (
              <Loading />
            ) : !announcements.data?.items.length ? (
              <Empty
                title={t(
                  "Le fil prend bientôt vie",
                  "Your feed is coming soon",
                )}
                description={t(
                  "Les annonces officielles de votre établissement apparaîtront ici.",
                  "Official announcements from your institution will appear here.",
                )}
              />
            ) : (
              announcements.data.items.map((item) => (
                <Link
                  className="announcement-row"
                  key={item.id}
                  href={`/app/announcements/${item.id}`}
                >
                  <div className="meta-row">
                    <Badge value={item.announcement_type} />
                    <span>{date(item.created_at, false, locale)}</span>
                    {!!item.is_pinned && <Pin size={12} />}
                  </div>
                  <h3>{String(item.title)}</h3>
                  <p>{String(item.summary || item.content)}</p>
                  <div className="row-footer">
                    <span>
                      {String(
                        item.author_name ||
                          t(
                            "L’administration de votre établissement",
                            "Your institution’s administration",
                          ),
                      )}
                    </span>
                    <ArrowUpRight size={15} />
                  </div>
                </Link>
              ))
            )}
          </section>
          <div>
            <div className="section-heading">
              <h2>
                {t(
                  "Un accès direct à l’essentiel",
                  "Quick access to your essentials",
                )}
              </h2>
            </div>
            <div className="quick-links">
              <Link href="/app/documents" className="quick-link">
                <BookOpen size={20} />
                {t("Mes ressources", "My resources")}
                <ArrowUpRight size={14} />
              </Link>
              <Link href="/app/profile" className="quick-link">
                <FileText size={20} />
                {t("Mon parcours", "My studies")}
                <ArrowUpRight size={14} />
              </Link>
              <Link href="/app/community" className="quick-link">
                <Users size={20} />
                {t("La communauté", "Community")}
                <ArrowUpRight size={14} />
              </Link>
            </div>
          </div>
          {!!activity.data?.items.length && (
            <section className="panel">
              <div className="panel-header">
                <h2>{t("Le campus en mouvement", "Campus activity")}</h2>
              </div>
              {activity.data.items.map((item) => (
                <div className="event-row" key={item.id}>
                  <span className="stat-icon">
                    <Sparkles size={16} />
                  </span>
                  <div>
                    <h3>{String(item.title)}</h3>
                    <p>{date(item.created_at, true, locale)}</p>
                  </div>
                </div>
              ))}
            </section>
          )}
        </div>
        <div className="stack">
          <section className="panel">
            <div className="panel-header">
              <h2>{t("À ne pas manquer", "Coming up")}</h2>
              <Link
                href="/app/events"
                className="icon-button"
                aria-label={t("Voir les événements", "View events")}
              >
                <ArrowUpRight size={17} />
              </Link>
            </div>
            <ErrorNotice error={events.error} />
            {events.isPending ? (
              <Loading />
            ) : !events.data?.items.length ? (
              <Empty
                title={t("L’agenda se prépare", "Your calendar is coming soon")}
                description={t(
                  "Les prochains temps forts seront affichés ici.",
                  "Upcoming highlights will appear here.",
                )}
              />
            ) : (
              events.data.items.map((item) => (
                <Link href="/app/events" className="event-row" key={item.id}>
                  <div className="event-date">
                    <strong>
                      {new Date(String(item.starts_at)).getDate()}
                    </strong>
                    <span>
                      {new Date(String(item.starts_at)).toLocaleDateString(
                        locale === "fr" ? "fr-FR" : "en-GB",
                        { month: "short" },
                      )}
                    </span>
                  </div>
                  <div>
                    <h3>{String(item.title)}</h3>
                    <p>
                      {String(
                        item.location ||
                          t("Votre établissement", "Your institution"),
                      )}
                    </p>
                    <p>
                      {new Date(String(item.starts_at)).toLocaleTimeString(
                        locale === "fr" ? "fr-FR" : "en-GB",
                        { hour: "2-digit", minute: "2-digit" },
                      )}
                    </p>
                  </div>
                </Link>
              ))
            )}
          </section>
          <aside className="tip-card">
            <Sparkles size={24} color="var(--teal)" />
            <h3>
              {t(
                "Une question ? Votre communauté est là.",
                "Have a question? Your community is here.",
              )}
            </h3>
            <p>
              {t(
                "Échangez avec les autres étudiants, partagez une ressource ou lancez une discussion.",
                "Connect with fellow students, share a resource or start a discussion.",
              )}
            </p>
            <Link
              className="text-link"
              href="/app/community"
              style={{ color: "var(--teal)" }}
            >
              {t("Rejoindre la conversation", "Join the conversation")}{" "}
              <ArrowRight size={14} />
            </Link>
          </aside>
        </div>
      </div>
    </>
  );
}
