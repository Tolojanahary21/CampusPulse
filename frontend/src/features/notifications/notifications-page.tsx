"use client";
import { usePreferences } from "@/components/preferences";
import { useState } from "react";
import Link from "next/link";
import { Bell, Check, CheckCheck } from "lucide-react";
import {
  Button,
  Empty,
  ErrorNotice,
  Loading,
  PageTitle,
  Pagination,
  Tabs,
} from "@/components/ui";
import { useAction, useData } from "@/hooks/use-data";
import { date, params } from "@/lib/format";
import type { Collection, RecordItem } from "@/types";
export function NotificationsPage() {
  const { t, locale } = usePreferences();
  const [page, setPage] = useState(1);
  const [unread, setUnread] = useState("all");
  const { data, error, isPending } = useData<Collection>(
    `/notifications${params({ page, page_size: 20, unread: unread === "unread" })}`,
  );
  const action = useAction();
  function notificationText(item: RecordItem) {
    let title = String(item.title);
    let message = String(item.message || "");
    // Only known server-generated templates are localized. Content titles and
    // names remain exactly as returned by the API.
    if (
      item.notification_type === "ANNOUNCEMENT" &&
      message === "Une nouvelle annonce officielle est disponible."
    ) {
      message = t(message, "A new official announcement is available.");
    } else if (
      item.notification_type === "DOCUMENT" &&
      message === "Une nouvelle ressource pédagogique est disponible."
    ) {
      message = t(message, "A new learning resource is available.");
    } else if (
      item.notification_type === "COMMUNITY" &&
      title === "Une réponse à votre publication"
    ) {
      title = t(title, "A reply to your post");
      const suffix = " a commenté votre publication.";
      if (message.endsWith(suffix)) {
        const authorName = message.slice(0, -suffix.length);
        message = t(message, `${authorName} commented on your post.`);
      }
    }
    return { title, message };
  }
  return (
    <>
      <PageTitle
        eyebrow={t("NE RIEN MANQUER", "STAY IN THE LOOP")}
        title={t("Vos notifications", "Your notifications")}
        description={t(
          "Les nouvelles qui vous concernent, réunies au même endroit.",
          "Updates that matter to you, all in one place.",
        )}
        action={
          <Button
            variant="secondary"
            busy={action.isPending}
            onClick={() => action.mutate({ path: "/notifications/read-all" })}
          >
            <CheckCheck size={17} />
            {t("Tout marquer comme lu", "Mark all as read")}
          </Button>
        }
      />
      <Tabs
        items={[
          {
            id: "all",
            label: t("Toutes les notifications", "All notifications"),
          },
          { id: "unread", label: t("Non lues", "Unread") },
        ]}
        value={unread}
        onChange={(v) => {
          setUnread(v);
          setPage(1);
        }}
      />
      <ErrorNotice error={error || action.error} />
      <div className="panel">
        {isPending ? (
          <Loading />
        ) : !data?.items.length ? (
          <Empty
            title={t("Vous êtes à jour", "You’re all caught up")}
            description={t(
              "Les prochaines actualités de votre campus apparaîtront ici.",
              "New updates from your campus will appear here.",
            )}
          />
        ) : (
          data.items.map((item) => {
            const text = notificationText(item);
            return (
              <article
                className={`notification-row ${!item.read_at ? "unread" : ""}`}
                key={item.id}
              >
                <span className="stat-icon">
                  <Bell size={18} />
                </span>
                <div>
                  <h3>{text.title}</h3>
                  <p>{text.message}</p>
                  <span className="small muted">
                    {date(item.created_at, true, locale)}
                  </span>
                  {typeof item.link === "string" &&
                    /^\/app(?:\/|$)/.test(item.link) && (
                      <Link
                        className="text-link"
                        style={{ marginLeft: 14 }}
                        href={item.link}
                      >
                        {t("Consulter →", "View →")}
                      </Link>
                    )}
                </div>
                {!item.read_at && (
                  <Button
                    variant="ghost"
                    busy={action.isPending}
                    aria-label={t("Marquer comme lue", "Mark as read")}
                    onClick={() =>
                      action.mutate({
                        path: `/notifications/${item.id}/read`,
                        method: "PATCH",
                      })
                    }
                  >
                    <Check size={17} />
                  </Button>
                )}
              </article>
            );
          })
        )}
      </div>
      <Pagination data={data} page={page} setPage={setPage} />
    </>
  );
}
