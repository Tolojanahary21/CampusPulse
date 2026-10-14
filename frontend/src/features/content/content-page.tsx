"use client";
import { usePreferences } from "@/components/preferences";
import { useState } from "react";
import Link from "next/link";
import { ArrowUpRight, FileText, Pin, Plus, Search } from "lucide-react";
import { useSession } from "@/components/app-shell";
import {
  Badge,
  Button,
  Empty,
  ErrorNotice,
  Loading,
  PageTitle,
  Pagination,
  Tabs,
  Field,
} from "@/components/ui";
import { useData } from "@/hooks/use-data";
import { date, params } from "@/lib/format";
import { useAcademic, options } from "@/features/academic/use-academic";
import type { Collection } from "@/types";
import { ContentEditor, type ContentKind } from "./content-editor";
export function ContentPage({ kind }: { kind: ContentKind }) {
  const { t, locale } = usePreferences();
  const { campusId, canPublish } = useSession();
  const doc = kind === "documents";
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [category, setCategory] = useState("");
  const [program, setProgram] = useState("");
  const [level, setLevel] = useState("");
  const [year, setYear] = useState("");
  const [subject, setSubject] = useState("");
  const [page, setPage] = useState(1);
  const [editing, setEditing] = useState(false);
  const academic = useAcademic(campusId);
  const { data, error, isPending } = useData<Collection>(
    `/${kind}${params({ campus_id: campusId, q, page, page_size: 12, status, category, program_id: program, level_id: level, year_id: year, subject_id: subject, manage: canPublish })}`,
  );
  function filter(set: (v: string) => void, v: string) {
    set(v);
    setPage(1);
  }
  return (
    <>
      <PageTitle
        eyebrow={
          doc
            ? t("APPRENDRE & PROGRESSER", "LEARN & GROW")
            : t("L’INFORMATION À LA SOURCE", "DIRECT FROM THE SOURCE")
        }
        title={
          doc
            ? t("La bibliothèque", "Library")
            : t("Annonces officielles", "Official announcements")
        }
        description={
          doc
            ? t(
                "Les ressources pour vous accompagner, tout au long de votre parcours.",
                "Resources to support you throughout your studies.",
              )
            : t(
                "Tout ce qui compte dans la vie de votre établissement.",
                "Everything that matters at your institution.",
              )
        }
        action={
          canPublish ? (
            <Button onClick={() => setEditing(true)} disabled={!campusId}>
              <Plus size={17} />
              {doc
                ? t("Ajouter un document", "Add a document")
                : t("Nouvelle annonce", "New announcement")}
            </Button>
          ) : undefined
        }
      />
      <div className="toolbar">
        <div className="search-input">
          <Search size={17} />
          <input
            aria-label={
              doc
                ? t("Rechercher un document", "Search documents")
                : t("Rechercher une annonce", "Search announcements")
            }
            placeholder={
              doc
                ? t(
                    "Rechercher un cours, un sujet…",
                    "Search for a course, a topic…",
                  )
                : t("Rechercher dans les annonces…", "Search announcements…")
            }
            value={q}
            onChange={(e) => filter(setQ, e.target.value)}
          />
        </div>
        {doc && (
          <select
            aria-label={t("Catégorie", "Category")}
            value={category}
            onChange={(e) => filter(setCategory, e.target.value)}
          >
            <option value="">
              {t("Toutes les catégories", "All categories")}
            </option>
            <option value="COURSE">{t("Cours", "Courses")}</option>
            <option value="EXERCISE">{t("Exercices", "Exercises")}</option>
            <option value="SOLUTION">{t("Corrigés", "Solutions")}</option>
            <option value="EXAM">{t("Examens", "Exams")}</option>
            <option value="SUMMARY">{t("Fiches", "Study notes")}</option>
            <option value="OTHER">{t("Autres", "Other")}</option>
          </select>
        )}
      </div>
      {doc && (
        <div className="filters-grid">
          <Field label={t("Année", "Year")}>
            <select
              value={year}
              onChange={(e) => filter(setYear, e.target.value)}
            >
              <option value="">{t("Toutes les années", "All years")}</option>
              {options(academic.years)}
            </select>
          </Field>
          <Field label={t("Filière", "Program")}>
            <select
              value={program}
              onChange={(e) => {
                filter(setProgram, e.target.value);
                setLevel("");
                setSubject("");
              }}
            >
              <option value="">
                {t("Toutes les filières", "All programs")}
              </option>
              {options(academic.programs)}
            </select>
          </Field>
          <Field label={t("Niveau", "Level")}>
            <select
              value={level}
              onChange={(e) => {
                filter(setLevel, e.target.value);
                setSubject("");
              }}
            >
              <option value="">{t("Tous les niveaux", "All levels")}</option>
              {options(
                academic.levels.filter(
                  (l) => !program || l.program_id === program,
                ),
                "program_name",
              )}
            </select>
          </Field>
          <Field label={t("Matière", "Subject")}>
            <select
              value={subject}
              onChange={(e) => filter(setSubject, e.target.value)}
            >
              <option value="">
                {t("Toutes les matières", "All subjects")}
              </option>
              {options(
                academic.subjects.filter(
                  (s) => !level || s.program_level_id === level,
                ),
              )}
            </select>
          </Field>
        </div>
      )}
      {canPublish && (
        <Tabs
          value={status}
          onChange={(v) => filter(setStatus, v)}
          items={[
            { id: "", label: t("Tous les contenus", "All content") },
            { id: "PUBLISHED", label: t("Publiés", "Published") },
            { id: "DRAFT", label: t("Brouillons", "Drafts") },
            { id: "ARCHIVED", label: t("Archives", "Archived") },
          ]}
        />
      )}
      <ErrorNotice error={error} />
      {isPending ? (
        <Loading />
      ) : !data?.items.length ? (
        <div className="panel">
          <Empty
            title={
              q || status || category
                ? t("Aucun résultat", "No results")
                : t(
                    "Votre espace attend ses premières ressources",
                    "Your first resources will appear here",
                  )
            }
            description={
              q || status || category
                ? t(
                    "Essayez d’autres mots-clés ou ajustez les filtres.",
                    "Try other keywords or adjust the filters.",
                  )
                : doc
                  ? t(
                      "Les documents publiés pour votre parcours apparaîtront ici.",
                      "Documents published for your program will appear here.",
                    )
                  : t(
                      "Les annonces de votre établissement apparaîtront ici dès leur publication.",
                      "Your institution’s announcements will appear here when published.",
                    )
            }
          />
        </div>
      ) : (
        <div className={doc ? "cards-grid" : "panel"}>
          {data.items.map((item) =>
            doc ? (
              <Link
                className="content-card"
                key={item.id}
                href={`/app/documents/${item.id}`}
              >
                <div
                  className={`document-symbol ${String(item.category).toLowerCase()}`}
                >
                  <FileText size={26} />
                </div>
                <div className="meta-row">
                  <Badge value={item.category} />
                  <Badge value={item.status} />
                </div>
                <h3>{String(item.title)}</h3>
                <p>
                  {String(
                    item.description ||
                      t("Ressource pédagogique", "Learning resource"),
                  )}
                </p>
                <div className="card-bottom">
                  <span className="small muted">
                    {date(item.created_at, false, locale)}
                  </span>
                  <ArrowUpRight size={18} />
                </div>
              </Link>
            ) : (
              <Link
                key={item.id}
                href={`/app/announcements/${item.id}`}
                className="announcement-row"
              >
                <div className="meta-row">
                  <Badge value={item.announcement_type} />
                  {canPublish && <Badge value={item.status} />}
                  <span>{date(item.created_at, false, locale)}</span>
                  {!!item.is_pinned && <Pin size={12} />}
                </div>
                <h3>{String(item.title)}</h3>
                <p>{String(item.summary || item.content)}</p>
                <div className="row-footer">
                  <span>
                    {String(
                      item.campus_name ||
                        t("Information officielle", "Official information"),
                    )}
                  </span>
                  <span className="text-link">
                    {t("Lire l’annonce", "Read announcement")}{" "}
                    <ArrowUpRight size={14} />
                  </span>
                </div>
              </Link>
            ),
          )}
        </div>
      )}
      <Pagination data={data} page={page} setPage={setPage} />
      {editing && (
        <ContentEditor kind={kind} onClose={() => setEditing(false)} />
      )}
    </>
  );
}
