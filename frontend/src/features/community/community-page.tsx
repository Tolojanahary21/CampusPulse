"use client";
import { usePreferences } from "@/components/preferences";
import { useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  ArrowUpRight,
  Edit3,
  Flag,
  Heart,
  MessageCircle,
  Plus,
  Search,
  Sparkles,
  Trash2,
} from "lucide-react";
import { useSession } from "@/components/app-shell";
import {
  Badge,
  Button,
  Empty,
  ErrorNotice,
  Field,
  Loading,
  Modal,
  PageTitle,
  Pagination,
} from "@/components/ui";
import { useAction, useData } from "@/hooks/use-data";
import { date, initials, params } from "@/lib/format";
import type { Collection, RecordItem } from "@/types";
import { Comments } from "./comments";
import { ReportDialog } from "./report";
function PostEditor({
  item,
  onClose,
}: {
  item?: RecordItem;
  onClose: () => void;
}) {
  const { t } = usePreferences();
  const { campusId } = useSession();
  const action = useAction(onClose);
  return (
    <Modal
      title={
        item
          ? t("Modifier votre publication", "Edit your post")
          : t("Une idée à partager ?", "Have an idea to share?")
      }
      onClose={onClose}
    >
      <form
        onSubmit={(e) => {
          e.preventDefault();
          const f = new FormData(e.currentTarget);
          action.mutate({
            path: `/community/posts${item ? `/${item.id}` : ""}`,
            method: item ? "PATCH" : "POST",
            data: {
              title: f.get("title"),
              content: f.get("content"),
              ...(!item
                ? { campus_id: campusId, post_type: f.get("post_type") }
                : {}),
            },
          });
        }}
      >
        <ErrorNotice error={action.error} />
        <Field label={t("Titre (facultatif)", "Title (optional)")}>
          <input
            name="title"
            maxLength={255}
            defaultValue={String(item?.title || "")}
          />
        </Field>
        {!item && (
          <Field label={t("Type de publication", "Post type")}>
            <select name="post_type">
              <option value="DISCUSSION">
                {t("Discussion", "Discussion")}
              </option>
              <option value="QUESTION">{t("Question", "Question")}</option>
              <option value="RESOURCE">{t("Ressource", "Resource")}</option>
              <option value="ANNOUNCEMENT">
                {t("Annonce communautaire", "Community announcement")}
              </option>
              <option value="OTHER">{t("Autre", "Other")}</option>
            </select>
          </Field>
        )}
        <Field label={t("Votre message", "Your message")}>
          <textarea
            name="content"
            required
            maxLength={10000}
            minLength={1}
            rows={6}
            placeholder={t(
              "Une question, une découverte, un coup de main…",
              "A question, a discovery, a helping hand…",
            )}
            defaultValue={String(item?.content || "")}
          />
        </Field>
        <div className="form-actions">
          <Button type="button" variant="secondary" onClick={onClose}>
            {t("Annuler", "Cancel")}
          </Button>
          <Button busy={action.isPending}>
            {item ? t("Enregistrer", "Save") : t("Publier", "Publish")}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
function PostCard({
  item,
  detail = false,
}: {
  item: RecordItem;
  detail?: boolean;
}) {
  const { t, locale } = usePreferences();
  const { user } = useSession();
  const [editing, setEditing] = useState(false);
  const [report, setReport] = useState(false);
  const router = useRouter();
  const action = useAction(() => {
    if (
      detail &&
      action.variables?.method === "DELETE" &&
      action.variables.path.startsWith("/community/posts/")
    )
      router.push("/app/community");
  });
  return (
    <article className="content-card">
      <div className="post-header">
        <span className="avatar">
          {initials(String(item.author_name || t("Membre", "Member")))}
        </span>
        <div style={{ flex: 1 }}>
          <strong>
            {String(item.author_name || t("Membre du campus", "Campus member"))}
          </strong>
          <small>{date(item.created_at, true, locale)}</small>
        </div>
        {item.status !== "PUBLISHED" &&
          item.status !== "VISIBLE" &&
          item.status !== "ACTIVE" && <Badge value={item.status} />}
        <button
          className="icon-button"
          aria-label={t("Signaler cette publication", "Report this post")}
          onClick={() => setReport(true)}
        >
          <Flag size={15} />
        </button>
        {item.author_user_id === user.id && (
          <>
            <button
              className="icon-button"
              aria-label={t("Modifier cette publication", "Edit this post")}
              onClick={() => setEditing(true)}
            >
              <Edit3 size={15} />
            </button>
            <button
              className="icon-button"
              aria-label={t("Retirer cette publication", "Remove this post")}
              onClick={() => {
                if (
                  window.confirm(
                    t("Retirer cette publication ?", "Remove this post?"),
                  )
                )
                  action.mutate({
                    path: `/community/posts/${item.id}`,
                    method: "DELETE",
                  });
              }}
            >
              <Trash2 size={15} />
            </button>
          </>
        )}
      </div>
      {!!item.title && (
        <h3>
          {detail ? (
            String(item.title)
          ) : (
            <Link href={`/app/community/${item.id}`}>{String(item.title)}</Link>
          )}
        </h3>
      )}
      <div className="content-body">
        {detail ? String(item.content) : String(item.content).slice(0, 700)}
        {!detail && String(item.content).length > 700 && "…"}
      </div>
      <ErrorNotice error={action.error} />
      <div className="post-footer">
        <Button
          variant="ghost"
          busy={action.isPending}
          aria-pressed={!!item.my_reaction_id}
          onClick={() =>
            action.mutate(
              item.my_reaction_id
                ? {
                    path: `/community/reactions/${item.my_reaction_id}`,
                    method: "DELETE",
                  }
                : {
                    path: "/community/reactions",
                    data: { post_id: item.id, reaction_type: "LIKE" },
                  },
            )
          }
        >
          <Heart
            size={17}
            fill={item.my_reaction_id ? "currentColor" : "none"}
          />
          {Number(item.reaction_count || 0)}{" "}
          {t(
            "J’aime",
            Number(item.reaction_count || 0) === 1 ? "Like" : "Likes",
          )}
        </Button>
        <Link className="button ghost" href={`/app/community/${item.id}`}>
          <MessageCircle size={17} />
          {Number(item.comment_count || 0)}{" "}
          {Number(item.comment_count || 0) === 1
            ? t("commentaire", "comment")
            : t("commentaires", "comments")}
        </Link>
        {!detail && (
          <Link
            className="icon-button"
            style={{ marginLeft: "auto" }}
            aria-label={t("Ouvrir la publication", "Open post")}
            href={`/app/community/${item.id}`}
          >
            <ArrowUpRight size={17} />
          </Link>
        )}
      </div>
      {editing && <PostEditor item={item} onClose={() => setEditing(false)} />}{" "}
      {report && (
        <ReportDialog postId={item.id} onClose={() => setReport(false)} />
      )}
    </article>
  );
}
export function CommunityPage() {
  const { t } = usePreferences();
  const { campusId, user } = useSession();
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [editing, setEditing] = useState(false);
  const { data, error, isPending } = useData<Collection>(
    `/community/posts${params({ campus_id: campusId, q, page, page_size: 10 })}`,
    !!campusId,
  );
  return (
    <>
      <PageTitle
        eyebrow={t("LA FORCE DU COLLECTIF", "BETTER TOGETHER")}
        title={t("La communauté", "Community")}
        description={t(
          "Des questions, des idées et des rencontres. Faites vivre votre campus.",
          "Questions, ideas and connections. Bring your campus to life.",
        )}
        action={
          <Button disabled={!campusId} onClick={() => setEditing(true)}>
            <Plus size={17} />
            {t("Créer une publication", "Create a post")}
          </Button>
        }
      />
      <div className="community-grid">
        <div className="stack">
          <div className="panel composer">
            <span className="avatar">
              {initials(user.first_name, user.last_name)}
            </span>
            <button disabled={!campusId} onClick={() => setEditing(true)}>
              {t(
                "Qu’avez-vous envie de partager,",
                "What would you like to share,",
              )}{" "}
              {user.first_name}
              {t(" ?", "?")}
            </button>
          </div>
          <div className="search-input">
            <Search size={17} />
            <input
              aria-label={t("Rechercher une publication", "Search posts")}
              placeholder={t(
                "Rechercher dans la communauté…",
                "Search the community…",
              )}
              value={q}
              onChange={(e) => {
                setQ(e.target.value);
                setPage(1);
              }}
            />
          </div>
          <ErrorNotice error={error} />
          {!campusId ? (
            <Empty
              title={t("Rejoignez un établissement", "Join an institution")}
              description={t(
                "L’administration peut vous rattacher à votre campus.",
                "An administrator can connect you to your campus.",
              )}
            />
          ) : isPending ? (
            <Loading />
          ) : !data?.items.length ? (
            <div className="panel">
              <Empty
                title={t(
                  "Le début d’une conversation",
                  "The start of a conversation",
                )}
                description={t(
                  "Partagez une première question ou une découverte avec votre campus.",
                  "Share your first question or discovery with your campus.",
                )}
              />
            </div>
          ) : (
            data.items.map((item) => <PostCard item={item} key={item.id} />)
          )}
          <Pagination data={data} page={page} setPage={setPage} />
        </div>
        <aside className="community-aside stack">
          <div className="tip-card">
            <Sparkles size={23} />
            <h3>
              {t("On avance mieux ensemble.", "We move forward together.")}
            </h3>
            <p>
              {t(
                "Une bonne question peut aider toute une promotion. Un conseil peut changer une journée.",
                "A good question can help an entire class. A piece of advice can change someone’s day.",
              )}
            </p>
          </div>
          <div className="panel">
            <div className="panel-header">
              <h3>
                {t("Un espace qui nous ressemble", "A space for all of us")}
              </h3>
            </div>
            <div className="panel-body">
              <p className="small muted">
                {t(
                  "Échangez avec respect et bienveillance. Protégez les informations personnelles et citez vos sources lorsque vous partagez une ressource.",
                  "Be respectful and considerate. Protect personal information and cite your sources when sharing a resource.",
                )}
              </p>
              <p className="small muted" style={{ marginTop: 14 }}>
                {t(
                  "Un contenu vous semble inapproprié ? Le bouton de signalement permet à l’équipe de modération d’intervenir.",
                  "See inappropriate content? Use the report button to let the moderation team know.",
                )}
              </p>
            </div>
          </div>
        </aside>
      </div>
      {editing && <PostEditor onClose={() => setEditing(false)} />}
    </>
  );
}
export function CommunityDetail() {
  const { t } = usePreferences();
  const { id } = useParams<{ id: string }>();
  const { data, error, isPending } = useData<RecordItem>(
    `/community/posts/${id}`,
  );
  return (
    <div className="detail-layout">
      <Link href="/app/community" className="text-link">
        <ArrowLeft size={16} />
        {t("Retour à la communauté", "Back to the community")}
      </Link>
      <ErrorNotice error={error} />
      {isPending ? (
        <Loading />
      ) : (
        data && (
          <div style={{ marginTop: 22 }}>
            <PostCard item={data} detail />
            <Comments path={`/community/posts/${id}/comments`} community />
          </div>
        )
      )}
    </div>
  );
}
